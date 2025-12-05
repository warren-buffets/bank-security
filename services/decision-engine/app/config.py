"""
Configuration settings for Decision Engine service.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Service config
    SERVICE_NAME: str = "decision-engine"
    VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Timeouts and budgets (milliseconds)
    ORCHESTRATION_TIMEOUT_MS: int = 15
    MODEL_SERVING_TIMEOUT_MS: int = 30
    RULES_SERVICE_TIMEOUT_MS: int = 50
    TOTAL_TIMEOUT_MS: int = 100
    
    # External services
    MODEL_SERVING_URL: str = os.getenv("MODEL_SERVING_URL", "http://model-serving:8001")
    RULES_SERVICE_URL: str = os.getenv("RULES_SERVICE_URL", "http://rules-service:8002")
    
    # Redis configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    REDIS_IDEMPOTENCY_TTL: int = 86400  # 24 hours
    
    # PostgreSQL configuration
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "fraudguard")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_MAX_CONNECTIONS: int = 20
    POSTGRES_MIN_CONNECTIONS: int = 5
    
    # Kafka configuration
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_TOPIC_DECISIONS: str = "decision_events"
    KAFKA_TOPIC_CASES: str = "case_events"
    KAFKA_ENABLE: bool = os.getenv("KAFKA_ENABLE", "true").lower() == "true"
    
    # Decision thresholds
    THRESHOLD_LOW_RISK: float = 0.50
    THRESHOLD_HIGH_RISK: float = 0.70
    
    # Tenant configuration
    DEFAULT_TENANT_ID: str = "default"
    
    # Model version
    MODEL_VERSION: str = os.getenv("MODEL_VERSION", "v1.0.0")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Metrics
    METRICS_ENABLED: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def postgres_dsn(self) -> str:
        """Generate PostgreSQL DSN."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


# Global settings instance
settings = Settings()
