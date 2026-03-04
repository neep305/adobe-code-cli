"""Pydantic schemas for Dataset operations."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DatasetCreateRequest(BaseModel):
    """Request schema for creating a dataset."""
    name: str = Field(..., min_length=1, max_length=255)
    schema_id: int
    description: Optional[str] = None
    enable_profile: bool = False
    enable_identity: bool = False


class DatasetUpdateRequest(BaseModel):
    """Request schema for updating a dataset."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    profile_enabled: Optional[bool] = None
    identity_enabled: Optional[bool] = None


class DatasetResponse(BaseModel):
    """Response schema for dataset."""
    id: int
    aep_dataset_id: str
    schema_id: Optional[int] = None
    schema_name: Optional[str] = None
    name: str
    description: Optional[str] = None
    profile_enabled: bool
    identity_enabled: bool
    state: str  # DRAFT, ENABLED
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class DatasetListResponse(BaseModel):
    """Response schema for dataset list."""
    datasets: List[DatasetResponse]
    total: int
    page: int = 1
    page_size: int = 50


class DatasetWithBatchesResponse(DatasetResponse):
    """Dataset response with batch information."""
    active_batches: int = 0
    total_batches: int = 0
    last_ingestion_at: Optional[datetime] = None
