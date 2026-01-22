"""
PostgreSQL storage for events and decisions.
"""
import asyncpg
import logging
import json
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime
from app.config import settings

logger = logging.getLogger(__name__)


class PostgresStorage:
    """PostgreSQL storage handler."""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Create connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                database=settings.POSTGRES_DB,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                min_size=settings.POSTGRES_MIN_CONNECTIONS,
                max_size=settings.POSTGRES_MAX_CONNECTIONS,
                command_timeout=10
            )
            logger.info("Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    async def close(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Closed PostgreSQL connection pool")
    
    def compute_hash(self, event_id: str, tenant_id: str, ts: datetime, payload: Dict[str, Any]) -> str:
        """Compute SHA256 hash for integrity."""
        content = f"{event_id}{tenant_id}{ts.isoformat()}{json.dumps(payload, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def store_event(
        self,
        event_id: str,
        tenant_id: str,
        event_type: str,
        payload: Dict[str, Any],
        idem_key: str
    ) -> bool:
        """
        Store transaction event.
        
        Args:
            event_id: Unique event identifier
            tenant_id: Tenant identifier
            event_type: Type of event (e.g., 'card_payment')
            payload: Full event payload
            idem_key: Idempotency key
            
        Returns:
            True if stored successfully
        """
        if not self.pool:
            logger.error("PostgreSQL pool not initialized")
            return False
        
        try:
            ts = datetime.utcnow()
            event_hash = self.compute_hash(event_id, tenant_id, ts, payload)
            
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO events (event_id, tenant_id, ts, type, payload_json, idem_key, hash, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (event_id) DO NOTHING
                    """,
                    event_id,
                    tenant_id,
                    ts,
                    event_type,
                    json.dumps(payload),
                    idem_key,
                    bytes.fromhex(event_hash),
                    ts
                )
            
            logger.debug(f"Stored event: {event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing event {event_id}: {e}")
            return False
    
    async def store_decision(
        self,
        decision_id: str,
        event_id: str,
        tenant_id: str,
        decision: str,
        score: Optional[float],
        rule_hits: list,
        reasons: list,
        latency_ms: int,
        model_version: str,
        thresholds: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store fraud decision.
        
        Args:
            decision_id: Unique decision identifier
            event_id: Related event ID
            tenant_id: Tenant identifier
            decision: ALLOW, CHALLENGE, or DENY
            score: ML score [0..1]
            rule_hits: List of rule IDs triggered
            reasons: Human-readable reasons
            latency_ms: Processing latency
            model_version: ML model version
            thresholds: Decision thresholds used
            
        Returns:
            True if stored successfully
        """
        if not self.pool:
            logger.error("PostgreSQL pool not initialized")
            return False
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO decisions 
                    (decision_id, event_id, tenant_id, decision, score, rule_hits, reasons, 
                     thresholds, latency_ms, model_version, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    """,
                    decision_id,
                    event_id,
                    tenant_id,
                    decision,
                    score,
                    rule_hits,
                    reasons,
                    json.dumps(thresholds) if thresholds else None,
                    latency_ms,
                    model_version,
                    datetime.utcnow()
                )
            
            logger.debug(f"Stored decision: {decision_id} -> {decision}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing decision {decision_id}: {e}")
            return False
    
    async def get_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve decision by ID.
        
        Args:
            decision_id: Decision identifier
            
        Returns:
            Decision record or None
        """
        if not self.pool:
            return None
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT decision_id, event_id, tenant_id, decision, score, 
                           rule_hits, reasons, latency_ms, model_version, created_at
                    FROM decisions
                    WHERE decision_id = $1
                    """,
                    decision_id
                )
            
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving decision {decision_id}: {e}")
            return None


# Global instance
postgres_storage = PostgresStorage()
