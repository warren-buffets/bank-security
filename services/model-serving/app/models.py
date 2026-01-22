"""Pydantic models for request/response validation."""
from typing import Dict, Optional
from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    """Request model for fraud prediction - Kaggle model with optional geo fields."""
    event_id: str = Field(..., description="Event/transaction ID")
    amount: float = Field(..., description="Transaction amount", ge=0)
    currency: str = Field(default="EUR", description="Currency code")
    merchant: Dict = Field(..., description="Merchant information (mcc, country, lat*, long*)")
    card: Dict = Field(..., description="Card information")
    context: Dict = Field(..., description="Transaction context (channel, city_pop*, user_lat*, user_long*)")
    timestamp: Optional[str] = Field(None, description="Transaction timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "evt_12345",
                "amount": 125.50,
                "currency": "EUR",
                "merchant": {
                    "id": "m123", 
                    "mcc": "5411", 
                    "country": "FR",
                    "lat": 48.8566,      # Optional
                    "long": 2.3522       # Optional
                },
                "card": {"card_id": "c123", "type": "physical", "user_id": "u123"},
                "context": {
                    "ip": "1.2.3.4", 
                    "geo": "FR", 
                    "device_id": "d123", 
                    "channel": "app",
                    "city_pop": 2200000,  # Optional
                    "user_lat": 48.8534,  # Optional
                    "user_long": 2.3488   # Optional
                }
            }
        }


class PredictionResponse(BaseModel):
    """Response model for fraud prediction."""
    event_id: str = Field(..., description="Event ID")
    score: float = Field(..., description="Fraud probability score (0-1)", ge=0, le=1)
    top_features: list = Field(default_factory=list, description="Top contributing features")
    model_version: str = Field(..., description="Model version used")
    prediction_time_ms: float = Field(..., description="Prediction latency in milliseconds")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    model_loaded: bool = Field(..., description="Whether model is loaded")
    model_path: str = Field(..., description="Path to model file")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")
