"""Batch metadata models."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class BatchCreate(BaseModel):
    """Batch creation record for persistence."""
    batch_id: str
    seed: Optional[int] = None
    scenarios: Optional[List[Any]] = None  # FraudScenario enums or strings
    count: int
    fraud_ratio: float
    generated_count: int
    fraudulent_count: int
    legit_count: int
    s3_uri: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
