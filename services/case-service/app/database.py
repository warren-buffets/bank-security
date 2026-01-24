import os
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Float, String, Boolean, JSON, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey, DECIMAL
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Table

# --- Configuration for DB connection ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres_dev@postgres:5432/safeguard")

Base = declarative_base()

# Explicitly declare the 'events' table for foreign key resolution
# Use Base.metadata so SQLAlchemy can resolve the foreign key
events_table = Table(
    "events", Base.metadata,
    Column("event_id", String, primary_key=True),
    extend_existing=True  # Allow redefining if already defined implicitly
)

class CaseDB(Base):
    __tablename__ = "cases"

    case_id = Column(String, primary_key=True, default=lambda: str(uuid4()), unique=True, nullable=False)
    event_id = Column(String, ForeignKey("events.event_id"), nullable=False, index=True) # event_id is also a FK to events(event_id)
    queue = Column(String, nullable=False)
    status = Column(String, nullable=False, default="open") # 'open','in_progress','closed' in SQL
    assignee = Column(String, nullable=True)
    priority = Column(Integer, nullable=False, default=0)
    notes = Column(Text, nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    resolution = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), default=func.now(), nullable=False)

    labels = relationship(
        "LabelDB",
        back_populates="case",
        primaryjoin="CaseDB.event_id == foreign(LabelDB.event_id)",
        viewonly=True
    )

class LabelDB(Base):
    __tablename__ = "labels"

    event_id = Column(String, ForeignKey("events.event_id"), primary_key=True, nullable=False) # FK to events.event_id
    label = Column(String, primary_key=True, nullable=False) # 'fraud','legit','chargeback','fp'
    source = Column(String, primary_key=True, nullable=False) # 'analyst', 'customer', 'chargeback_system'
    
    confidence = Column(DECIMAL(3, 2), nullable=True)
    ts = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    metadata_ = Column(JSON, nullable=True) # Renamed to metadata_ to avoid conflict with SQLAlchemy's internal 'metadata'

    # The relationship to CaseDB is indirect via event_id
    case = relationship(
        "CaseDB",
        back_populates="labels",
        primaryjoin="foreign(LabelDB.event_id) == CaseDB.event_id",
        viewonly=True
    )

# --- Async Database Engine and Session ---
async_engine = create_async_engine(DATABASE_URL, echo=False) # echo=True for debugging SQL queries

AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
