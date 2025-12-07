"""Configuration settings for the Model Serving service."""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Service configuration
    service_name: str = "fraudguard-model-serving"
    host: str = "0.0.0.0"
    port: int = 8001
    workers: int = 1

    # Model configuration
    model_path: str = "/models/gbdt_v1.bin"
    max_prediction_time_ms: int = 30

    # Feature configuration - MVP features
    expected_features: list = [
        "amount",
        "trans_hour",
        "trans_day",
        "merchant_mcc",
        "merchant_country",
        "card_type",
        "channel",
        "is_international",
        "is_night",
        "is_weekend",
        "amount_category"
    ]

    # Metrics configuration
    enable_metrics: bool = True
    metrics_port: int = 9090

    class Config:
        env_prefix = "MODEL_SERVING_"
        case_sensitive = False


settings = Settings()
