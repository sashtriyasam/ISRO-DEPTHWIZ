"""Models for city-scale DSM grid mosaic operations."""

from __future__ import annotations

from dataclasses import dataclass

from depthwizard.dsm.grid import DSMGrid


@dataclass(frozen=True)
class MosaicTileInfo:
    """Provenance for one tile contributing to a mosaic."""

    source_input_id: str | None
    source_checksum: str | None
    width: int
    height: int
    valid_count: int


@dataclass(frozen=True)
class MosaicResult:
    """Outcome of stitching multiple georeferenced DSM grids."""

    mosaic_grid: DSMGrid
    tiles: tuple[MosaicTileInfo, ...]
    tile_count: int
    overlap_pixel_count: int
