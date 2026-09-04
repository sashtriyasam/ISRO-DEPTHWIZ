"""Local DEM terrain-reference subsystem (ground, never surface).

Inspects local GeoTIFF DEMs, aligns them to explicit target grids via
S7 primitives, and serves deterministic nearest-neighbour terrain
samples. Offline only. A DEM provides terrain elevation — never
surface elevation, AGL height, or DSM ground truth — and this package
constructs no calibration objects from it.
"""

from depthwizard.dem.build import build_terrain_reference
from depthwizard.dem.inspect import inspect_dem
from depthwizard.dem.models import DEMInspection, TerrainReferenceGrid, TerrainSample
from depthwizard.dem.provider import TerrainReferenceProvider
from depthwizard.dem.sample import sample_terrain, sample_terrain_at_world
from depthwizard.dem.target import target_grid_from_inspection

__all__ = [
    "DEMInspection",
    "TerrainReferenceGrid",
    "TerrainReferenceProvider",
    "TerrainSample",
    "build_terrain_reference",
    "inspect_dem",
    "sample_terrain",
    "sample_terrain_at_world",
    "target_grid_from_inspection",
]
