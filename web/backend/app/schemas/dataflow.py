"""Pydantic schemas for Dataflow operations."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class DataflowRunMetrics(BaseModel):
    """Dataflow run metrics."""
    input_record_count: Optional[int] = None
    output_record_count: Optional[int] = None
    failed_record_count: Optional[int] = None
    files_read: Optional[int] = None
    duration_ms: Optional[int] = None


class DataflowRunError(BaseModel):
    """Dataflow run error details."""
    code: str
    message: str
    activity: Optional[str] = None


class DataflowRunResponse(BaseModel):
    """Response schema for dataflow run."""
    id: str
    flow_id: str
    status: str  # pending, inProgress, success, failed, cancelled
    created_at: datetime
    updated_at: datetime
    metrics: Optional[DataflowRunMetrics] = None
    errors: List[DataflowRunError] = Field(default_factory=list)


class DataflowResponse(BaseModel):
    """Response schema for dataflow."""
    id: str
    name: str
    state: str  # enabled, disabled
    source_connection_ids: List[str]
    target_connection_ids: List[str]
    created_at: datetime
    updated_at: datetime
    description: Optional[str] = None


class DataflowHealthError(BaseModel):
    """Aggregated error information."""
    code: str
    message: str
    count: int
    run_ids: List[str]


class DataflowHealthResponse(BaseModel):
    """Response schema for dataflow health analysis."""
    flow_id: str
    flow_name: str
    lookback_days: int
    total_runs: int
    success_runs: int
    failed_runs: int
    pending_runs: int
    success_rate: float = Field(ge=0, le=100)
    avg_duration_seconds: float
    health_status: str  # excellent, good, poor, critical
    errors: List[DataflowHealthError] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class DataflowListResponse(BaseModel):
    """Response schema for dataflow list."""
    dataflows: List[DataflowResponse]
    total: int
