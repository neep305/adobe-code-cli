"""Adobe Experience Platform Flow Service module.

This module provides interfaces to the Flow Service API for managing
dataflows (data ingestion pipelines) in Adobe Experience Platform.
"""

from adobe_experience.flow.client import FlowServiceClient
from adobe_experience.flow.models import (
    Connection,
    ConnectionSpec,
    Dataflow,
    DataflowMetrics,
    DataflowRun,
    DataflowSchedule,
    DataflowState,
    FlowSpec,
    RunActivity,
    RunStatus,
    SourceConnection,
    TargetConnection,
)

__all__ = [
    "FlowServiceClient",
    "Dataflow",
    "DataflowRun",
    "DataflowState",
    "RunStatus",
    "DataflowSchedule",
    "DataflowMetrics",
    "RunActivity",
    "SourceConnection",
    "TargetConnection",
    "Connection",
    "ConnectionSpec",
    "FlowSpec",
]
