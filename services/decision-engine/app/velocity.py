"""
Velocity calculation module using Redis.
Tracks transaction frequency per user for fraud detection.
"""
import logging
import time
from typing import Optional, Dict
import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)


class VelocityTracker:
    """Tracks transaction velocity per user using Redis."""

    # Time windows in seconds
    WINDOW_1H = 3600      # 1 hour
    WINDOW_24H = 86400    # 24 hours

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.connected = False

    async def initialize(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=2.0
            )
            # Test connection
            await self.redis_client.ping()
            self.connected = True
            logger.info(f"Velocity tracker connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis for velocity: {e}")
            self.connected = False

    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Velocity tracker Redis connection closed")

    def _get_key(self, user_id: str, window: str) -> str:
        """Generate Redis key for user velocity."""
        return f"velocity:{user_id}:{window}"

    async def record_transaction(self, user_id: str, amount: float) -> Dict[str, int]:
        """
        Record a transaction and return current velocity counts.

        Args:
            user_id: User identifier
            amount: Transaction amount

        Returns:
            Dict with velocity_1h and velocity_24h counts
        """
        if not self.connected or not self.redis_client:
            logger.debug("Redis not connected, returning default velocity")
            return {"velocity_1h": 0, "velocity_24h": 0, "amount_sum_24h": 0.0}

        try:
            now = int(time.time())

            # Keys for sorted sets (score = timestamp)
            key_1h = self._get_key(user_id, "1h")
            key_24h = self._get_key(user_id, "24h")
            key_amount = self._get_key(user_id, "amount_24h")

            # Use pipeline for efficiency
            pipe = self.redis_client.pipeline()

            # Remove expired entries
            pipe.zremrangebyscore(key_1h, 0, now - self.WINDOW_1H)
            pipe.zremrangebyscore(key_24h, 0, now - self.WINDOW_24H)
            pipe.zremrangebyscore(key_amount, 0, now - self.WINDOW_24H)

            # Add current transaction
            tx_id = f"{now}:{id(self)}"  # Unique transaction ID
            pipe.zadd(key_1h, {tx_id: now})
            pipe.zadd(key_24h, {tx_id: now})
            pipe.zadd(key_amount, {f"{tx_id}:{amount}": now})

            # Set TTL to auto-cleanup
            pipe.expire(key_1h, self.WINDOW_1H + 60)
            pipe.expire(key_24h, self.WINDOW_24H + 60)
            pipe.expire(key_amount, self.WINDOW_24H + 60)

            # Count transactions
            pipe.zcard(key_1h)
            pipe.zcard(key_24h)

            # Execute pipeline
            results = await pipe.execute()

            # Get counts from results (last 2 items)
            velocity_1h = results[-2]
            velocity_24h = results[-1]

            # Calculate amount sum (separate query for simplicity)
            amount_entries = await self.redis_client.zrange(key_amount, 0, -1)
            amount_sum_24h = sum(
                float(entry.split(":")[-1])
                for entry in amount_entries
                if ":" in entry
            )

            logger.debug(f"User {user_id} velocity: 1h={velocity_1h}, 24h={velocity_24h}, sum={amount_sum_24h:.2f}")

            return {
                "velocity_1h": velocity_1h,
                "velocity_24h": velocity_24h,
                "amount_sum_24h": amount_sum_24h
            }

        except Exception as e:
            logger.error(f"Error recording velocity: {e}")
            return {"velocity_1h": 0, "velocity_24h": 0, "amount_sum_24h": 0.0}

    async def get_velocity(self, user_id: str) -> Dict[str, int]:
        """
        Get current velocity for a user without recording.

        Args:
            user_id: User identifier

        Returns:
            Dict with velocity counts
        """
        if not self.connected or not self.redis_client:
            return {"velocity_1h": 0, "velocity_24h": 0, "amount_sum_24h": 0.0}

        try:
            now = int(time.time())

            key_1h = self._get_key(user_id, "1h")
            key_24h = self._get_key(user_id, "24h")
            key_amount = self._get_key(user_id, "amount_24h")

            pipe = self.redis_client.pipeline()

            # Clean expired and count
            pipe.zremrangebyscore(key_1h, 0, now - self.WINDOW_1H)
            pipe.zremrangebyscore(key_24h, 0, now - self.WINDOW_24H)
            pipe.zcard(key_1h)
            pipe.zcard(key_24h)

            results = await pipe.execute()

            velocity_1h = results[-2]
            velocity_24h = results[-1]

            # Get amount sum
            amount_entries = await self.redis_client.zrange(key_amount, 0, -1)
            amount_sum_24h = sum(
                float(entry.split(":")[-1])
                for entry in amount_entries
                if ":" in entry
            )

            return {
                "velocity_1h": velocity_1h,
                "velocity_24h": velocity_24h,
                "amount_sum_24h": amount_sum_24h
            }

        except Exception as e:
            logger.error(f"Error getting velocity: {e}")
            return {"velocity_1h": 0, "velocity_24h": 0, "amount_sum_24h": 0.0}


# Global instance
velocity_tracker = VelocityTracker()
