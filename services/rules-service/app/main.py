"""
SafeGuard AI - Rules Service
FastAPI service for fraud detection rules evaluation.
"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

import asyncpg
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from .config import config
from .models import (
    EvaluationRequest,
    EvaluationResponse,
    HealthResponse,
    MatchedRule,
    ListMatch,
    Rule,
    TransactionContext
)
from .rules_engine import RulesEngine
from .lists_checker import ListsChecker

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
if config.METRICS_ENABLED:
    evaluation_counter = Counter(
        'rules_evaluations_total',
        'Total number of rule evaluations',
        ['status']
    )
    evaluation_duration = Histogram(
        'rules_evaluation_duration_seconds',
        'Rule evaluation duration in seconds'
    )
    rule_matches_counter = Counter(
        'rules_matched_total',
        'Total number of rule matches',
        ['rule_id', 'action']
    )
    list_matches_counter = Counter(
        'list_matches_total',
        'Total number of list matches',
        ['list_type']
    )

# Global state
app_state = {
    'db_pool': None,
    'redis_client': None,
    'rules_engine': None,
    'lists_checker': None,
    'rules_cache': {},
    'cache_timestamp': 0
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for the application."""
    # Startup
    logger.info(f"Starting {config.SERVICE_NAME} v{config.SERVICE_VERSION}")
    
    try:
        # Initialize PostgreSQL connection pool
        logger.info("Connecting to PostgreSQL...")
        app_state['db_pool'] = await asyncpg.create_pool(
            host=config.POSTGRES_HOST,
            port=config.POSTGRES_PORT,
            database=config.POSTGRES_DB,
            user=config.POSTGRES_USER,
            password=config.POSTGRES_PASSWORD,
            min_size=5,
            max_size=20,
            timeout=10
        )
        logger.info("PostgreSQL connection pool created")
        
        # Initialize Redis client
        logger.info("Connecting to Redis...")
        redis_url = f"redis://{config.REDIS_HOST}:{config.REDIS_PORT}/{config.REDIS_DB}"
        if config.REDIS_PASSWORD:
            redis_url = f"redis://:{config.REDIS_PASSWORD}@{config.REDIS_HOST}:{config.REDIS_PORT}/{config.REDIS_DB}"
        
        app_state['redis_client'] = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        await app_state['redis_client'].ping()
        logger.info("Redis connection established")
        
        # Initialize engines
        app_state['rules_engine'] = RulesEngine()
        app_state['lists_checker'] = ListsChecker(app_state['redis_client'])
        
        # Load initial rules
        await load_rules_from_db()
        
        logger.info("Service startup complete")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down service...")
    
    if app_state['db_pool']:
        await app_state['db_pool'].close()
        logger.info("PostgreSQL connection pool closed")
    
    if app_state['redis_client']:
        await app_state['redis_client'].close()
        logger.info("Redis connection closed")
    
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="SafeGuard AI - Rules Service",
    description="Rule evaluation service for fraud detection",
    version=config.SERVICE_VERSION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def load_rules_from_db() -> List[Dict]:
    """Load rules from PostgreSQL database."""
    try:
        async with app_state['db_pool'].acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, name, expression, action, priority, enabled, description, metadata, created_at, updated_at
                FROM rules_v2
                WHERE enabled = true
                ORDER BY priority DESC
            """)
            
            rules = []
            for row in rows:
                # Parse metadata if it's a string (JSONB might be returned as string)
                metadata = row['metadata'] or {}
                if isinstance(metadata, str):
                    import json
                    metadata = json.loads(metadata)

                rules.append({
                    'id': row['id'],
                    'name': row['name'],
                    'expression': row['expression'],
                    'action': row['action'],
                    'priority': row['priority'],
                    'enabled': row['enabled'],
                    'description': row['description'],
                    'metadata': metadata
                })
            
            # Update cache
            app_state['rules_cache'] = {rule['id']: rule for rule in rules}
            app_state['cache_timestamp'] = time.time()
            
            logger.info(f"Loaded {len(rules)} rules from database")
            return rules
            
    except Exception as e:
        logger.error(f"Error loading rules from database: {e}")
        # Return cached rules if available
        return list(app_state['rules_cache'].values())


async def get_rules() -> List[Dict]:
    """Get rules from cache or database."""
    # Refresh cache if expired
    cache_age = time.time() - app_state['cache_timestamp']
    if cache_age > config.RULES_CACHE_TTL:
        return await load_rules_from_db()
    
    return list(app_state['rules_cache'].values())


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    dependencies = {}
    
    # Check PostgreSQL
    try:
        async with app_state['db_pool'].acquire() as conn:
            await conn.fetchval("SELECT 1")
        dependencies['postgresql'] = 'healthy'
    except Exception as e:
        dependencies['postgresql'] = f'unhealthy: {str(e)}'
    
    # Check Redis
    try:
        await app_state['redis_client'].ping()
        dependencies['redis'] = 'healthy'
    except Exception as e:
        dependencies['redis'] = f'unhealthy: {str(e)}'
    
    status = 'healthy' if all(v == 'healthy' for v in dependencies.values()) else 'degraded'
    
    return HealthResponse(
        status=status,
        service=config.SERVICE_NAME,
        version=config.SERVICE_VERSION,
        dependencies=dependencies
    )


@app.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_transaction(request: EvaluationRequest):
    """
    Evaluate a transaction against fraud detection rules.
    
    Returns:
        Evaluation response with matched rules and decision
    """
    start_time = time.time()
    context = request.context
    
    try:
        # Convert context to dict for evaluation
        context_dict = context.model_dump()
        
        # Initialize response
        matched_rules = []
        list_matches = []
        should_deny = False
        should_review = False
        reasons = []
        
        # Check deny/allow lists if requested
        if request.check_lists:
            deny_matches, allow_matches = await app_state['lists_checker'].check_all_lists(context_dict)
            
            # Process deny list matches
            for match in deny_matches:
                should_deny = True
                reasons.append(match['reason'])
                list_matches.append(ListMatch(**match))
                
                if config.METRICS_ENABLED:
                    list_matches_counter.labels(list_type='deny').inc()
            
            # Process allow list matches
            for match in allow_matches:
                list_matches.append(ListMatch(**match))
                
                if config.METRICS_ENABLED:
                    list_matches_counter.labels(list_type='allow').inc()
            
            # If on allow list and not on deny list, skip rule evaluation
            if allow_matches and not deny_matches:
                logger.info(f"Transaction {context.transaction_id} on allow list, skipping rules")
                evaluation_time_ms = (time.time() - start_time) * 1000
                
                if config.METRICS_ENABLED:
                    evaluation_counter.labels(status='allowed').inc()
                    evaluation_duration.observe(time.time() - start_time)
                
                return EvaluationResponse(
                    transaction_id=context.transaction_id,
                    should_deny=False,
                    should_review=False,
                    matched_rules=[],
                    list_matches=list_matches,
                    evaluation_time_ms=round(evaluation_time_ms, 2),
                    reasons=["Transaction on allow list"]
                )
        
        # Load rules
        rules = await get_rules()
        
        # Evaluate rules with timeout
        matched = app_state['rules_engine'].evaluate_rules(
            rules,
            context_dict,
            timeout_ms=config.EVALUATION_TIMEOUT_MS
        )
        
        # Process matched rules
        for rule in matched:
            matched_rule = MatchedRule(**rule)
            matched_rules.append(matched_rule)
            reasons.append(rule['reason'])
            
            # Update decision based on action
            if rule['action'] == 'deny':
                should_deny = True
            elif rule['action'] == 'review':
                should_review = True
            
            if config.METRICS_ENABLED:
                rule_matches_counter.labels(
                    rule_id=rule['rule_id'],
                    action=rule['action']
                ).inc()
        
        # Calculate evaluation time
        evaluation_time_ms = (time.time() - start_time) * 1000
        
        # Check if we exceeded timeout
        if evaluation_time_ms > config.EVALUATION_TIMEOUT_MS:
            logger.warning(
                f"Evaluation exceeded timeout: {evaluation_time_ms}ms > {config.EVALUATION_TIMEOUT_MS}ms"
            )
        
        # Update metrics
        if config.METRICS_ENABLED:
            status = 'denied' if should_deny else ('review' if should_review else 'approved')
            evaluation_counter.labels(status=status).inc()
            evaluation_duration.observe(time.time() - start_time)
        
        logger.info(
            f"Transaction {context.transaction_id}: "
            f"deny={should_deny}, review={should_review}, "
            f"rules={len(matched_rules)}, lists={len(list_matches)}, "
            f"time={evaluation_time_ms:.2f}ms"
        )
        
        return EvaluationResponse(
            transaction_id=context.transaction_id,
            should_deny=should_deny,
            should_review=should_review,
            matched_rules=matched_rules,
            list_matches=list_matches,
            evaluation_time_ms=round(evaluation_time_ms, 2),
            reasons=reasons
        )
        
    except Exception as e:
        logger.error(f"Error evaluating transaction {context.transaction_id}: {e}", exc_info=True)
        
        if config.METRICS_ENABLED:
            evaluation_counter.labels(status='error').inc()
        
        raise HTTPException(status_code=500, detail=f"Evaluation error: {str(e)}")


@app.post("/rules/reload")
async def reload_rules():
    """Reload rules from database (admin endpoint)."""
    try:
        rules = await load_rules_from_db()
        return {
            'status': 'success',
            'rules_loaded': len(rules),
            'timestamp': time.time()
        }
    except Exception as e:
        logger.error(f"Error reloading rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rules")
async def list_rules():
    """List all active rules."""
    try:
        rules = await get_rules()
        return {
            'rules': rules,
            'count': len(rules),
            'cache_age': time.time() - app_state['cache_timestamp']
        }
    except Exception as e:
        logger.error(f"Error listing rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    if not config.METRICS_ENABLED:
        return Response(content="Metrics disabled", status_code=404)
    
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        'service': config.SERVICE_NAME,
        'version': config.SERVICE_VERSION,
        'status': 'running',
        'endpoints': {
            'health': '/health',
            'evaluate': 'POST /evaluate',
            'rules': '/rules',
            'reload': 'POST /rules/reload',
            'metrics': '/metrics'
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,
        log_level=config.LOG_LEVEL.lower()
    )
