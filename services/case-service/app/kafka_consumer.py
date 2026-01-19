import asyncio
import json
import logging
from aiokafka import AIOKafkaConsumer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .database import AsyncSessionLocal, CaseDB
from .models import CaseCreate, CaseQueue, CaseStatusSQL, Decision

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration for Kafka (will come from config.py or environment variables)
KAFKA_BOOTSTRAP_SERVERS = "kafka:9092"  # Assuming Kafka service name in docker-compose
KAFKA_TOPIC_DECISION_EVENTS = "decision_events"
KAFKA_CONSUMER_GROUP_ID = "case-service-group"

async def consume_messages():
    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC_DECISION_EVENTS,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_CONSUMER_GROUP_ID,
        auto_offset_reset="earliest"
    )
    logger.info(f"Starting Kafka consumer for topic: {KAFKA_TOPIC_DECISION_EVENTS} on servers: {KAFKA_BOOTSTRAP_SERVERS}")
    try:
        await consumer.start()
        logger.info("Kafka consumer started successfully.")
        while True:
            async for msg in consumer:
                logger.info(f"Consumed message: topic={msg.topic}, partition={msg.partition}, offset={msg.offset}")
                
                try:
                    event_data = json.loads(msg.value.decode())
                    decision = event_data.get("decision")
                    
                    # Only create a case if the decision is CHALLENGE or DENY
                    if decision in [Decision.CHALLENGE.value, Decision.DENY.value]:
                        # Map event_data to CaseCreate model fields
                        # Most event_data goes into 'notes' as JSON string
                        case_create_data = CaseCreate(
                            event_id=event_data["event_id"],
                            queue=CaseQueue.REVIEW, # Default to review queue
                            status=CaseStatusSQL.OPEN,   # Default status is open
                            notes=json.dumps(event_data) # Store the full event data as JSON string in notes
                            # assignee, priority, closed_at, resolution are optional, will default to None or 0
                        )

                        async with AsyncSessionLocal() as db:
                            # Check if a case with this event_id already exists to prevent duplicates
                            existing_case_result = await db.execute(select(CaseDB).where(CaseDB.event_id == case_create_data.event_id))
                            if existing_case_result.scalars().first():
                                logger.warning(f"Case with event_id {case_create_data.event_id} already exists. Skipping.")
                                continue

                            new_case = CaseDB(**case_create_data.model_dump())
                            db.add(new_case)
                            await db.commit()
                            await db.refresh(new_case)
                            logger.info(f"Created new case: {new_case.id} for event {new_case.event_id} with decision {new_case.decision}")
                    else:
                        logger.info(f"Decision '{decision}' does not require case creation. Skipping.")

                except json.JSONDecodeError:
                    logger.error(f"Error decoding JSON from message: {msg.value.decode()}")
                except KeyError as e:
                    logger.error(f"Missing key '{e}' in message data: {msg.value.decode()}")
                except Exception as e:
                    logger.error(f"An unexpected error occurred while processing message: {e}", exc_info=True)
    except asyncio.CancelledError:
        logger.info("Kafka consumer task cancelled.")
    except Exception as e:
        logger.error(f"Kafka consumer failed to start or run: {e}", exc_info=True)
    finally:
        logger.info("Stopping Kafka consumer.")
        await consumer.stop()
        logger.info("Kafka consumer stopped.")

