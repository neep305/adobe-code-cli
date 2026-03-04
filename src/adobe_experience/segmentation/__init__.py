"""Adobe Experience Platform Segmentation Service module."""

from adobe_experience.segmentation.client import SegmentationServiceClient
from adobe_experience.segmentation.models import (
    SegmentDefinition,
    SegmentJob,
    SegmentStatus,
    PQLExpression,
    SegmentEstimate,
    SegmentExportJob,
)

__all__ = [
    "SegmentationServiceClient",
    "SegmentDefinition",
    "SegmentJob",
    "SegmentStatus",
    "PQLExpression",
    "SegmentEstimate",
    "SegmentExportJob",
]
