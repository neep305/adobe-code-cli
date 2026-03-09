"""Pydantic models for Adobe Experience Platform Segmentation Service."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SegmentStatus(str, Enum):
    """Segment definition status."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DELETED = "DELETED"


class SegmentJobStatus(str, Enum):
    """Segment evaluation job status."""

    NEW = "NEW"
    PROCESSING = "PROCESSING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PQLExpression(BaseModel):
    """Profile Query Language (PQL) expression for segment definition.
    
    PQL is used to define segment criteria that operate on Real-Time Customer Profile data.
    
    Example:
        person.totalSpent > 1000 AND person.lastPurchase > now() - duration("P30D")
    """

    type: str = Field(default="PQL", description="Expression type")
    format: str = Field(default="pql/text", description="PQL format")
    value: str = Field(..., description="PQL query string")

    model_config = {"populate_by_name": True}


class SegmentDefinition(BaseModel):
    """Adobe AEP Segment Definition.
    
    A segment definition describes a subset of profiles from Real-Time Customer Profile
    based on PQL criteria. Segments can be evaluated on-demand or on a schedule.
    
    Attributes:
        id: Unique segment identifier (auto-generated)
        name: Human-readable segment name
        description: Optional description
        expression: PQL expression defining segment criteria
        schema: Schema reference (e.g., {"name": "_xdm.context.profile"})
        ttlInDays: Time-to-live for segment membership in days
        status: Current segment status (DRAFT, ACTIVE, INACTIVE, DELETED)
        created: Creation timestamp (Unix milliseconds)
        updated: Last update timestamp (Unix milliseconds)
        createdBy: User who created the segment
        eligibilityRule: Defines when profiles enter/exit segment
    """

    id: Optional[str] = Field(None, description="Segment ID", alias="id")
    name: str = Field(..., description="Segment name")
    description: Optional[str] = Field(None, description="Segment description")
    expression: PQLExpression = Field(..., description="PQL expression")
    schema: Dict[str, str] = Field(
        default_factory=lambda: {"name": "_xdm.context.profile"},
        description="Schema reference",
    )
    ttlInDays: Optional[int] = Field(
        None, description="Time to live in days", alias="ttlInDays"
    )
    status: SegmentStatus = Field(
        default=SegmentStatus.DRAFT, description="Segment status"
    )
    created: Optional[int] = Field(None, description="Creation timestamp")
    updated: Optional[int] = Field(None, description="Last update timestamp")
    createdBy: Optional[str] = Field(None, description="Creator user ID", alias="createdBy")
    
    # Evaluation configuration
    evaluationInfo: Optional[Dict[str, Any]] = Field(
        None, description="Evaluation configuration", alias="evaluationInfo"
    )
    
    model_config = {"populate_by_name": True}

    @property
    def created_at(self) -> Optional[datetime]:
        """Get creation datetime."""
        if self.created:
            return datetime.fromtimestamp(self.created / 1000)
        return None

    @property
    def updated_at(self) -> Optional[datetime]:
        """Get update datetime."""
        if self.updated:
            return datetime.fromtimestamp(self.updated / 1000)
        return None


class SegmentJobMetrics(BaseModel):
    """Metrics for a segment evaluation job."""

    totalTime: Optional[int] = Field(None, description="Total time in milliseconds", alias="totalTime")
    profileSegmentationTime: Optional[int] = Field(
        None, description="Profile segmentation time", alias="profileSegmentationTime"
    )
    segmentedProfileCounter: Optional[Dict[str, int]] = Field(
        None, description="Segmented profile counts", alias="segmentedProfileCounter"
    )
    
    model_config = {"populate_by_name": True}


class SegmentJob(BaseModel):
    """Segment evaluation job.
    
    Represents an execution of segment evaluation, either scheduled or on-demand.
    The job processes all eligible profiles and determines segment membership.
    
    Attributes:
        id: Job ID
        status: Current job status (NEW, PROCESSING, SUCCEEDED, FAILED)
        segments: List of segment IDs being evaluated
        computeJobId: Associated compute job ID
        snapshot: Snapshot information
        metrics: Job execution metrics
        errors: List of errors if job failed
        requestId: Original request ID
        created: Creation timestamp
        updated: Last update timestamp
    """

    id: str = Field(..., description="Job ID")
    status: SegmentJobStatus = Field(..., description="Job status")
    segments: List[str] = Field(default_factory=list, description="Segment IDs")
    computeJobId: Optional[int] = Field(None, description="Compute job ID", alias="computeJobId")
    snapshot: Optional[Dict[str, Any]] = Field(None, description="Snapshot info")
    metrics: Optional[SegmentJobMetrics] = Field(None, description="Job metrics")
    errors: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, description="Error details"
    )
    requestId: Optional[str] = Field(None, description="Request ID", alias="requestId")
    created: Optional[int] = Field(None, description="Creation timestamp")
    updated: Optional[int] = Field(None, description="Update timestamp")
    
    model_config = {"populate_by_name": True}

    @property
    def created_at(self) -> Optional[datetime]:
        """Get creation datetime."""
        if self.created:
            return datetime.fromtimestamp(self.created / 1000)
        return None

    @property
    def updated_at(self) -> Optional[datetime]:
        """Get update datetime."""
        if self.updated:
            return datetime.fromtimestamp(self.updated / 1000)
        return None


class SegmentEstimate(BaseModel):
    """Segment size estimate.
    
    Provides an estimate of how many profiles match the segment criteria
    without performing full evaluation.
    """

    estimatedSize: int = Field(..., description="Estimated profile count", alias="estimatedSize")
    confidenceInterval: Optional[str] = Field(
        None, description="Confidence interval", alias="confidenceInterval"
    )
    
    model_config = {"populate_by_name": True}


class SegmentExportJob(BaseModel):
    """Segment export job.
    
    Exports segment membership data to a dataset for downstream consumption.
    """

    id: str = Field(..., description="Export job ID")
    status: str = Field(..., description="Job status")
    segments: List[str] = Field(default_factory=list, description="Segment IDs")
    destination: Optional[Dict[str, Any]] = Field(None, description="Destination config")
    schema: Optional[Dict[str, str]] = Field(None, description="Output schema")
    created: Optional[int] = Field(None, description="Creation timestamp")
    updated: Optional[int] = Field(None, description="Update timestamp")
    
    model_config = {"populate_by_name": True}

    @property
    def created_at(self) -> Optional[datetime]:
        """Get creation datetime."""
        if self.created:
            return datetime.fromtimestamp(self.created / 1000)
        return None

    @property
    def updated_at(self) -> Optional[datetime]:
        """Get update datetime."""
        if self.updated:
            return datetime.fromtimestamp(self.updated / 1000)
        return None
