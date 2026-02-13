"""Pydantic models for Adobe Experience Platform Flow Service."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== Enums ====================


class DataflowState(str, Enum):
    """Dataflow state enumeration."""

    ENABLED = "enabled"
    DISABLED = "disabled"


class RunStatus(str, Enum):
    """Flow run status enumeration."""

    PENDING = "pending"
    IN_PROGRESS = "inProgress"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ==================== Base Models ====================


class ConnectionSpec(BaseModel):
    """Connection specification reference."""

    id: str = Field(..., description="Connection spec ID")
    version: Optional[str] = Field(None, description="Connection spec version")
    name: Optional[str] = Field(None, description="Connection spec name")

    model_config = {"populate_by_name": True}


class FlowSpec(BaseModel):
    """Flow specification reference."""

    id: str = Field(..., description="Flow spec ID")
    version: Optional[str] = Field(None, description="Flow spec version")
    name: Optional[str] = Field(None, description="Flow spec name")

    model_config = {"populate_by_name": True}


# ==================== Dataflow Models ====================


class DataflowSchedule(BaseModel):
    """Dataflow schedule configuration."""

    start_time: Optional[int] = Field(
        None,
        alias="startTime",
        description="Schedule start time (Unix seconds)",
    )
    interval: Optional[int] = Field(
        None,
        description="Interval between runs",
    )
    frequency: Optional[str] = Field(
        None,
        description="Frequency unit (minute, hour, day, week)",
    )

    model_config = {"populate_by_name": True}


class InheritedSourceConnection(BaseModel):
    """Inherited source connection info in dataflow details."""

    id: str = Field(..., description="Source connection ID")
    connection_spec: Optional[ConnectionSpec] = Field(
        None,
        alias="connectionSpec",
        description="Connection specification",
    )

    model_config = {"populate_by_name": True}


class InheritedTargetConnection(BaseModel):
    """Inherited target connection info in dataflow details."""

    id: str = Field(..., description="Target connection ID")
    connection_spec: Optional[ConnectionSpec] = Field(
        None,
        alias="connectionSpec",
        description="Connection specification",
    )

    model_config = {"populate_by_name": True}


class InheritedAttributes(BaseModel):
    """Inherited attributes from connections."""

    source_connections: Optional[List[InheritedSourceConnection]] = Field(
        None,
        alias="sourceConnections",
        description="Source connections with specs",
    )
    target_connections: Optional[List[InheritedTargetConnection]] = Field(
        None,
        alias="targetConnections",
        description="Target connections with specs",
    )

    model_config = {"populate_by_name": True}


class Transformation(BaseModel):
    """Dataflow transformation configuration."""

    name: str = Field(..., description="Transformation name")
    params: Optional[Dict[str, Any]] = Field(
        None,
        description="Transformation parameters",
    )

    model_config = {"populate_by_name": True}


class Dataflow(BaseModel):
    """Adobe Experience Platform Dataflow object.
    
    A dataflow represents a data ingestion pipeline from a source
    to a target (typically an AEP dataset).
    """

    id: str = Field(..., description="Dataflow ID")
    name: str = Field(..., description="Dataflow name")
    description: Optional[str] = Field(None, description="Dataflow description")
    flow_spec: FlowSpec = Field(
        ...,
        alias="flowSpec",
        description="Flow specification",
    )
    source_connection_ids: List[str] = Field(
        ...,
        alias="sourceConnectionIds",
        description="Source connection IDs",
    )
    target_connection_ids: List[str] = Field(
        ...,
        alias="targetConnectionIds",
        description="Target connection IDs",
    )
    transformations: Optional[List[Transformation]] = Field(
        None,
        description="Data transformations",
    )
    schedule_params: Optional[DataflowSchedule] = Field(
        None,
        alias="scheduleParams",
        description="Schedule configuration",
    )
    state: DataflowState = Field(..., description="Dataflow state")
    inherited_attributes: Optional[InheritedAttributes] = Field(
        None,
        alias="inheritedAttributes",
        description="Inherited connection attributes",
    )
    created_at: int = Field(
        ...,
        alias="createdAt",
        description="Creation timestamp (Unix milliseconds)",
    )
    updated_at: int = Field(
        ...,
        alias="updatedAt",
        description="Last update timestamp (Unix milliseconds)",
    )
    created_by: Optional[str] = Field(
        None,
        alias="createdBy",
        description="User who created dataflow",
    )
    etag: str = Field(..., description="Entity tag for concurrency control")

    model_config = {"populate_by_name": True}


# ==================== Run Models ====================


class RunError(BaseModel):
    """Error details for failed run."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details",
    )

    model_config = {"populate_by_name": True}


class RunStatusDetail(BaseModel):
    """Run status with error details."""

    value: RunStatus = Field(..., description="Run status")
    errors: List[RunError] = Field(
        default_factory=list,
        description="Error details if failed",
    )

    model_config = {"populate_by_name": True}


class DurationSummary(BaseModel):
    """Duration information for run or activity."""

    started_at_utc: Optional[int] = Field(
        None,
        alias="startedAtUTC",
        description="Start timestamp (Unix milliseconds)",
    )
    completed_at_utc: Optional[int] = Field(
        None,
        alias="completedAtUTC",
        description="Completion timestamp (Unix milliseconds)",
    )

    model_config = {"populate_by_name": True}


class DataflowMetrics(BaseModel):
    """Metrics for dataflow run."""

    records_read: Optional[int] = Field(
        None,
        alias="recordsRead",
        description="Number of records read",
    )
    records_written: Optional[int] = Field(
        None,
        alias="recordsWritten",
        description="Number of records written",
    )
    records_failed: Optional[int] = Field(
        None,
        alias="recordsFailed",
        description="Number of records failed",
    )
    files_read: Optional[int] = Field(
        None,
        alias="filesRead",
        description="Number of files read",
    )
    duration_summary: Optional[DurationSummary] = Field(
        None,
        alias="durationSummary",
        description="Duration information",
    )

    model_config = {"populate_by_name": True}


class StatusSummary(BaseModel):
    """Status summary with optional extensions."""

    status: str = Field(..., description="Status value (success, failed, etc.)")
    extensions: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional status details",
    )

    model_config = {"populate_by_name": True}


class RecordSummary(BaseModel):
    """Record count summary."""

    input_record_count: Optional[int] = Field(
        None,
        alias="inputRecordCount",
        description="Input record count",
    )
    output_record_count: Optional[int] = Field(
        None,
        alias="outputRecordCount",
        description="Output record count",
    )
    failed_record_count: Optional[int] = Field(
        None,
        alias="failedRecordCount",
        description="Failed record count",
    )

    model_config = {"populate_by_name": True}


class RunActivity(BaseModel):
    """Individual activity within a flow run."""

    id: str = Field(..., description="Activity ID")
    name: Optional[str] = Field(None, description="Activity name")
    activity_type: Optional[str] = Field(
        None,
        alias="activityType",
        description="Activity type (e.g., ingestion)",
    )
    updated_at_utc: Optional[int] = Field(
        None,
        alias="updatedAtUTC",
        description="Last update timestamp",
    )
    duration_summary: Optional[DurationSummary] = Field(
        None,
        alias="durationSummary",
        description="Duration information",
    )
    latency_summary: Optional[Dict[str, Any]] = Field(
        None,
        alias="latencySummary",
        description="Latency metrics",
    )
    size_summary: Optional[Dict[str, Any]] = Field(
        None,
        alias="sizeSummary",
        description="Size metrics",
    )
    record_summary: Optional[RecordSummary] = Field(
        None,
        alias="recordSummary",
        description="Record count metrics",
    )
    file_summary: Optional[Dict[str, Any]] = Field(
        None,
        alias="fileSummary",
        description="File metrics",
    )
    status_summary: Optional[StatusSummary] = Field(
        None,
        alias="statusSummary",
        description="Status with details",
    )

    model_config = {"populate_by_name": True}


class RunMetrics(BaseModel):
    """Metrics for a dataflow run."""

    duration_summary: Optional[DurationSummary] = Field(
        None,
        alias="durationSummary",
        description="Duration information",
    )
    record_summary: Optional[RecordSummary] = Field(
        None,
        alias="recordSummary",
        description="Record count metrics",
    )
    status_summary: Optional[StatusSummary] = Field(
        None,
        alias="statusSummary",
        description="Status summary",
    )

    model_config = {"populate_by_name": True}


class DataflowRun(BaseModel):
    """Dataflow run (execution instance).
    
    Represents a single execution of a dataflow, either scheduled
    or manually triggered.
    """

    id: str = Field(..., description="Run ID")
    flow_id: str = Field(
        ...,
        alias="flowId",
        description="Associated dataflow ID",
    )
    flow_spec: Optional[FlowSpec] = Field(
        None,
        alias="flowSpec",
        description="Flow specification",
    )
    provider_ref_id: Optional[str] = Field(
        None,
        alias="providerRefId",
        description="Provider reference ID",
    )
    metrics: Optional[RunMetrics] = Field(
        None,
        description="Run metrics",
    )
    activities: Optional[List[RunActivity]] = Field(
        None,
        description="Run activities",
    )
    record_types: Optional[List[str]] = Field(
        None,
        alias="recordTypes",
        description="Record types processed",
    )
    labels: Optional[List[str]] = Field(
        None,
        description="Labels for categorization",
    )
    created_at: int = Field(
        ...,
        alias="createdAt",
        description="Creation timestamp (Unix milliseconds)",
    )
    updated_at: int = Field(
        ...,
        alias="updatedAt",
        description="Last update timestamp (Unix milliseconds)",
    )
    created_by: Optional[str] = Field(
        None,
        alias="createdBy",
        description="User who created run",
    )
    updated_by: Optional[str] = Field(
        None,
        alias="updatedBy",
        description="User who last updated run",
    )
    created_client: Optional[str] = Field(
        None,
        alias="createdClient",
        description="Client that created run",
    )
    updated_client: Optional[str] = Field(
        None,
        alias="updatedClient",
        description="Client that last updated run",
    )
    sandbox_id: Optional[str] = Field(
        None,
        alias="sandboxId",
        description="Sandbox ID",
    )
    sandbox_name: Optional[str] = Field(
        None,
        alias="sandboxName",
        description="Sandbox name",
    )
    ims_org_id: Optional[str] = Field(
        None,
        alias="imsOrgId",
        description="IMS Organization ID",
    )
    etag: Optional[str] = Field(None, description="Entity tag")

    model_config = {"populate_by_name": True}
    
    @property
    def status(self) -> Optional[str]:
        """Get run status from metrics."""
        if self.metrics and self.metrics.status_summary:
            return self.metrics.status_summary.status
        return None


# ==================== Connection Models ====================


class ConnectionAuth(BaseModel):
    """Connection authentication details."""

    spec_name: Optional[str] = Field(
        None,
        alias="specName",
        description="Auth spec name",
    )
    params: Optional[Dict[str, Any]] = Field(
        None,
        description="Auth parameters (credentials masked)",
    )

    model_config = {"populate_by_name": True}


class Connection(BaseModel):
    """Base connection object."""

    id: str = Field(..., description="Connection ID")
    name: Optional[str] = Field(None, description="Connection name")
    auth: Optional[ConnectionAuth] = Field(
        None,
        description="Authentication details",
    )
    connection_spec: ConnectionSpec = Field(
        ...,
        alias="connectionSpec",
        description="Connection specification",
    )
    state: Optional[str] = Field(None, description="Connection state")
    created_at: Optional[int] = Field(
        None,
        alias="createdAt",
        description="Creation timestamp (Unix milliseconds)",
    )
    updated_at: Optional[int] = Field(
        None,
        alias="updatedAt",
        description="Last update timestamp (Unix milliseconds)",
    )
    etag: Optional[str] = Field(None, description="Entity tag")

    model_config = {"populate_by_name": True}


class SourceConnection(BaseModel):
    """Source connection object."""

    id: str = Field(..., description="Source connection ID")
    name: Optional[str] = Field(None, description="Connection name")
    base_connection_id: Optional[str] = Field(
        None,
        alias="baseConnectionId",
        description="Base connection ID",
    )
    connection_spec: ConnectionSpec = Field(
        ...,
        alias="connectionSpec",
        description="Connection specification",
    )
    params: Optional[Dict[str, Any]] = Field(
        None,
        description="Source-specific parameters",
    )
    created_at: Optional[int] = Field(
        None,
        alias="createdAt",
        description="Creation timestamp (Unix milliseconds)",
    )
    updated_at: Optional[int] = Field(
        None,
        alias="updatedAt",
        description="Last update timestamp (Unix milliseconds)",
    )
    etag: Optional[str] = Field(None, description="Entity tag")

    model_config = {"populate_by_name": True}
    
    def get_entity_name(self) -> Optional[str]:
        """Extract readable entity name from connection parameters.
        
        Returns:
            Formatted entity string (e.g., "s3://bucket/path") or None
        """
        from adobe_experience.flow.source_parser import extract_source_entity
        return extract_source_entity(self)
    
    def get_source_summary(self) -> str:
        """Get concise summary of source connection for display.
        
        Returns:
            Summary string like "Amazon S3: s3://bucket/path"
        """
        from adobe_experience.flow.source_parser import extract_source_summary
        return extract_source_summary(self)


class TargetConnection(BaseModel):
    """Target connection object."""

    id: str = Field(..., description="Target connection ID")
    name: Optional[str] = Field(None, description="Connection name")
    base_connection_id: Optional[str] = Field(
        None,
        alias="baseConnectionId",
        description="Base connection ID",
    )
    connection_spec: ConnectionSpec = Field(
        ...,
        alias="connectionSpec",
        description="Connection specification",
    )
    params: Optional[Dict[str, Any]] = Field(
        None,
        description="Target-specific parameters (e.g., dataSetId)",
    )
    created_at: Optional[int] = Field(
        None,
        alias="createdAt",
        description="Creation timestamp (Unix milliseconds)",
    )
    updated_at: Optional[int] = Field(
        None,
        alias="updatedAt",
        description="Last update timestamp (Unix milliseconds)",
    )
    etag: Optional[str] = Field(None, description="Entity tag")

    model_config = {"populate_by_name": True}
