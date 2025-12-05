"""Configuration settings for the Model Serving service."""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Service configuration
    service_name: str = "fraudguard-model-serving"
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    
    # Model configuration
    model_path: str = "/models/gbdt_v1.bin"
    max_prediction_time_ms: int = 30
    
    # Feature configuration
    expected_features: list = [
        "amount",
        "hour",
        "day_of_week",
        "merchant_risk_score",
        "card_present",
        "international",
        "high_risk_country",
        "velocity_1h",
        "velocity_24h",
        "avg_amount_30d"
    ]
    
    # Metrics configuration
    enable_metrics: bool = True
    metrics_port: int = 9090
    
    class Config:
        env_prefix = "MODEL_SERVING_"
        case_sensitive = False


settings = Settings()
