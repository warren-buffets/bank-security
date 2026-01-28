"""Transaction and generation request/response models."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TransactionType(str, Enum):
    """Type of transaction."""
    PURCHASE = "purchase"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    REFUND = "refund"
    PAYMENT = "payment"


class FraudScenario(str, Enum):
    """Fraud scenario type."""
    CARD_TESTING = "card_testing"
    ACCOUNT_TAKEOVER = "account_takeover"
    IDENTITY_THEFT = "identity_theft"
    MERCHANT_FRAUD = "merchant_fraud"
    MONEY_LAUNDERING = "money_laundering"
    PHISHING = "phishing"
    CHARGEBACK_FRAUD = "chargeback_fraud"


class Transaction(BaseModel):
    """Synthetic transaction model."""
    transaction_id: str
    user_id: str
    merchant_id: Optional[str] = None
    amount: float = Field(..., gt=0)
    currency: str = "EUR"
    transaction_type: TransactionType = TransactionType.PURCHASE
    timestamp: datetime
    country: str
    city: Optional[str] = None
    ip_address: Optional[str] = None
    device_id: Optional[str] = None
    card_last4: Optional[str] = None
    is_fraud: bool = False
    fraud_scenarios: List[FraudScenario] = Field(default_factory=list)
    explanation: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    batch_id: Optional[str] = None

    class Config:
        use_enum_values = False


class GenerateRequest(BaseModel):
    """Request for generating synthetic transactions."""
    count: int = Field(..., ge=1, le=100000, description="Number of transactions to generate")
    fraud_ratio: float = Field(default=0.1, ge=0, le=1, description="Ratio of fraudulent transactions")
    scenarios: Optional[List[FraudScenario]] = None
    currency: str = "EUR"
    countries: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    seed: Optional[int] = None


class GenerateResponse(BaseModel):
    """Response after generating transactions."""
    batch_id: str
    generated: int
    fraudulent: int
    legit: int
    s3_uri: Optional[str] = None
    latency_ms: int
    transactions: Optional[List[Transaction]] = None
