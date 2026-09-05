"""Mode-A relative path: input → relative geometry → rDSM → mesh.

The non-georeferenced SIH path that never touches calibration: ingest
a real input file, run any ``DepthBackend``, rasterize the relative
surface, and triangulate it in a pixel-local frame. Metric
``PipelineRunner`` remains the only route to metric products.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from depthwizard.contracts.artifacts import DepthBackend, DepthResult
from depthwizard.ingestion import inspect_input
from depthwizard.rdsm.mesh import RelativeTerrainMesh as RelativeTerrainMesh
from depthwizard.rdsm.mesh import build_relative_mesh as build_relative_mesh
from depthwizard.rdsm.models import RelativeSurfaceGrid
from depthwizard.rdsm.rasterize import rasterize_relative_surface


class RelativeSurfaceResult(BaseModel):
    """Complete Mode-A outcome (artifacts owned, provenance linked)."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    input_path: str = Field(min_length=1)
    input_checksum: str | None = None
    depth: DepthResult
    grid: RelativeSurfaceGrid
    mesh: RelativeTerrainMesh


def run_relative_path(input_path: str, backend: DepthBackend) -> RelativeSurfaceResult:
    """Execute the relative surface path for one real input file."""
    inspection = inspect_input(input_path)
    depth = backend.estimate_depth(inspection)
    grid = rasterize_relative_surface(depth)
    mesh = build_relative_mesh(grid)
    return RelativeSurfaceResult(
        input_path=input_path,
        input_checksum=inspection.handle.sha256,
        depth=depth,
        grid=grid,
        mesh=mesh,
    )
