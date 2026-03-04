"""Pydantic schemas for Batch operations."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class BatchError(BaseModel):
    """Batch error details."""
    code: str
    message: str
    rows: Optional[List[int]] = None


class BatchStatusResponse(BaseModel):
    """Response schema for batch status."""
    id: int
    aep_batch_id: str
    dataset_id: int
    dataset_name: Optional[str] = None
    status: str  # loading, staged, processing, success, failed, aborted, retrying
    files_count: int
    files_uploaded: int
    progress_percent: float = Field(ge=0, le=100)
    records_processed: Optional[int] = None
    records_failed: Optional[int] = None
    error_message: Optional[str] = None
    errors: List[BatchError] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    model_config = {"from_attributes": True}


class BatchListResponse(BaseModel):
    """Response schema for batch list."""
    batches: List[BatchStatusResponse]
    total: int
    page: int = 1
    page_size: int = 50


class BatchCreateRequest(BaseModel):
    """Request schema for creating a batch."""
    dataset_id: int
    format: str = Field(default="parquet", pattern="^(parquet|json|csv)$")


class BatchCreateResponse(BaseModel):
    """Response schema for batch creation."""
    id: int
    aep_batch_id: str
    dataset_id: int
    status: str
    created_at: datetime


class FileUploadResponse(BaseModel):
    """Response schema for file upload."""
    file_name: str
    file_size: int
    upload_id: str
    status: str  # uploading, completed, failed
    message: Optional[str] = None


class BatchCompleteRequest(BaseModel):
    """Request schema for completing a batch."""
    action: str = Field(default="COMPLETE", pattern="^(COMPLETE|ABORT)$")
