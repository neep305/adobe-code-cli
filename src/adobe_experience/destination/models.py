"""Pydantic models for Adobe Experience Platform Destination Service.

NOTE: This is initial implementation based on Flow Service patterns.
Actual API structure may differ and should be validated against Adobe documentation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DestinationType(str, Enum):
    """Destination platform type."""

    EMAIL = "EMAIL"
    ADS = "ADS"
    CDP = "CDP"  # Customer Data Platform
    ANALYTICS = "ANALYTICS"
    CLOUD_STORAGE = "CLOUD_STORAGE"
    CRM = "CRM"
    DMP = "DMP"  # Data Management Platform
    OTHER = "OTHER"


class ActivationStatus(str, Enum):
    """Segment activation status."""

    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    DRAFT = "DRAFT"
    FAILED = "FAILED"
    PROCESSING = "PROCESSING"


class ConnectionSpec(BaseModel):
    """Connection specification for destination.
    
    Defines the type and capabilities of a destination connection.
    """

    id: str = Field(..., description="Connection spec ID")
    name: Optional[str] = Field(None, description="Connection spec name")
    version: Optional[str] = Field(None, description="Connection spec version")

    model_config = {"populate_by_name": True}


class Destination(BaseModel):
    """Destination catalog entry.
    
    Represents an available destination type in the Adobe Experience Platform catalog.
    Users can configure instances of these destinations to activate segments.
    """

    id: str = Field(..., description="Destination ID")
    name: str = Field(..., description="Destination name")
    description: Optional[str] = Field(None, description="Destination description")
    destination_type: DestinationType = Field(..., description="Type of destination platform")
    connection_spec: Optional[ConnectionSpec] = Field(None, description="Connection specification")
    supported_identities: Optional[List[str]] = Field(
        default_factory=list, description="Supported identity namespaces"
    )
    supported_segments: Optional[bool] = Field(True, description="Supports segment activation")
    documentation_url: Optional[str] = Field(None, description="Documentation URL")

    model_config = {"populate_by_name": True}


class DestinationInstance(BaseModel):
    """Configured destination instance.
    
    An instance of a destination that has been configured with credentials
    and settings, ready to receive segment activations.
    """

    id: str = Field(..., description="Destination instance ID")
    name: str = Field(..., description="Instance name")
    destination_id: str = Field(..., description="Reference to destination catalog entry")
    destination_type: Optional[DestinationType] = Field(None, description="Destination type")
    connection_id: Optional[str] = Field(None, description="Flow Service connection ID")
    state: Optional[str] = Field(None, description="Instance state (enabled/disabled)")
    created_at: Optional[int] = Field(None, description="Creation timestamp (ms)")
    updated_at: Optional[int] = Field(None, description="Last update timestamp (ms)")
    created_by: Optional[str] = Field(None, description="Creator user ID")

    model_config = {"populate_by_name": True}


class SegmentActivation(BaseModel):
    """Segment activation to a destination.
    
    Represents the activation of a segment to a specific destination instance.
    This creates a dataflow that exports segment membership to the destination.
    """

    id: str = Field(..., description="Activation ID (typically dataflow ID)")
    segment_id: str = Field(..., description="Segment definition ID")
    segment_name: Optional[str] = Field(None, description="Segment name")
    destination_id: str = Field(..., description="Destination instance ID")
    destination_name: Optional[str] = Field(None, description="Destination name")
    status: ActivationStatus = Field(..., description="Activation status")
    dataflow_id: Optional[str] = Field(None, description="Associated dataflow ID")
    schedule: Optional[Dict[str, Any]] = Field(None, description="Activation schedule")
    mapping_config: Optional[Dict[str, Any]] = Field(
        None, description="Field mapping configuration"
    )
    created_at: Optional[int] = Field(None, description="Activation created timestamp (ms)")
    updated_at: Optional[int] = Field(None, description="Last update timestamp (ms)")
    last_run_at: Optional[int] = Field(None, description="Last execution timestamp (ms)")
    next_run_at: Optional[int] = Field(None, description="Next scheduled run timestamp (ms)")

    model_config = {"populate_by_name": True}


class ActivationDataflow(BaseModel):
    """Dataflow for segment activation.
    
    Specialized dataflow that exports segment membership from AEP to external destinations.
    Similar to ingestion dataflows but in reverse direction.
    """

    id: str = Field(..., description="Dataflow ID")
    name: str = Field(..., description="Dataflow name")
    description: Optional[str] = Field(None, description="Dataflow description")
    flow_spec_id: Optional[str] = Field(None, description="Flow specification ID for activation")
    segment_ids: List[str] = Field(default_factory=list, description="Activated segment IDs")
    destination_id: str = Field(..., description="Target destination instance ID")
    state: Optional[str] = Field(None, description="Dataflow state (enabled/disabled)")
    created_at: Optional[int] = Field(None, description="Creation timestamp (ms)")
    updated_at: Optional[int] = Field(None, description="Last update timestamp (ms)")
    etag: Optional[str] = Field(None, description="Entity tag for versioning")

    model_config = {"populate_by_name": True}


class ActivationRun(BaseModel):
    """Execution run of an activation dataflow.
    
    Represents a single execution of segment data export to a destination.
    """

    id: str = Field(..., description="Run ID")
    dataflow_id: str = Field(..., description="Parent dataflow ID")
    status: str = Field(..., description="Run status (success/failed/processing)")
    started_at: Optional[int] = Field(None, description="Run start timestamp (ms)")
    completed_at: Optional[int] = Field(None, description="Run completion timestamp (ms)")
    records_processed: Optional[int] = Field(0, description="Number of profiles exported")
    records_failed: Optional[int] = Field(0, description="Number of failed records")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    model_config = {"populate_by_name": True}
