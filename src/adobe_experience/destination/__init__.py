"""Adobe Experience Platform Destination Service."""

from adobe_experience.destination.client import DestinationServiceClient
from adobe_experience.destination.models import (
    Destination,
    DestinationInstance,
    DestinationType,
    ActivationStatus,
    SegmentActivation,
)

__all__ = [
    "Destination",
    "DestinationInstance",
    "DestinationType",
    "ActivationStatus",
    "SegmentActivation",
    "DestinationServiceClient",
]
