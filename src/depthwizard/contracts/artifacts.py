"""Backend artifact contract: ``DepthBackend -> DepthResult``.

Model-agnostic by design. Nothing here names Depth Anything, Sat3DGen,
or any other specific model. Both scale-ambiguous (relative) and
calibrated (metric) outputs are representable, but metric units can
never be claimed without the matching scale semantics: a validator
rejects ``METRIC`` results that do not declare metre units, and
rejects ``RELATIVE`` results that falsely claim metres.

Georeferencing consistency is enforced the same way: a
``NON_GEOREFERENCED`` input (plain PNG/JPG) cannot carry ``PRESENT``
spatial details (no fake CRS), and ``PRESENT`` spatial details require
a georeferenced level.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import (
    DepthScale,
    ElevationSemantics,
    GeoreferencingLevel,
)
from depthwizard.contracts.spatial import SpatialContext, SpatialKind

if TYPE_CHECKING:
    from depthwizard.ingestion.models import InputInspection

METRIC_UNIT = "meters"


class ImageResolution(BaseModel):
    """Pixel dimensions of an input or output raster."""

    model_config = ConfigDict(frozen=True)

    width: int = Field(gt=0)
    height: int = Field(gt=0)

    @property
    def pixel_count(self) -> int:
        """Total number of pixels (width * height)."""
        return self.width * self.height


class DepthResult(BaseModel):
    """Model-agnostic output of a depth backend.

    Depth samples are stored row-major as a flat tuple so the contract
    needs no scientific runtime (no numpy) at this stage.
    """

    model_config = ConfigDict(frozen=True)

    model_name: str = Field(min_length=1)
    model_version: str | None = None
    checkpoint_id: str | None = None

    input_resolution: ImageResolution
    output_resolution: ImageResolution

    depth_scale: DepthScale
    elevation_semantics: ElevationSemantics
    georeferencing: GeoreferencingLevel

    depth_values: tuple[float, ...] = Field(
        description="Row-major depth samples, length == output pixel count."
    )
    confidence_values: tuple[float, ...] | None = Field(
        default=None, description="Per-pixel confidence in [0, 1], if provided."
    )
    valid_mask: tuple[bool, ...] | None = Field(
        default=None, description="Per-pixel validity; False marks invalid samples."
    )

    preprocessing: dict[str, str] = Field(
        default_factory=dict,
        description="Preprocessing steps applied, e.g. {'resize': 'bilinear_512'}.",
    )
    units: str | None = Field(
        default=None,
        description="'meters' for METRIC output, otherwise None or a "
        "non-metre label. Never 'meters' for RELATIVE output.",
    )

    spatial: SpatialContext
    provenance: ProductProvenance = Field(default_factory=ProductProvenance)

    @model_validator(mode="after")
    def _check_consistency(self) -> DepthResult:
        expected = self.output_resolution.pixel_count
        if len(self.depth_values) != expected:
            raise ValueError(
                f"depth_values length {len(self.depth_values)} != output pixel count {expected}"
            )
        if self.confidence_values is not None:
            if len(self.confidence_values) != expected:
                raise ValueError("confidence_values length must match output pixel count")
            if any(c < 0.0 or c > 1.0 for c in self.confidence_values):
                raise ValueError("confidence_values must lie in [0, 1]")
        if self.valid_mask is not None and len(self.valid_mask) != expected:
            raise ValueError("valid_mask length must match output pixel count")

        # Scale/unit honesty: metric claims require metres, relative forbids them.
        if self.depth_scale is DepthScale.METRIC and self.units != METRIC_UNIT:
            raise ValueError("METRIC DepthResult must declare units='meters'")
        if self.depth_scale is DepthScale.RELATIVE and self.units == METRIC_UNIT:
            raise ValueError("RELATIVE DepthResult must not claim units='meters'")

        # A plain image has no CRS: non-georeferenced output cannot carry
        # PRESENT spatial details, and PRESENT details need a georeferenced level.
        if self.georeferencing is GeoreferencingLevel.NON_GEOREFERENCED:
            if self.spatial.kind is SpatialKind.PRESENT:
                raise ValueError(
                    "NON_GEOREFERENCED DepthResult must not carry PRESENT spatial details"
                )
        if self.spatial.kind is SpatialKind.PRESENT and self.georeferencing not in (
            GeoreferencingLevel.GEOREFERENCED_NO_ELEVATION_REFERENCE,
            GeoreferencingLevel.GEOREFERENCED_WITH_DEM,
            GeoreferencingLevel.GEOREFERENCED_WITH_GCP,
        ):
            raise ValueError("PRESENT spatial details require a georeferenced level")
        return self


class DepthBackend(Protocol):
    """Interface future depth models implement. No implementation here."""

    @property
    def model_name(self) -> str:
        """Backend model name, e.g. 'depth-anything-v2' (any model allowed)."""
        ...

    @property
    def model_version(self) -> str | None:
        """Backend model version, if known."""
        ...

    @property
    def checkpoint_id(self) -> str | None:
        """Checkpoint identifier, if known."""
        ...

    def estimate_depth(self, inspection: InputInspection) -> DepthResult:
        """Run inference for an already-validated input inspection.

        Implementations consume the validated ``InputInspection`` value
        object (dimensions, checksum, spatial semantics) instead of an
        opaque string id, so backends stay stateless: no registry, cache
        or lookup is needed to execute. Changed from ``input_id: str``
        in the S5 milestone for exactly this reason — a string id would
        force every backend to resolve inputs through hidden state.
        Real inference (future model adapters) implements this same
        boundary.
        """
        ...
