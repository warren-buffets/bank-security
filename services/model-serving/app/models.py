"""Pydantic models for request/response validation."""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class TransactionFeatures(BaseModel):
    """Input features for fraud prediction."""
    amount: float = Field(..., description="Transaction amount", ge=0)
    hour: int = Field(..., description="Hour of day (0-23)", ge=0, le=23)
    day_of_week: int = Field(..., description="Day of week (0-6)", ge=0, le=6)
    merchant_risk_score: float = Field(..., description="Merchant risk score", ge=0, le=1)
    card_present: int = Field(..., description="Card present (0 or 1)", ge=0, le=1)
    international: int = Field(..., description="International transaction (0 or 1)", ge=0, le=1)
    high_risk_country: int = Field(..., description="High risk country (0 or 1)", ge=0, le=1)
    velocity_1h: int = Field(..., description="Transactions in last 1 hour", ge=0)
    velocity_24h: int = Field(..., description="Transactions in last 24 hours", ge=0)
    avg_amount_30d: float = Field(..., description="Average amount in last 30 days", ge=0)

    class Config:
        json_schema_extra = {
            "example": {
                "amount": 125.50,
                "hour": 14,
                "day_of_week": 3,
                "merchant_risk_score": 0.25,
                "card_present": 1,
                "international": 0,
                "high_risk_country": 0,
                "velocity_1h": 2,
                "velocity_24h": 8,
                "avg_amount_30d": 95.30
            }
        }


class PredictionRequest(BaseModel):
    """Request model for fraud prediction."""
    transaction_id: Optional[str] = Field(None, description="Optional transaction ID for tracking")
    features: TransactionFeatures = Field(..., description="Transaction features")


class PredictionResponse(BaseModel):
    """Response model for fraud prediction."""
    transaction_id: Optional[str] = Field(None, description="Transaction ID if provided")
    fraud_score: float = Field(..., description="Fraud probability score (0-1)", ge=0, le=1)
    prediction_time_ms: float = Field(..., description="Prediction latency in milliseconds")
    model_version: str = Field(..., description="Model version used")


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
