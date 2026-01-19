from fastapi import FastAPI, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional, Dict
from uuid import UUID
from datetime import datetime, date
from sqlalchemy.sql import func

import asyncio
from contextlib import asynccontextmanager # Add func import here for statistics endpoint

from .database import get_db, CaseDB, LabelDB
from .models import (
    Case, CaseCreate, CaseUpdate,
    Label, LabelCreate, CaseWithLabel,
    CaseQueue, CaseStatusSQL, LabelType, LabelSource,
    Statistics
)
from .kafka_consumer import consume_messages

# Define lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup event
    print("Starting Case Service application lifespan...")
    # Start Kafka consumer in a background task
    task = asyncio.create_task(consume_messages())
    app.state.kafka_consumer_task = task # Store task reference
    yield
    # Shutdown event
    print("Shutting down Case Service application lifespan...")
    # Cancel the Kafka consumer task
    if app.state.kafka_consumer_task:
        app.state.kafka_consumer_task.cancel()
        try:
            await app.state.kafka_consumer_task
        except asyncio.CancelledError:
            print("Kafka consumer task cancelled successfully.")
    print("Case Service application lifespan finished.")

app = FastAPI(
    title="Case Service",
    description="Service for managing fraud cases and analyst feedback",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan # Attach the lifespan context manager
)

@app.get("/health", status_code=status.HTTP_200_OK, summary="Health check endpoint")
async def health_check():
    """
    Checks the health of the Case Service.
    """
    return {"status": "healthy", "service": "Case Service"}

@app.post("/v1/cases", response_model=Case, status_code=status.HTTP_201_CREATED, summary="Create a new fraud case")
async def create_case(case_data: CaseCreate, db: AsyncSession = Depends(get_db)):
    """
    Creates a new fraud case.
    This endpoint is primarily for internal use or testing, as cases will mainly be created by the Kafka consumer.
    """
    new_case = CaseDB(**case_data.model_dump(exclude_unset=True))
    db.add(new_case)
    await db.commit()
    await db.refresh(new_case)
    return Case.model_validate(new_case)

@app.get("/v1/cases", response_model=List[Case], summary="List all fraud cases")
async def list_cases(
    status_filter: Optional[CaseStatusSQL] = Query(None, alias="status"),
    queue_filter: Optional[CaseQueue] = Query(None, alias="queue"),
    event_id_filter: Optional[str] = Query(None, alias="event_id"),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves a list of fraud cases, with optional filtering by status, queue, or event ID.
    """
    query = select(CaseDB)
    if status_filter:
        query = query.where(CaseDB.status == status_filter.value)
    if queue_filter:
        query = query.where(CaseDB.queue == queue_filter.value)
    if event_id_filter:
        query = query.where(CaseDB.event_id == event_id_filter)

    result = await db.execute(query)
    cases = result.scalars().all()
    return [Case.model_validate(c) for c in cases]

@app.get("/v1/cases/{case_id}", response_model=CaseWithLabel, summary="Get details of a specific fraud case")
async def get_case(case_id: str, db: AsyncSession = Depends(get_db)): # case_id is str
    """
    Retrieves the details of a single fraud case, including all associated labels if available.
    """
    query = select(CaseDB).where(CaseDB.case_id == case_id) # Use case_id here
    result = await db.execute(query)
    case_db = result.scalars().first()

    if not case_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    # Fetch labels associated with the case's event_id
    labels_query = select(LabelDB).where(LabelDB.event_id == case_db.event_id)
    labels_result = await db.execute(labels_query)
    labels_db = labels_result.scalars().all()

    case_with_label = CaseWithLabel.model_validate(case_db)
    case_with_label.labels = [Label.model_validate(lbl) for lbl in labels_db] # Assign list of labels
    
    return case_with_label

@app.put("/v1/cases/{case_id}", response_model=Case, summary="Update an existing fraud case")
async def update_case(case_id: str, case_update: CaseUpdate, db: AsyncSession = Depends(get_db)): # case_id is str
    """
    Updates the details of an existing fraud case.
    """
    query = select(CaseDB).where(CaseDB.case_id == case_id) # Use case_id here
    result = await db.execute(query)
    case_db = result.scalars().first()

    if not case_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    update_data = case_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(case_db, key, value)
    
    db.add(case_db)
    await db.commit()
    await db.refresh(case_db)
    return Case.model_validate(case_db)

@app.post("/v1/cases/{case_id}/label", response_model=Label, status_code=status.HTTP_201_CREATED, summary="Label a fraud case")
async def label_case(case_id: str, label_data: LabelCreate, db: AsyncSession = Depends(get_db)): # case_id is str
    """
    Applies a label (fraud or legitimate) to a specific fraud case's associated event.
    Automatically updates the case status to 'in_progress' if it was 'open'.
    """
    # First, find the case to get its event_id
    case_query = select(CaseDB).where(CaseDB.case_id == case_id)
    case_result = await db.execute(case_query)
    case_db = case_result.scalars().first()

    if not case_db:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Case not found or case_id mismatch")
    
    # Ensure label_data's event_id matches the case's event_id
    if label_data.event_id != case_db.event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Label's event_id must match the case's event_id"
        )

    # Create the label
    new_label = LabelDB(**label_data.model_dump())
    db.add(new_label)

    # Update case status to IN_PROGRESS if it's currently OPEN
    if case_db.status == CaseStatusSQL.OPEN.value:
        case_db.status = CaseStatusSQL.IN_PROGRESS.value
        db.add(case_db)

    await db.commit()
    await db.refresh(new_label)
    return Label.model_validate(new_label)

@app.get("/v1/stats", response_model=Statistics, summary="Get fraud detection statistics")
async def get_statistics(db: AsyncSession = Depends(get_db)):
    """
    Retrieves aggregated statistics about fraud cases.
    """
    total_cases_result = await db.execute(select(func.count(CaseDB.case_id)))
    total_cases = total_cases_result.scalar_one()

    open_cases_result = await db.execute(select(func.count(CaseDB.case_id)).where(CaseDB.status == CaseStatusSQL.OPEN.value))
    open_cases = open_cases_result.scalar_one()

    in_progress_cases_result = await db.execute(select(func.count(CaseDB.case_id)).where(CaseDB.status == CaseStatusSQL.IN_PROGRESS.value))
    in_progress_cases = in_progress_cases_result.scalar_one()

    closed_cases_result = await db.execute(select(func.count(CaseDB.case_id)).where(CaseDB.status == CaseStatusSQL.CLOSED.value))
    closed_cases = closed_cases_result.scalar_one()

    # Fraud rate among closed cases
    fraud_labels_on_closed_result = await db.execute(
        select(func.count(LabelDB.event_id))
        .join(CaseDB, CaseDB.event_id == LabelDB.event_id)
        .where(CaseDB.status == CaseStatusSQL.CLOSED.value)
        .where(LabelDB.label == LabelType.FRAUD.value)
    )
    fraud_labels_on_closed = fraud_labels_on_closed_result.scalar_one()

    fraud_rate_on_closed = fraud_labels_on_closed / closed_cases if closed_cases > 0 else 0.0

    cases_per_day_result = await db.execute(
        select(
            func.to_char(CaseDB.created_at, 'YYYY-MM-DD').label('day'),
            func.count(CaseDB.case_id).label('count')
        )
        .group_by('day')
        .order_by('day')
    )
    cases_per_day_data: Dict[str, int] = {row.day: row.count for row in cases_per_day_result.all()}

    return Statistics(
        total_cases=total_cases,
        open_cases=open_cases,
        in_progress_cases=in_progress_cases,
        closed_cases=closed_cases,
        fraud_rate_on_closed=fraud_rate_on_closed,
        cases_per_day=cases_per_day_data
    )
