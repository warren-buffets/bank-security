"""Configuration settings for the Model Serving service."""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Service configuration
    service_name: str = "safeguard-model-serving"
    host: str = "0.0.0.0"
    port: int = 8001
    workers: int = 1

    # Model configuration - Kaggle model
    model_path: str = "/app/artifacts/models/fraud_lgbm_kaggle.bin"
    max_prediction_time_ms: int = 30

    # Feature configuration - Kaggle model features (12 features)
    expected_features: list = [
        "amt",
        "trans_hour",
        "trans_day",
        "merchant_mcc",
        "card_type",
        "channel",
        "is_international",
        "is_night",
        "is_weekend",
        "amount_category",
        "distance_category",  # NEW - calculated from geo
        "city_pop"            # NEW - optional from context
    ]

    # Default values for optional features
    default_city_pop: int = 100000        # Average city population
    default_distance_category: int = 1     # 10-50km (medium distance)

    # Metrics configuration
    enable_metrics: bool = True
    metrics_port: int = 9090

    class Config:
        env_prefix = "MODEL_SERVING_"
        case_sensitive = False


settings = Settings()
