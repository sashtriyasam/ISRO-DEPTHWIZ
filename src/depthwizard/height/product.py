"""Scientific height/elevation product contracts (meaning, not storage).

``ScientificHeightProduct`` is an in-memory typed representation of
calibrated metric values with explicit semantics: above-ground-level
height or absolute elevation, in metres, linked to the depth source
and the calibration that produced the mapping. It is a semantic
numeric product — not a raster export, not a mesh, not a DEM.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, model_validator

from depthwizard.contracts.artifacts import METRIC_UNIT
from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import ElevationSemantics, GeoreferencingLevel
from depthwizard.contracts.spatial import SpatialContext, SpatialKind

_METRIC_SEMANTICS = frozenset(
    {
        ElevationSemantics.HEIGHT_AGL_NDSM,
        ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
    }
)


class ScientificHeightProduct(BaseModel):
    """Calibrated metric height/elevation values with explicit meaning.

    Values are row-major over ``width`` x ``height`` (the source depth
    grid is never reshaped or resampled). There is deliberately no
    vertical-datum field: the contract does not define one, so absolute
    elevation carries no datum claim.
    """

    model_config = ConfigDict(frozen=True)

    values: tuple[float, ...] = Field(description="Metric values, row-major.")
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    units: str = Field(description="Always explicit metric units ('meters').")
    semantics: ElevationSemantics = Field(
        description="HEIGHT_AGL_NDSM or ABSOLUTE_ELEVATION_DSM only."
    )
    georeferencing: GeoreferencingLevel = Field(
        description="Preserved source georeferencing level (never upgraded)."
    )
    spatial: SpatialContext = Field(description="Preserved source spatial context.")
    depth_model_name: str = Field(min_length=1)
    depth_model_version: str | None = None
    depth_checkpoint_id: str | None = None
    source_input_id: str | None = None
    source_checksum: str | None = None
    calibration_method: str = Field(min_length=1)
    calibration_reference: str = Field(min_length=1)
    calibration_scale: float
    calibration_offset: float
    calibration_valid_samples: int = Field(ge=0)
    provenance: ProductProvenance = Field(
        description="Product provenance derived from the calibration record "
        "plus depth-backend identity (authoritative source: calibration)."
    )

    @model_validator(mode="after")
    def _check_product_honesty(self) -> ScientificHeightProduct:
        if self.units != METRIC_UNIT:
            raise ValueError(
                f"scientific height product must use explicit metric units "
                f"('{METRIC_UNIT}'); got '{self.units}'"
            )
        if self.semantics not in _METRIC_SEMANTICS:
            raise ValueError(
                f"scientific height product requires a metric meaning "
                f"({sorted(m.value for m in _METRIC_SEMANTICS)}); "
                f"got '{self.semantics.value}'"
            )
        if len(self.values) != self.width * self.height:
            raise ValueError(
                f"value count ({len(self.values)}) != dimensions ({self.width}x{self.height})"
            )
        if any(not math.isfinite(v) for v in self.values):
            raise ValueError("scientific height product values must all be finite")
        if self.georeferencing is GeoreferencingLevel.NON_GEOREFERENCED:
            if self.spatial.kind is SpatialKind.PRESENT:
                raise ValueError(
                    "NON_GEOREFERENCED product must not carry PRESENT spatial details; "
                    "calibration changes numeric semantics, not spatial referencing"
                )
        return self
