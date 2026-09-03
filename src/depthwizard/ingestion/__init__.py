"""Safe deterministic input ingestion (inspection only, no transforms)."""

from depthwizard.ingestion.api import inspect_input
from depthwizard.ingestion.formats import DetectedFormat
from depthwizard.ingestion.models import (
    InputHandle,
    InputInspection,
    InspectionStatus,
)

__all__ = [
    "DetectedFormat",
    "InputHandle",
    "InputInspection",
    "InspectionStatus",
    "inspect_input",
]
