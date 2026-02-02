"""Pydantic models for Adobe Experience Platform Catalog Service."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== Dataset Models ====================


class DatasetSchemaRef(BaseModel):
    """Reference to XDM schema for a dataset."""

    id: str = Field(..., description="Schema $id URI")
    content_type: str = Field(
        ...,
        alias="contentType",
        description="Schema content type (e.g., application/vnd.adobe.xed+json;version=1)",
    )

    model_config = {"populate_by_name": True}


class DatasetTags(BaseModel):
    """Dataset tags for Profile and Identity configuration."""

    unified_profile: Optional[List[str]] = Field(
        None, alias="unifiedProfile", description="Profile enablement tags"
    )
    unified_identity: Optional[List[str]] = Field(
        None, alias="unifiedIdentity", description="Identity enablement tags"
    )

    model_config = {"populate_by_name": True}


class Dataset(BaseModel):
    """Adobe Experience Platform Dataset object."""

    id: Optional[str] = Field(None, alias="@id", description="Dataset ID (auto-generated)")
    name: str = Field(..., description="Dataset name")
    schema_ref: DatasetSchemaRef = Field(..., alias="schemaRef", description="Associated XDM schema")
    description: Optional[str] = Field(None, description="Dataset description")
    tags: Optional[DatasetTags] = Field(None, description="Dataset tags for configuration")
    created: Optional[int] = Field(None, description="Creation timestamp (Unix milliseconds)")
    updated: Optional[int] = Field(None, description="Last update timestamp (Unix milliseconds)")
    created_user: Optional[str] = Field(None, alias="createdUser", description="User who created dataset")
    ims_org: Optional[str] = Field(None, alias="imsOrg", description="IMS Organization ID")
    state: Optional[str] = Field(None, description="Dataset state (DRAFT or ENABLED)")
    version: Optional[str] = Field(None, description="Dataset version")
    namespace: Optional[str] = Field(None, description="Namespace")

    model_config = {"populate_by_name": True}


# ==================== Batch Models ====================


class BatchStatus(str, Enum):
    """Batch ingestion status values."""

    LOADING = "loading"
    STAGED = "staged"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    ABORTED = "aborted"
    RETRYING = "retrying"


class BatchInputFormat(BaseModel):
    """Batch input format specification."""

    format: str = Field(
        default="parquet",
        description="Input file format: parquet, json, csv, or avro",
    )
    delimiter: Optional[str] = Field(None, description="CSV delimiter (if format=csv)")
    quote: Optional[str] = Field(None, description="CSV quote character (if format=csv)")
    escape: Optional[str] = Field(None, description="CSV escape character (if format=csv)")

    model_config = {"populate_by_name": True}


class BatchRelatedObject(BaseModel):
    """Related object reference in batch (typically dataset)."""

    type: str = Field(..., description="Object type (usually 'dataSet')")
    id: str = Field(..., description="Object ID")

    model_config = {"populate_by_name": True}


class BatchMetrics(BaseModel):
    """Batch ingestion metrics and timing."""

    start_time: Optional[int] = Field(None, alias="startTime", description="Batch start time (Unix ms)")
    end_time: Optional[int] = Field(None, alias="endTime", description="Batch end time (Unix ms)")
    records_read: Optional[int] = Field(None, alias="recordsRead", description="Records read from source")
    records_written: Optional[int] = Field(
        None, alias="recordsWritten", description="Records written to dataset"
    )
    records_failed: Optional[int] = Field(None, alias="recordsFailed", description="Failed records")
    failure_reason: Optional[str] = Field(None, alias="failureReason", description="Failure reason")

    model_config = {"populate_by_name": True}


class BatchError(BaseModel):
    """Batch error details."""

    code: str = Field(..., description="Error code")
    description: str = Field(..., description="Error description")
    rows: Optional[List[int]] = Field(None, description="Affected row numbers")

    model_config = {"populate_by_name": True}


class Batch(BaseModel):
    """Adobe Experience Platform Batch object."""

    id: str = Field(..., description="Batch ID")
    ims_org: str = Field(..., alias="imsOrg", description="IMS Organization ID")
    status: BatchStatus = Field(..., description="Current batch status")
    created: int = Field(..., description="Creation timestamp (Unix milliseconds)")
    updated: int = Field(..., description="Last update timestamp (Unix milliseconds)")
    related_objects: List[BatchRelatedObject] = Field(
        default_factory=list,
        alias="relatedObjects",
        description="Related objects (datasets)",
    )
    input_format: Optional[BatchInputFormat] = Field(None, alias="inputFormat", description="Input format spec")
    metrics: Optional[BatchMetrics] = Field(None, description="Ingestion metrics")
    errors: List[BatchError] = Field(default_factory=list, description="Error details")
    version: str = Field(default="1.0.0", description="Batch API version")
    created_user: Optional[str] = Field(None, alias="createdUser", description="User who created batch")
    tags: Optional[Dict[str, Any]] = Field(None, description="Custom batch tags")

    model_config = {"populate_by_name": True}


# ==================== DataSetFile Models ====================


class DataSetFile(BaseModel):
    """Dataset file metadata from Catalog Service."""

    id: str = Field(..., alias="@id", description="File ID")
    dataset_id: str = Field(..., alias="dataSetId", description="Parent dataset ID")
    batch_id: str = Field(..., alias="batchId", description="Batch ID")
    file_name: str = Field(..., alias="name", description="File name")
    size_bytes: int = Field(..., alias="sizeInBytes", description="File size in bytes")
    records: Optional[int] = Field(None, description="Number of records in file")
    created: int = Field(..., description="Creation timestamp (Unix milliseconds)")
    is_valid: Optional[bool] = Field(None, alias="isValid", description="File validation status")

    model_config = {"populate_by_name": True}
