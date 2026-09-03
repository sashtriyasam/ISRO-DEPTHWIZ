"""Renderer-independent terrain mesh contracts (no display dependencies).

``TerrainMesh`` is a scientific surface representation: owned float64
vertices with Y as the vertical/elevation axis, int64 triangle
indices, deterministic normals and UVs, compact valid-vertex storage
with a source-pixel mapping, and preserved units/semantics/spatial
metadata. Nothing here knows about renderers, cameras or interaction.
"""

from __future__ import annotations

import math
from enum import Enum

import numpy as np
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


class CoordinateFrame(str, Enum):
    """Planar coordinate frame of mesh vertices.

    GEOREFERENCED_LOCAL: horizontal positions derive from the source
    raster transform at pixel centers, expressed relative to an
    explicitly stored local origin (world = origin + vertex). The
    source CRS is preserved unchanged in ``spatial``.
    LOCAL: deterministic pixel/grid-local coordinates (x = column,
    z = row). Used for non-georeferenced sources and as an explicit
    fallback when a CRS exists but no transform can place pixels.
    Horizontal metric distance is never claimed in this frame.
    """

    GEOREFERENCED_LOCAL = "georeferenced_local"
    LOCAL = "local"


class TerrainMesh(BaseModel):
    """Deterministic triangulated terrain surface (representation only).

    Vertices use Y as the vertical axis carrying exact scientific
    elevation values (never exaggerated, normalized or shifted).
    Triangles reference compacted valid vertices only; holes are never
    bridged. Arrays are owned: factories hand out fresh allocations.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    vertices: np.ndarray = Field(description="(N,3) float64 [x, elevation, z].")
    indices: np.ndarray = Field(description="(3*T,) int64 triangle vertex ids.")
    normals: np.ndarray = Field(description="(N,3) float64 unit (or fallback) normals.")
    uvs: np.ndarray = Field(description="(N,2) float64 normalized display coords.")
    vertex_source_indices: np.ndarray = Field(
        description="(N,) int64 flat row-major DSM pixel index per vertex."
    )
    vertex_count: int = Field(
        gt=0, description="Compacted valid vertices (empty meshes unsupported)."
    )
    triangle_count: int = Field(
        gt=0, description="Triangles (a terrain mesh without any is not a surface)."
    )
    valid_source_pixels: int = Field(ge=0)
    invalid_source_pixels: int = Field(ge=0)
    skipped_cells: int = Field(
        ge=0, description="Raster quads omitted for lack of 4 valid corners."
    )
    coverage: float = Field(
        ge=0.0,
        le=1.0,
        description="Triangles over 2*(H-1)*(W-1) possible; topology share only.",
    )
    frame: CoordinateFrame
    origin_x: float | None = Field(
        default=None, description="Local origin X (set iff georeferenced-local)."
    )
    origin_y: float | None = Field(
        default=None, description="Local origin Y (set iff georeferenced-local)."
    )
    width: int = Field(gt=0, description="Source raster width.")
    height: int = Field(gt=0, description="Source raster height.")
    units: str = Field(
        description="Vertical units ('meters'); horizontal units are CRS-dependent "
        "and never claimed here."
    )
    semantics: ElevationSemantics = Field(description="Preserved product meaning.")
    georeferencing: GeoreferencingLevel = Field(description="Preserved, never upgraded.")
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
    provenance: ProductProvenance = Field(description="Reused product provenance.")

    @model_validator(mode="after")
    def _check_mesh_honesty(self) -> TerrainMesh:
        if self.units != METRIC_UNIT:
            raise ValueError(f"mesh vertical units must be ('{METRIC_UNIT}')")
        if self.semantics not in _METRIC_SEMANTICS:
            raise ValueError("mesh requires a metric product meaning")
        for name, array, shape, kind in (
            ("vertices", self.vertices, (self.vertex_count, 3), "f"),
            ("normals", self.normals, (self.vertex_count, 3), "f"),
            ("uvs", self.uvs, (self.vertex_count, 2), "f"),
        ):
            if not isinstance(array, np.ndarray) or array.ndim != 2:
                raise ValueError(f"{name} must be an explicit 2D array")
            if array.dtype.kind != kind or tuple(array.shape) != shape:
                raise ValueError(f"{name} must be {kind}64 with shape {shape}")
        if (
            not isinstance(self.indices, np.ndarray)
            or self.indices.ndim != 1
            or self.indices.dtype.kind != "i"
        ):
            raise ValueError("indices must be a 1D integer array")
        if len(self.indices) != 3 * self.triangle_count:
            raise ValueError("indices length must equal 3 * triangle_count")
        if self.triangle_count and (
            bool((self.indices < 0).any()) or bool((self.indices >= self.vertex_count).any())
        ):
            raise ValueError("triangle indices must lie in [0, vertex_count)")
        if (
            not isinstance(self.vertex_source_indices, np.ndarray)
            or self.vertex_source_indices.ndim != 1
            or self.vertex_source_indices.dtype.kind != "i"
            or len(self.vertex_source_indices) != self.vertex_count
        ):
            raise ValueError("vertex_source_indices must map every vertex to a pixel")
        if bool(
            (
                (self.vertex_source_indices < 0)
                | (self.vertex_source_indices >= self.width * self.height)
            ).any()
        ):
            raise ValueError("source indices must lie in [0, width*height)")
        if not math.isfinite(self.coverage):
            raise ValueError("coverage must be finite")
        if not bool(np.isfinite(self.vertices).all()):
            raise ValueError("vertices must all be finite")
        if not bool(np.isfinite(self.normals).all()):
            raise ValueError("normals must all be finite")
        if bool(((self.uvs < 0.0) | (self.uvs > 1.0)).any()):
            raise ValueError("UVs must lie in [0, 1]")
        if (self.origin_x is None) != (self.origin_y is None):
            raise ValueError("local origin must be fully set or fully absent")
        if (self.frame is CoordinateFrame.GEOREFERENCED_LOCAL) != (self.origin_x is not None):
            raise ValueError("georeferenced-local frame requires a stored origin")
        if self.georeferencing is GeoreferencingLevel.NON_GEOREFERENCED:
            if self.spatial.kind is SpatialKind.PRESENT:
                raise ValueError("NON_GEOREFERENCED mesh must not carry PRESENT details")
        return self
