"""
Pydantic models for the Rules Service.
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class TransactionContext(BaseModel):
    """Transaction context for rule evaluation."""
    
    transaction_id: str = Field(..., description="Unique transaction identifier")
    user_id: str = Field(..., description="User identifier")
    amount: float = Field(..., description="Transaction amount")
    currency: str = Field(default="USD", description="Currency code")
    merchant_id: Optional[str] = Field(None, description="Merchant identifier")
    merchant_category: Optional[str] = Field(None, description="Merchant category code")
    geo: Optional[str] = Field(None, description="Transaction geolocation (country/city)")
    user_home_geo: Optional[str] = Field(None, description="User's home geolocation")
    ip_address: Optional[str] = Field(None, description="IP address")
    device_id: Optional[str] = Field(None, description="Device identifier")
    payment_method: Optional[str] = Field(None, description="Payment method type")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Transaction timestamp")
    
    # Velocity data (optional, can be pre-computed)
    tx_count_24h: Optional[int] = Field(None, description="Transaction count in last 24h")
    amount_sum_24h: Optional[float] = Field(None, description="Amount sum in last 24h")
    tx_count_1h: Optional[int] = Field(None, description="Transaction count in last 1h")
    
    # Additional context
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "tx_123456",
                "user_id": "user_789",
                "amount": 1500.00,
                "currency": "USD",
                "merchant_id": "merch_456",
                "merchant_category": "electronics",
                "geo": "US",
                "user_home_geo": "US",
                "ip_address": "192.168.1.1",
                "device_id": "dev_abc",
                "payment_method": "credit_card",
                "tx_count_24h": 3,
                "amount_sum_24h": 2500.00
            }
        }


class MatchedRule(BaseModel):
    """A rule that matched the transaction."""
    
    rule_id: str = Field(..., description="Rule identifier")
    rule_name: str = Field(..., description="Rule name")
    expression: str = Field(..., description="Rule expression/DSL")
    action: str = Field(..., description="Action: deny, review, allow")
    reason: str = Field(..., description="Reason for match")
    priority: int = Field(..., description="Rule priority")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Rule metadata")


class EvaluationRequest(BaseModel):
    """Request for rule evaluation."""
    
    context: TransactionContext = Field(..., description="Transaction context")
    check_lists: bool = Field(default=True, description="Check deny/allow lists")
    
    class Config:
        json_schema_extra = {
            "example": {
                "context": {
                    "transaction_id": "tx_123456",
                    "user_id": "user_789",
                    "amount": 1500.00,
                    "geo": "RU",
                    "user_home_geo": "US"
                },
                "check_lists": True
            }
        }


class ListMatch(BaseModel):
    """Match from deny/allow list."""
    
    list_type: str = Field(..., description="Type of list: deny or allow")
    list_name: str = Field(..., description="Name of the list")
    matched_value: str = Field(..., description="Value that matched")
    field: str = Field(..., description="Field that was checked")
    reason: str = Field(..., description="Reason for match")


class EvaluationResponse(BaseModel):
    """Response from rule evaluation."""
    
    transaction_id: str = Field(..., description="Transaction identifier")
    should_deny: bool = Field(..., description="Whether transaction should be denied")
    should_review: bool = Field(default=False, description="Whether transaction should be reviewed")
    matched_rules: List[MatchedRule] = Field(default_factory=list, description="Rules that matched")
    list_matches: List[ListMatch] = Field(default_factory=list, description="List matches")
    evaluation_time_ms: float = Field(..., description="Evaluation time in milliseconds")
    reasons: List[str] = Field(default_factory=list, description="Reasons for decision")
    
    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "tx_123456",
                "should_deny": True,
                "should_review": False,
                "matched_rules": [
                    {
                        "rule_id": "rule_001",
                        "rule_name": "High Amount Foreign Transaction",
                        "expression": "amount > 1000 AND geo != user_home_geo",
                        "action": "deny",
                        "reason": "Large transaction from foreign country",
                        "priority": 10,
                        "metadata": {}
                    }
                ],
                "list_matches": [],
                "evaluation_time_ms": 12.5,
                "reasons": ["Large transaction from foreign country"]
            }
        }


class Rule(BaseModel):
    """Rule model from database."""
    
    id: str = Field(..., description="Rule ID")
    name: str = Field(..., description="Rule name")
    expression: str = Field(..., description="Rule expression in DSL")
    action: str = Field(..., description="Action: deny, review, allow")
    priority: int = Field(default=0, description="Rule priority (higher = first)")
    enabled: bool = Field(default=True, description="Whether rule is enabled")
    description: Optional[str] = Field(None, description="Rule description")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Update timestamp")


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    dependencies: Dict[str, str] = Field(default_factory=dict, description="Dependency statuses")
