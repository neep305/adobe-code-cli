"""Schema management API router."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import Dataset, Schema, User

router = APIRouter()


class SchemaResponse(BaseModel):
    """Response schema for an XDM schema."""
    id: int
    aep_schema_id: str
    name: str
    title: str
    description: Optional[str] = None
    class_id: str
    dataset_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SchemaDetailResponse(SchemaResponse):
    """Detailed schema response including field definition."""
    definition: Dict[str, Any]


class SchemaListResponse(BaseModel):
    """Response schema for schema list."""
    schemas: List[SchemaResponse]
    total: int


@router.get("", response_model=SchemaListResponse)
async def list_schemas(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SchemaListResponse:
    """List all schemas for the current user.

    Args:
        limit: Maximum number of schemas to return
        offset: Number of schemas to skip
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of schemas with dataset count
    """
    query = (
        select(Schema)
        .where(Schema.user_id == current_user.id)
        .order_by(Schema.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    schemas_db = result.scalars().all()

    count_result = await db.execute(
        select(Schema).where(Schema.user_id == current_user.id)
    )
    total = len(count_result.all())

    schema_responses = []
    for schema in schemas_db:
        ds_result = await db.execute(
            select(Dataset).where(Dataset.schema_id == schema.id)
        )
        dataset_count = len(ds_result.all())
        schema_responses.append(
            SchemaResponse(
                id=schema.id,
                aep_schema_id=schema.aep_schema_id,
                name=schema.name,
                title=schema.title,
                description=schema.description,
                class_id=schema.class_id,
                dataset_count=dataset_count,
                created_at=schema.created_at,
                updated_at=schema.updated_at,
            )
        )

    return SchemaListResponse(schemas=schema_responses, total=total)


@router.get("/{schema_id}", response_model=SchemaDetailResponse)
async def get_schema(
    schema_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SchemaDetailResponse:
    """Get schema details including field definition.

    Args:
        schema_id: Database schema ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Schema details with full definition JSON
    """
    result = await db.execute(
        select(Schema).where(Schema.id == schema_id, Schema.user_id == current_user.id)
    )
    schema = result.scalar_one_or_none()

    if not schema:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema {schema_id} not found",
        )

    ds_result = await db.execute(
        select(Dataset).where(Dataset.schema_id == schema.id)
    )
    dataset_count = len(ds_result.all())

    try:
        definition = json.loads(schema.definition_json)
    except (json.JSONDecodeError, TypeError):
        definition = {}

    return SchemaDetailResponse(
        id=schema.id,
        aep_schema_id=schema.aep_schema_id,
        name=schema.name,
        title=schema.title,
        description=schema.description,
        class_id=schema.class_id,
        dataset_count=dataset_count,
        definition=definition,
        created_at=schema.created_at,
        updated_at=schema.updated_at,
    )
