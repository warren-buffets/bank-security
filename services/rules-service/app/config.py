"""
Configuration settings for the Rules Service.
"""
import os
from typing import Optional


class Config:
    """Service configuration."""
    
    # Service
    SERVICE_NAME = "rules-service"
    SERVICE_VERSION = "1.0.0"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8003"))
    
    # Timeouts
    EVALUATION_TIMEOUT_MS = int(os.getenv("EVALUATION_TIMEOUT_MS", "50"))
    
    # PostgreSQL
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB = os.getenv("POSTGRES_DB", "safeguard")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "safeguard")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "safeguard")
    
    @property
    def postgres_dsn(self) -> str:
        """Get PostgreSQL connection DSN."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    # Redis
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    
    # Cache TTLs
    RULES_CACHE_TTL = int(os.getenv("RULES_CACHE_TTL", "300"))  # 5 minutes
    LISTS_CACHE_TTL = int(os.getenv("LISTS_CACHE_TTL", "600"))  # 10 minutes
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Metrics
    METRICS_ENABLED = os.getenv("METRICS_ENABLED", "true").lower() == "true"


config = Config()
