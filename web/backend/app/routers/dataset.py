"""Dataset management API router."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import Dataset, Schema, User

router = APIRouter()


class DatasetResponse(BaseModel):
    """Response schema for a dataset."""
    id: int
    aep_dataset_id: str
    name: str
    description: Optional[str] = None
    profile_enabled: bool
    identity_enabled: bool
    state: str
    schema_id: Optional[int] = None
    schema_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DatasetListResponse(BaseModel):
    """Response schema for dataset list."""
    datasets: List[DatasetResponse]
    total: int


@router.get("", response_model=DatasetListResponse)
async def list_datasets(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    state: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DatasetListResponse:
    """List all datasets for the current user.

    Args:
        limit: Maximum number of datasets to return
        offset: Number of datasets to skip
        state: Filter by state (DRAFT, ACTIVE, etc.)
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of datasets with optional schema info
    """
    query = (
        select(Dataset, Schema)
        .outerjoin(Schema, Dataset.schema_id == Schema.id)
        .where(Dataset.user_id == current_user.id)
    )

    if state:
        query = query.where(Dataset.state == state)

    query = query.order_by(Dataset.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    rows = result.all()

    count_query = select(Dataset).where(Dataset.user_id == current_user.id)
    if state:
        count_query = count_query.where(Dataset.state == state)
    count_result = await db.execute(count_query)
    total = len(count_result.all())

    datasets = [
        DatasetResponse(
            id=dataset.id,
            aep_dataset_id=dataset.aep_dataset_id,
            name=dataset.name,
            description=dataset.description,
            profile_enabled=dataset.profile_enabled,
            identity_enabled=dataset.identity_enabled,
            state=dataset.state,
            schema_id=dataset.schema_id,
            schema_name=schema.name if schema else None,
            created_at=dataset.created_at,
            updated_at=dataset.updated_at,
        )
        for dataset, schema in rows
    ]

    return DatasetListResponse(datasets=datasets, total=total)


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DatasetResponse:
    """Get dataset details.

    Args:
        dataset_id: Database dataset ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Dataset details with schema info
    """
    result = await db.execute(
        select(Dataset, Schema)
        .outerjoin(Schema, Dataset.schema_id == Schema.id)
        .where(Dataset.id == dataset_id, Dataset.user_id == current_user.id)
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found",
        )

    dataset, schema = row
    return DatasetResponse(
        id=dataset.id,
        aep_dataset_id=dataset.aep_dataset_id,
        name=dataset.name,
        description=dataset.description,
        profile_enabled=dataset.profile_enabled,
        identity_enabled=dataset.identity_enabled,
        state=dataset.state,
        schema_id=dataset.schema_id,
        schema_name=schema.name if schema else None,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at,
    )
