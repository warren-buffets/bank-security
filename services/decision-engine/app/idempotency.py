"""
Idempotency check using Redis.
"""
import redis.asyncio as redis
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


class IdempotencyChecker:
    """Redis-based idempotency checker."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            await self.redis_client.ping()
            logger.info("Connected to Redis for idempotency checks")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Closed Redis connection")
    
    async def check_and_set(self, idempotency_key: str, decision_id: str) -> Optional[str]:
        """
        Check if request is duplicate and set if new.
        
        Args:
            idempotency_key: Unique key for the request (e.g., event_id + tenant_id)
            decision_id: Decision ID to store
            
        Returns:
            None if new request, existing decision_id if duplicate
        """
        if not self.redis_client:
            logger.warning("Redis not connected, skipping idempotency check")
            return None
        
        try:
            redis_key = f"idem:{idempotency_key}"
            
            # Try to get existing value
            existing = await self.redis_client.get(redis_key)
            if existing:
                logger.info(f"Duplicate request detected: {idempotency_key}")
                return existing
            
            # Set new value with TTL
            await self.redis_client.setex(
                redis_key,
                settings.REDIS_IDEMPOTENCY_TTL,
                decision_id
            )
            logger.debug(f"Set idempotency key: {idempotency_key} -> {decision_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error checking idempotency: {e}")
            # Fail open - allow request to proceed
            return None
    
    async def get_decision(self, idempotency_key: str) -> Optional[str]:
        """
        Get existing decision for idempotency key.
        
        Args:
            idempotency_key: Unique key for the request
            
        Returns:
            Decision ID if found, None otherwise
        """
        if not self.redis_client:
            return None
        
        try:
            redis_key = f"idem:{idempotency_key}"
            return await self.redis_client.get(redis_key)
        except Exception as e:
            logger.error(f"Error getting idempotency key: {e}")
            return None


# Global instance
idempotency_checker = IdempotencyChecker()
