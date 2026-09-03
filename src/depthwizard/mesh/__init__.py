"""Renderer-independent terrain mesh engine (representation only).

Triangulates validated ``DSMGrid`` rasters into owned ``TerrainMesh``
surfaces with Y as the vertical axis. No display, camera or
interaction concepts live here.
"""

from depthwizard.mesh.build import build_terrain_mesh
from depthwizard.mesh.models import CoordinateFrame, TerrainMesh

__all__ = [
    "CoordinateFrame",
    "TerrainMesh",
    "build_terrain_mesh",
]
