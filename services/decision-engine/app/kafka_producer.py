"""
Kafka event producer.
"""
import logging
from typing import Dict, Any, Optional
from aiokafka import AIOKafkaProducer
import json
from app.config import settings

logger = logging.getLogger(__name__)


class KafkaEventProducer:
    """Async Kafka producer for decision events."""
    
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self.enabled = settings.KAFKA_ENABLE
    
    async def start(self):
        """Start Kafka producer."""
        if not self.enabled:
            logger.info("Kafka publishing disabled")
            return
        
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                compression_type='gzip',
                request_timeout_ms=5000,
                max_request_size=1048576  # 1MB
            )
            await self.producer.start()
            logger.info(f"Kafka producer started: {settings.KAFKA_BOOTSTRAP_SERVERS}")
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            self.enabled = False
    
    async def stop(self):
        """Stop Kafka producer."""
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")
    
    async def publish_decision_event(
        self,
        event_id: str,
        decision_id: str,
        decision: str,
        score: Optional[float],
        tenant_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Publish decision event to Kafka.
        
        Args:
            event_id: Transaction event ID
            decision_id: Decision ID
            decision: Decision type (ALLOW, CHALLENGE, DENY)
            score: ML score
            tenant_id: Tenant identifier
            metadata: Additional metadata
        """
        if not self.enabled or not self.producer:
            logger.debug("Kafka publishing disabled, skipping event")
            return
        
        try:
            event = {
                "event_id": event_id,
                "decision_id": decision_id,
                "decision": decision,
                "score": score,
                "tenant_id": tenant_id,
                "timestamp": None,  # Will be set by Kafka
                "metadata": metadata or {}
            }
            
            await self.producer.send_and_wait(
                settings.KAFKA_TOPIC_DECISIONS,
                value=event,
                key=event_id.encode('utf-8')
            )
            
            logger.debug(f"Published decision event: {decision_id} -> {decision}")
            
        except Exception as e:
            logger.error(f"Error publishing decision event: {e}")
            # Fail gracefully - don't block decision response
    
    async def publish_case_event(
        self,
        event_id: str,
        decision_id: str,
        decision: str,
        score: Optional[float],
        priority: int,
        queue: str,
        tenant_id: str
    ):
        """
        Publish case creation event to Kafka.
        
        Args:
            event_id: Transaction event ID
            decision_id: Decision ID
            decision: Decision type
            score: ML score
            priority: Case priority (0=low, 1=medium, 2=high)
            queue: Case queue name
            tenant_id: Tenant identifier
        """
        if not self.enabled or not self.producer:
            logger.debug("Kafka publishing disabled, skipping case event")
            return
        
        try:
            event = {
                "event_id": event_id,
                "decision_id": decision_id,
                "decision": decision,
                "score": score,
                "priority": priority,
                "queue": queue,
                "tenant_id": tenant_id,
                "timestamp": None
            }
            
            await self.producer.send_and_wait(
                settings.KAFKA_TOPIC_CASES,
                value=event,
                key=event_id.encode('utf-8')
            )
            
            logger.debug(f"Published case event: {decision_id} -> queue={queue}")
            
        except Exception as e:
            logger.error(f"Error publishing case event: {e}")


# Global instance
kafka_producer = KafkaEventProducer()
