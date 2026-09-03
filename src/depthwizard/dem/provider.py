"""Future-compatible terrain-reference provider boundary.

A later acquisition subsystem (local DEM directories, SRTM tiles,
Copernicus archives) implements this interface to serve
``TerrainReferenceGrid`` objects for explicit target grids. This task
ships no implementation: reference-control logic that later combines
model predictions with terrain samples must not assume terrain equals
surface, and no fake provider is constructed to pretend otherwise.
"""

from __future__ import annotations

from typing import Protocol

from depthwizard.dem.models import TerrainReferenceGrid
from depthwizard.geospatial.grids import TargetGrid


class TerrainReferenceProvider(Protocol):
    """Source of aligned terrain references for explicit target grids."""

    def terrain_reference(self, target: TargetGrid) -> TerrainReferenceGrid:
        """Provide the terrain reference aligned to the target grid."""
        ...
