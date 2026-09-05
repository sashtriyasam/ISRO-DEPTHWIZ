"""Relative surface contracts: grid and mesh with no metric claims.

``RelativeSurfaceGrid`` is the raster form of a RELATIVE ``DepthResult``
(rDSM); ``RelativeTerrainMesh`` is its triangulated surface in a
pixel-local frame. Units are absent by construction (``None``), the
frame is always ``LOCAL`` (relative geometry carries no world frame),
and spatial context passes through untouched — never upgraded, never
used for placement.
"""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import ElevationSemantics, GeoreferencingLevel
from depthwizard.contracts.spatial import SpatialContext, SpatialKind
from depthwizard.mesh.models import CoordinateFrame

_RELATIVE_MEANINGS = frozenset(
    {
        ElevationSemantics.RELATIVE_DEPTH,
        ElevationSemantics.RELATIVE_SURFACE_RDSM,
    }
)


class RelativeSurfaceGrid(BaseModel):
    """Owned 2D raster of relative surface values (rDSM, not elevation)."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    array: np.ndarray = Field(description="2D float array, shape (height, width).")
    valid_mask: np.ndarray = Field(description="2D bool array, True marks usable relative samples.")
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    dtype: str = Field(description="Storage dtype name ('float32'/'float64').")
    units: None = Field(default=None, description="Always absent: relative values carry no units.")
    semantics: ElevationSemantics = Field(description="RELATIVE_DEPTH or RELATIVE_SURFACE_RDSM.")
    invalid_count: int = Field(ge=0, description="Samples masked as unusable.")
    georeferencing: GeoreferencingLevel = Field(description="Preserved, never upgraded.")
    spatial: SpatialContext = Field(description="Preserved source spatial context.")
    depth_model_name: str = Field(min_length=1)
    depth_model_version: str | None = None
    depth_checkpoint_id: str | None = None
    source_input_id: str | None = None
    source_checksum: str | None = None
    provenance: ProductProvenance = Field(description="Depth-backend provenance.")

    @model_validator(mode="after")
    def _check_grid_honesty(self) -> RelativeSurfaceGrid:
        if self.units is not None:
            raise ValueError("relative surface grid must not declare units")
        if self.semantics not in _RELATIVE_MEANINGS:
            raise ValueError(
                f"relative surface grid requires a relative meaning; got '{self.semantics.value}'"
            )
        if not isinstance(self.array, np.ndarray) or self.array.ndim != 2:
            raise ValueError("grid array must be an explicit 2D array")
        if self.array.dtype.kind != "f" or str(self.array.dtype) not in (
            "float32",
            "float64",
        ):
            raise ValueError("grid array must be float32/float64")
        if self.array.shape != (self.height, self.width):
            raise ValueError(
                f"array shape {self.array.shape} != (height, width) ({self.height}, {self.width})"
            )
        if self.dtype != str(self.array.dtype):
            raise ValueError("dtype label must match the array dtype")
        if (
            not isinstance(self.valid_mask, np.ndarray)
            or self.valid_mask.dtype.kind != "b"
            or self.valid_mask.shape != self.array.shape
        ):
            raise ValueError("valid_mask must be a bool array matching the grid shape")
        if self.invalid_count != int((~self.valid_mask).sum()):
            raise ValueError("invalid_count must equal the masked sample count")
        valid_cells = self.array[self.valid_mask]
        if valid_cells.size and not bool(np.isfinite(valid_cells).all()):
            raise ValueError("valid samples must all be finite")
        if self.georeferencing is GeoreferencingLevel.NON_GEOREFERENCED:
            if self.spatial.kind is SpatialKind.PRESENT:
                raise ValueError("NON_GEOREFERENCED grid must not carry PRESENT details")
        return self


class RelativeTerrainMesh(BaseModel):
    """Triangulated relative surface in a pixel-local frame (display geometry).

    Vertices use Y for the relative value axis; Y carries NO metric
    meaning. Horizontal positions are pixel/grid-local (x = column,
    z = row) regardless of source georeferencing: relative geometry
    never places pixels in the world.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    vertices: np.ndarray = Field(description="(N,3) float64 [x, relative, z].")
    indices: np.ndarray = Field(description="(3*T,) int64 triangle vertex ids.")
    normals: np.ndarray = Field(description="(N,3) float64 unit (or fallback) normals.")
    uvs: np.ndarray = Field(description="(N,2) float64 normalized display coords.")
    vertex_source_indices: np.ndarray = Field(
        description="(N,) int64 flat row-major grid pixel index per vertex."
    )
    vertex_count: int = Field(gt=0)
    triangle_count: int = Field(gt=0)
    valid_source_pixels: int = Field(ge=0)
    invalid_source_pixels: int = Field(ge=0)
    skipped_cells: int = Field(
        ge=0, description="Raster quads omitted for lack of 4 valid corners."
    )
    coverage: float = Field(ge=0.0, le=1.0)
    frame: CoordinateFrame = Field(description="Always LOCAL for relative geometry.")
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    units: None = Field(default=None, description="Always absent: no metric claim.")
    semantics: ElevationSemantics = Field(description="Relative meaning only.")
    georeferencing: GeoreferencingLevel = Field(description="Preserved, never upgraded.")
    spatial: SpatialContext = Field(description="Preserved source spatial context.")
    depth_model_name: str = Field(min_length=1)
    depth_model_version: str | None = None
    depth_checkpoint_id: str | None = None
    source_input_id: str | None = None
    source_checksum: str | None = None
    provenance: ProductProvenance = Field(description="Depth-backend provenance.")

    @model_validator(mode="after")
    def _check_mesh_honesty(self) -> RelativeTerrainMesh:
        if self.units is not None:
            raise ValueError("relative mesh must not declare units")
        if self.semantics not in _RELATIVE_MEANINGS:
            raise ValueError(
                f"relative mesh requires a relative meaning; got '{self.semantics.value}'"
            )
        if self.frame is not CoordinateFrame.LOCAL:
            raise ValueError(
                "relative geometry carries no world frame; "
                f"got '{self.frame.value}' (must be 'local')"
            )
        if not isinstance(self.vertices, np.ndarray) or self.vertices.shape != (
            self.vertex_count,
            3,
        ):
            raise ValueError("vertices must be an (N,3) array matching vertex_count")
        if not bool(np.isfinite(self.vertices).all()):
            raise ValueError("relative mesh vertices must all be finite")
        if self.georeferencing is GeoreferencingLevel.NON_GEOREFERENCED:
            if self.spatial.kind is SpatialKind.PRESENT:
                raise ValueError("NON_GEOREFERENCED mesh must not carry PRESENT details")
        return self
