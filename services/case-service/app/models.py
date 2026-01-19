from datetime import datetime
from typing import Optional, Dict, List
from uuid import UUID, uuid4
from enum import Enum

from pydantic import BaseModel, Field, condecimal

# Enums matching SQL table constraints
class Decision(str, Enum): # Re-introduced Decision Enum
    ALLOW = "ALLOW"
    CHALLENGE = "CHALLENGE"
    DENY = "DENY"

class CaseQueue(str, Enum):
    HIGH_RISK = "high_risk"
    MEDIUM_RISK = "medium_risk"
    REVIEW = "review" # Default queue

class CaseStatusSQL(str, Enum): # Renamed to avoid conflict with former CaseStatus
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"

class LabelType(str, Enum):
    FRAUD = "fraud"
    LEGIT = "legit"
    CHARGEBACK = "chargeback"
    FALSE_POSITIVE = "fp"

class LabelSource(str, Enum):
    ANALYST = "analyst"
    CUSTOMER = "customer"
    CHARGEBACK_SYSTEM = "chargeback_system"

class TimestampedModel(BaseModel):
    # case_id is primary key, not a UUID generated here
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# --- Pydantic Models for Cases (aligned with SQL 'cases' table) ---
class CaseCreate(BaseModel):
    event_id: str = Field(..., description="Reference to the original event in the 'events' table.")
    queue: CaseQueue = Field(CaseQueue.REVIEW, description="Assigned queue for investigation.")
    status: CaseStatusSQL = Field(CaseStatusSQL.OPEN, description="Current status of the case.")
    assignee: Optional[str] = Field(None, description="ID of the analyst assigned to the case.")
    priority: int = Field(0, description="Priority level of the case (0=low, 1=medium, 2=high).")
    notes: Optional[str] = Field(None, description="Detailed notes about the case, can include serialized event data.")
    closed_at: Optional[datetime] = Field(None, description="Timestamp when the case was closed.")
    resolution: Optional[str] = Field(None, description="Final resolution of the case.")

class Case(TimestampedModel, CaseCreate):
    case_id: str = Field(..., description="Unique case identifier.") # VARCHAR in SQL
    # The default for created_at and updated_at comes from TimestampedModel

class CaseUpdate(BaseModel):
    queue: Optional[CaseQueue] = Field(None, description="Assigned queue for investigation.")
    status: Optional[CaseStatusSQL] = Field(None, description="Current status of the case.")
    assignee: Optional[str] = Field(None, description="ID of the analyst assigned to the case.")
    priority: Optional[int] = Field(None, description="Priority level of the case (0=low, 1=medium, 2=high).")
    notes: Optional[str] = Field(None, description="Detailed notes about the case, can include serialized event data.")
    closed_at: Optional[datetime] = Field(None, description="Timestamp when the case was closed.")
    resolution: Optional[str] = Field(None, description="Final resolution of the case.")

# --- Pydantic Models for Labels (aligned with SQL 'labels' table) ---
class LabelCreate(BaseModel):
    event_id: str = Field(..., description="Reference to the original event in the 'events' table.")
    label: LabelType = Field(..., description="Type of label (fraud, legit, chargeback, fp).")
    source: LabelSource = Field(..., description="Source of the label (analyst, customer, chargeback_system).")
    confidence: Optional[condecimal(max_digits=3, decimal_places=2)] = Field(None, ge=0.0, le=1.0, description="Confidence score for the label.")
    # ts will be set by DB

class Label(BaseModel): # No TimestampedModel here, ts is specific
    event_id: str
    label: LabelType
    source: LabelSource
    confidence: Optional[condecimal(max_digits=3, decimal_places=2)] = None
    ts: datetime

# --- Composite Models ---
class CaseWithLabel(Case):
    labels: List[Label] = Field([], description="All labels associated with the event of this case.")

class Statistics(BaseModel):
    total_cases: int = Field(..., description="Total number of cases")
    open_cases: int = Field(..., description="Number of cases awaiting review")
    in_progress_cases: int = Field(..., description="Number of cases currently being reviewed")
    closed_cases: int = Field(..., description="Number of cases that have been closed")
    fraud_rate_on_closed: float = Field(..., ge=0.0, le=1.0, description="Calculated fraud rate among closed cases.")
    cases_per_day: Dict[str, int] = Field(..., description="Number of cases per day, keyed by date string (YYYY-MM-DD)")
