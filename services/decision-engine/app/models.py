"""
Pydantic models for request/response validation.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class DecisionType(str, Enum):
    """Decision types."""
    ALLOW = "ALLOW"
    CHALLENGE = "CHALLENGE"
    DENY = "DENY"


class TransactionContext(BaseModel):
    """Transaction context information."""
    ip: Optional[str] = None
    geo: Optional[str] = None
    device_id: Optional[str] = None
    channel: str = Field(..., description="app, web, pos, atm")
    user_agent: Optional[str] = None
    proxy_vpn_flag: Optional[bool] = False


class Card(BaseModel):
    """Card information."""
    card_id: str
    user_id: str
    type: str = Field(..., description="physical, virtual")
    bin: Optional[str] = None


class Merchant(BaseModel):
    """Merchant information."""
    id: str
    name: Optional[str] = None
    mcc: str = Field(..., description="Merchant Category Code")
    country: str


class ScoreRequest(BaseModel):
    """POST /v1/score request payload."""
    event_id: str = Field(..., description="Unique transaction ID")
    tenant_id: str = Field(default="default", description="Tenant identifier")
    amount: float = Field(..., gt=0, description="Transaction amount")
    currency: str = Field(default="EUR", description="Currency code")
    merchant: Merchant
    card: Card
    context: TransactionContext
    has_initial_2fa: bool = Field(default=False, description="Whether 2FA was already performed")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ScoreResponse(BaseModel):
    """POST /v1/score response."""
    event_id: str
    decision_id: str
    decision: DecisionType
    score: Optional[float] = Field(None, ge=0, le=1, description="ML score [0..1]")
    reasons: List[str] = Field(default_factory=list, description="Human-readable reasons")
    rule_hits: List[str] = Field(default_factory=list, description="Rules triggered")
    latency_ms: int = Field(..., description="Total processing time")
    model_version: str
    requires_2fa: bool = Field(default=False, description="Whether 2FA is required")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
    timestamp: datetime
    dependencies: Dict[str, str] = Field(default_factory=dict)


class MetricsResponse(BaseModel):
    """Metrics response."""
    total_requests: int
    decisions_by_type: Dict[str, int]
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
