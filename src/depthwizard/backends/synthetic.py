"""Deterministic synthetic depth backend (development/test fixture only).

``SyntheticDepthBackend`` implements :class:`DepthBackend` with a pure
analytic pattern — a normalized separable sinusoid in ``[0, 1]`` derived
only from the input grid dimensions. It performs no inference, needs no
data/network/GPU/weights, and is bit-for-bit deterministic.

It is NOT scientific inference and must never be treated as a
production model. Real model adapters (Shravan) implement the same
``DepthBackend`` boundary later. Output is always ``RELATIVE`` with no
metre claim; input georeferencing/spatial metadata is preserved as-is
(never upgraded, never invented).
"""

from __future__ import annotations

import math

from depthwizard.contracts.artifacts import DepthResult, ImageResolution
from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import DepthScale, ElevationSemantics
from depthwizard.ingestion.models import InputInspection
from depthwizard.version import __version__

MODEL_NAME = "synthetic-depth"
MODEL_VERSION = "0.1.0"
PATTERN_DESCRIPTION = "separable-sinusoid-normalized"


def synthetic_depth_values(width: int, height: int) -> tuple[float, ...]:
    """Deterministic relative-depth pattern in ``[0, 1]``, row-major.

    v(col, row) = 0.5 * (1 + sin(2*pi*col/width) * cos(2*pi*row/height)).
    Closed-form over the grid indices: no randomness, no I/O, finite
    for every valid (width, height >= 1).
    """
    two_pi = 2.0 * math.pi
    values: list[float] = []
    for row in range(height):
        cos_row = math.cos(two_pi * row / height)
        for col in range(width):
            values.append(0.5 * (1.0 + math.sin(two_pi * col / width) * cos_row))
    return tuple(values)


class SyntheticDepthBackend:
    """Development/test ``DepthBackend``. Stateless and deterministic."""

    @property
    def model_name(self) -> str:
        """Stable backend name, clearly marked synthetic."""
        return MODEL_NAME

    @property
    def model_version(self) -> str | None:
        """Stable backend version."""
        return MODEL_VERSION

    @property
    def checkpoint_id(self) -> str | None:
        """No checkpoint exists for an analytic pattern: always None."""
        return None

    def estimate_depth(self, inspection: InputInspection) -> DepthResult:
        """Generate deterministic relative depth for a validated inspection.

        Raises :class:`TypeError` for non-``InputInspection`` input
        (the backend consumes validated inspections, never raw paths or
        opaque ids). Timestamps are deliberately omitted from provenance
        so repeated runs are bit-for-bit identical.
        """
        if not isinstance(inspection, InputInspection):
            raise TypeError(
                "SyntheticDepthBackend requires an InputInspection from "
                f"inspect_input(); got {type(inspection).__name__}"
            )
        handle = inspection.handle
        resolution = ImageResolution(width=inspection.width, height=inspection.height)
        return DepthResult(
            model_name=self.model_name,
            model_version=self.model_version,
            checkpoint_id=self.checkpoint_id,
            input_resolution=resolution,
            output_resolution=resolution,
            depth_scale=DepthScale.RELATIVE,
            elevation_semantics=ElevationSemantics.RELATIVE_DEPTH,
            georeferencing=inspection.georeferencing,
            depth_values=synthetic_depth_values(inspection.width, inspection.height),
            preprocessing={"synthetic_pattern": PATTERN_DESCRIPTION},
            units=None,
            spatial=inspection.spatial,
            provenance=ProductProvenance(
                source_input_id=handle.display_name,
                input_checksum=handle.sha256,
                model_name=self.model_name,
                model_version=self.model_version,
                checkpoint_id=None,
                software_version=__version__,
                generated_at=None,
                units=None,
                semantic_meaning=(
                    "relative_depth from synthetic development backend (not scientific inference)"
                ),
            ),
        )
