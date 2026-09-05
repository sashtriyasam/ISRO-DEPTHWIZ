"""Relative surface (rDSM) products: visualization geometry, never metres.

For non-georeferenced input the SIH pipeline ends at a relative
surface: ``DepthResult`` → ``RelativeSurfaceGrid`` → relative mesh in
a pixel-local frame. No calibration, no CRS invention, no metric
claims. Metric products remain the exclusive output of the calibrated
``height``/``dsm``/``mesh`` path.
"""

from depthwizard.rdsm.mesh import RelativeTerrainMesh as RelativeTerrainMesh
from depthwizard.rdsm.mesh import build_relative_mesh as build_relative_mesh
from depthwizard.rdsm.models import RelativeSurfaceGrid as RelativeSurfaceGrid
from depthwizard.rdsm.pipeline import RelativeSurfaceResult as RelativeSurfaceResult
from depthwizard.rdsm.pipeline import run_relative_path as run_relative_path
from depthwizard.rdsm.rasterize import rasterize_relative_surface as rasterize_relative_surface

__all__ = [
    "RelativeSurfaceGrid",
    "RelativeSurfaceResult",
    "RelativeTerrainMesh",
    "build_relative_mesh",
    "rasterize_relative_surface",
    "run_relative_path",
]
