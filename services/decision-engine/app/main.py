"""
Decision Engine FastAPI application.
"""
import logging
import uuid
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

from app.config import settings
from app.models import ScoreRequest, ScoreResponse, HealthResponse, DecisionType
from app.idempotency import idempotency_checker
from app.storage import postgres_storage
from app.kafka_producer import kafka_producer
from app.orchestrator import orchestrator

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'decision_engine_requests_total',
    'Total number of requests',
    ['endpoint', 'method', 'status']
)
DECISION_COUNT = Counter(
    'decision_engine_decisions_total',
    'Total number of decisions',
    ['decision_type']
)
LATENCY = Histogram(
    'decision_engine_latency_seconds',
    'Request latency in seconds',
    ['endpoint']
)
SCORE_HISTOGRAM = Histogram(
    'decision_engine_scores',
    'Distribution of ML scores',
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.VERSION}")
    
    try:
        await idempotency_checker.connect()
        await postgres_storage.connect()
        await kafka_producer.start()
        await orchestrator.initialize()
        logger.info("All services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down services")
    await orchestrator.close()
    await kafka_producer.stop()
    await postgres_storage.close()
    await idempotency_checker.close()
    logger.info("All services shut down successfully")


app = FastAPI(
    title="FraudGuard AI - Decision Engine",
    version=settings.VERSION,
    description="Real-time fraud detection orchestration service",
    lifespan=lifespan
)


@app.post("/v1/score", response_model=ScoreResponse)
async def score_transaction(request: ScoreRequest) -> ScoreResponse:
    """
    Score a transaction and make fraud decision.
    
    This endpoint orchestrates parallel calls to:
    1. Model Serving (ML score)
    2. Rules Service (business rules)
    
    And then makes a final decision: ALLOW, CHALLENGE, or DENY.
    """
    start_time = datetime.utcnow()
    
    try:
        # Generate decision ID
        decision_id = f"dec_{uuid.uuid4().hex[:12]}"
        
        # Check idempotency
        idem_key = f"{request.tenant_id}:{request.event_id}"
        existing_decision_id = await idempotency_checker.check_and_set(idem_key, decision_id)
        
        if existing_decision_id:
            # Return cached decision
            logger.info(f"Idempotent request detected: {request.event_id}")
            cached_decision = await postgres_storage.get_decision(existing_decision_id)
            
            if cached_decision:
                return ScoreResponse(
                    event_id=request.event_id,
                    decision_id=existing_decision_id,
                    decision=DecisionType(cached_decision['decision']),
                    score=cached_decision.get('score'),
                    reasons=cached_decision.get('reasons', []),
                    rule_hits=cached_decision.get('rule_hits', []),
                    latency_ms=cached_decision['latency_ms'],
                    model_version=cached_decision['model_version'],
                    requires_2fa=False
                )
        
        # Store event
        await postgres_storage.store_event(
            event_id=request.event_id,
            tenant_id=request.tenant_id,
            event_type="card_payment",
            payload=request.dict(),
            idem_key=idem_key
        )
        
        # Orchestrate decision
        result = await orchestrator.orchestrate(request)
        
        decision = result['decision']
        score = result.get('score')
        rule_hits = result.get('rule_hits', [])
        reasons = result.get('reasons', [])
        requires_2fa = result.get('requires_2fa', False)
        orchestration_latency = result.get('latency_ms', 0)
        
        # Calculate total latency
        total_latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        # Store decision
        await postgres_storage.store_decision(
            decision_id=decision_id,
            event_id=request.event_id,
            tenant_id=request.tenant_id,
            decision=decision.value,
            score=score,
            rule_hits=rule_hits,
            reasons=reasons,
            latency_ms=total_latency_ms,
            model_version=settings.MODEL_VERSION,
            thresholds={
                "low_risk": settings.THRESHOLD_LOW_RISK,
                "high_risk": settings.THRESHOLD_HIGH_RISK
            }
        )
        
        # Publish to Kafka
        await kafka_producer.publish_decision_event(
            event_id=request.event_id,
            decision_id=decision_id,
            decision=decision.value,
            score=score,
            tenant_id=request.tenant_id,
            metadata={"reasons": reasons, "rule_hits": rule_hits}
        )
        
        # Create case for CHALLENGE/DENY
        if decision in [DecisionType.CHALLENGE, DecisionType.DENY]:
            priority = 2 if decision == DecisionType.DENY else 1
            queue = "high_risk" if decision == DecisionType.DENY else "medium_risk"
            
            await kafka_producer.publish_case_event(
                event_id=request.event_id,
                decision_id=decision_id,
                decision=decision.value,
                score=score,
                priority=priority,
                queue=queue,
                tenant_id=request.tenant_id
            )
        
        # Update metrics
        DECISION_COUNT.labels(decision_type=decision.value).inc()
        if score is not None:
            SCORE_HISTOGRAM.observe(score)
        LATENCY.labels(endpoint="/v1/score").observe(total_latency_ms / 1000.0)
        REQUEST_COUNT.labels(endpoint="/v1/score", method="POST", status="200").inc()
        
        logger.info(
            f"Decision made: {decision.value} | event={request.event_id} | "
            f"score={score} | latency={total_latency_ms}ms"
        )
        
        return ScoreResponse(
            event_id=request.event_id,
            decision_id=decision_id,
            decision=decision,
            score=score,
            reasons=reasons,
            rule_hits=rule_hits,
            latency_ms=total_latency_ms,
            model_version=settings.MODEL_VERSION,
            requires_2fa=requires_2fa
        )
        
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        REQUEST_COUNT.labels(endpoint="/v1/score", method="POST", status="500").inc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    dependencies = {}
    
    # Check Redis
    try:
        if idempotency_checker.redis_client:
            await idempotency_checker.redis_client.ping()
            dependencies["redis"] = "healthy"
        else:
            dependencies["redis"] = "not_connected"
    except Exception as e:
        dependencies["redis"] = f"unhealthy: {str(e)}"
    
    # Check PostgreSQL
    try:
        if postgres_storage.pool:
            async with postgres_storage.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            dependencies["postgres"] = "healthy"
        else:
            dependencies["postgres"] = "not_connected"
    except Exception as e:
        dependencies["postgres"] = f"unhealthy: {str(e)}"
    
    # Check Kafka
    if kafka_producer.enabled and kafka_producer.producer:
        dependencies["kafka"] = "healthy"
    else:
        dependencies["kafka"] = "disabled" if not kafka_producer.enabled else "not_connected"
    
    # Overall status
    status = "healthy" if all(
        v in ["healthy", "disabled"] for v in dependencies.values()
    ) else "degraded"
    
    return HealthResponse(
        status=status,
        service=settings.SERVICE_NAME,
        version=settings.VERSION,
        timestamp=datetime.utcnow(),
        dependencies=dependencies
    )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION,
        "status": "running",
        "endpoints": {
            "score": "/v1/score",
            "health": "/health",
            "metrics": "/metrics"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=False
    )
