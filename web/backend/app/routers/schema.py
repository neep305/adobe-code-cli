"""Schema management API router."""

import json
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import AEPConfig, Dataset, Schema, User
from app.utils.sample_records import load_records_from_bytes

_SRC = Path(__file__).resolve().parent.parent.parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from adobe_experience.schema.xdm import XDMSchemaAnalyzer  # noqa: E402

router = APIRouter()

PROFILE_CLASS = "https://ns.adobe.com/xdm/context/profile"
EXPERIENCE_EVENT_CLASS = "https://ns.adobe.com/xdm/context/experienceevent"
_MAX_SAMPLE_ROWS = 500
_MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def _slug_title(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s or "schema"


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


class SuggestResponse(BaseModel):
    """Response for schema metadata suggestion."""
    class_id: str
    class_reasoning: str
    description: str


@router.post("/suggest", response_model=SuggestResponse)
async def suggest_schema_metadata(
    file: UploadFile = File(...),
    title: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuggestResponse:
    """Suggest XDM class and description from sample file content using heuristics."""
    filename = file.filename or ""
    if not filename.lower().endswith((".csv", ".json")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be .csv or .json")

    content = await file.read()
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File too large")

    try:
        records = load_records_from_bytes(content, filename)
    except Exception:
        records = []

    sample = records[:20] if records else []
    columns: List[str] = list(sample[0].keys()) if sample else []
    col_lower = [c.lower() for c in columns]

    event_keywords = {
        "timestamp", "event_type", "event_name", "event_id", "session_id", "page_url",
        "page_name", "action", "click", "referrer", "visit_id", "hit_id", "interaction",
        "pageview", "page_view", "touchpoint", "event_time", "event_date",
    }
    profile_keywords = {
        "email", "first_name", "last_name", "full_name", "phone", "address", "city",
        "country", "zip", "postal", "loyalty", "tier", "birth_date", "birthdate",
        "gender", "age", "preference", "customer_id", "account_id", "crm_id",
        "subscriber", "membership",
    }

    event_score = sum(1 for c in col_lower if any(k in c for k in event_keywords))
    profile_score = sum(1 for c in col_lower if any(k in c for k in profile_keywords))
    has_timestamp = any(
        c in ("ts", "time", "date", "datetime", "created_at", "updated_at")
        or "timestamp" in c or "event_time" in c
        for c in col_lower
    )

    is_event = event_score > profile_score or (
        has_timestamp and event_score > 0 and event_score >= profile_score
    )

    title_clean = (title or "").strip() or "Schema"
    col_preview = ", ".join(columns[:5])
    if len(columns) > 5:
        col_preview += f" + {len(columns) - 5} more"

    if is_event:
        matched = [c for c in columns if any(k in c.lower() for k in event_keywords)]
        sample_cols = ", ".join(matched[:3]) if matched else col_preview
        class_id = EXPERIENCE_EVENT_CLASS
        class_label = "Experience Event"
        reasoning = (
            f"Your data looks like time-based behavioral events. "
            f"Detected event-related columns: {sample_cols}. "
            f"Experience Event is recommended for page views, clicks, purchases, and other actions that happen at a specific point in time."
        )
    else:
        matched = [c for c in columns if any(k in c.lower() for k in profile_keywords)]
        sample_cols = ", ".join(matched[:3]) if matched else col_preview
        class_id = PROFILE_CLASS
        class_label = "Individual Profile"
        reasoning = (
            f"Your data looks like customer attribute records. "
            f"Detected profile-related columns: {sample_cols}. "
            f"Individual Profile is recommended for identity attributes, contact details, preferences, and loyalty data that describe who a customer is."
        )

    num_cols = len(columns)
    description = (
        f"{title_clean} — {class_label} schema with {num_cols} field(s) ({col_preview})."
        if num_cols > 0
        else f"{title_clean} — {class_label} schema."
    )

    return SuggestResponse(class_id=class_id, class_reasoning=reasoning, description=description)


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


@router.post("/generate", response_model=SchemaDetailResponse)
async def generate_schema_from_sample(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    class_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SchemaDetailResponse:
    """Generate XDM schema draft from CSV/JSON sample and persist to DB (no AEP upload).

    Human review is expected before registering to AEP Schema Registry.
    """
    filename = file.filename or ""
    if not filename.lower().endswith((".csv", ".json")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be .csv or .json",
        )

    content = await file.read()
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large (max {_MAX_UPLOAD_BYTES // (1024 * 1024)}MB)",
        )

    try:
        records = load_records_from_bytes(content, filename)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e) or "Invalid file contents",
        ) from e

    if not records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data rows found in file",
        )

    records = records[:_MAX_SAMPLE_ROWS]

    cfg_result = await db.execute(
        select(AEPConfig).where(AEPConfig.user_id == current_user.id).limit(1)
    )
    cfg = cfg_result.scalar_one_or_none()
    tenant_id = cfg.tenant_id if cfg else None

    effective_class = (class_id or "").strip() or PROFILE_CLASS
    if effective_class not in (PROFILE_CLASS, EXPERIENCE_EVENT_CLASS):
        if not effective_class.startswith("https://"):
            effective_class = PROFILE_CLASS

    title_clean = title.strip()
    if not title_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Title is required",
        )

    try:
        xdm_schema = XDMSchemaAnalyzer.from_sample_data(
            records,
            schema_name=title_clean,
            schema_description=description,
            tenant_id=tenant_id,
            class_id=effective_class,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    definition_dict = xdm_schema.model_dump(mode="json", by_alias=True, exclude_none=True)

    aep_local_id = f"local-{uuid.uuid4()}"
    name_slug = _slug_title(title_clean)

    row = Schema(
        user_id=current_user.id,
        aep_schema_id=aep_local_id,
        name=name_slug,
        title=title_clean,
        description=description,
        class_id=effective_class,
        definition_json=json.dumps(definition_dict),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    return SchemaDetailResponse(
        id=row.id,
        aep_schema_id=row.aep_schema_id,
        name=row.name,
        title=row.title,
        description=row.description,
        class_id=row.class_id,
        dataset_count=0,
        definition=definition_dict,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


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
