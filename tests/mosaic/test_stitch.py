"""Tests for city-scale multi-tile DSM mosaic stitching."""

from __future__ import annotations

import numpy as np
import pytest

from depthwizard.contracts.artifacts import METRIC_UNIT
from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import ElevationSemantics, GeoreferencingLevel
from depthwizard.contracts.spatial import (
    AffineTransform,
    Bounds,
    SpatialContext,
    SpatialDetails,
    SpatialKind,
)
from depthwizard.dsm.grid import NODATA, DSMGrid, ResamplingPolicy
from depthwizard.errors import GeospatialProcessingError, MissingCRSError
from depthwizard.mosaic.models import MosaicResult
from depthwizard.mosaic.stitch import stitch_dsm_grids
from depthwizard.version import __version__


def _make_tile(
    x_offset: float = 0.0,
    y_offset: float = 0.0,
    fill_value: float = 25.0,
    crs: str = "EPSG:32643",
    semantics: ElevationSemantics = ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
    width: int = 10,
    height: int = 10,
    tile_id: str = "tile_1",
) -> DSMGrid:
    arr = np.full((height, width), fill_value, dtype=np.float32)
    mask = np.ones((height, width), dtype=bool)
    t = AffineTransform(a=1.0, b=0.0, c=x_offset, d=0.0, e=-1.0, f=y_offset)
    spatial = SpatialContext(
        kind=SpatialKind.PRESENT,
        details=SpatialDetails(
            crs=crs,
            transform=t,
            bounds=Bounds(
                min_x=x_offset,
                min_y=y_offset - height * 1.0,
                max_x=x_offset + width * 1.0,
                max_y=y_offset,
            ),
        ),
    )
    prov = ProductProvenance(
        source_input_id=tile_id,
        input_checksum="a" * 64,
        model_name="test-model",
        model_version=None,
        checkpoint_id=None,
        software_version=__version__,
        generated_at=None,
        units=METRIC_UNIT,
        semantic_meaning="test",
    )
    return DSMGrid(
        array=arr,
        valid_mask=mask,
        width=width,
        height=height,
        dtype="float32",
        units=METRIC_UNIT,
        semantics=semantics,
        nodata=NODATA,
        invalid_count=0,
        resampling=ResamplingPolicy.NO_RESAMPLING,
        georeferencing=GeoreferencingLevel.GEOREFERENCED_NO_ELEVATION_REFERENCE,
        spatial=spatial,
        depth_model_name="test-model",
        depth_model_version=None,
        depth_checkpoint_id=None,
        source_input_id=tile_id,
        source_checksum="a" * 64,
        calibration_method="test",
        calibration_reference="test",
        calibration_scale=1.0,
        calibration_offset=0.0,
        calibration_valid_samples=width * height,
        provenance=prov,
    )


def test_stitch_two_adjacent_tiles() -> None:
    """Two horizontally adjacent 10x10 tiles form a single 20x10 mosaic."""
    t1 = _make_tile(x_offset=0.0, y_offset=100.0, fill_value=10.0, tile_id="left")
    t2 = _make_tile(x_offset=10.0, y_offset=100.0, fill_value=20.0, tile_id="right")

    res = stitch_dsm_grids([t1, t2])
    assert isinstance(res, MosaicResult)
    assert res.tile_count == 2
    assert res.overlap_pixel_count == 0
    grid = res.mosaic_grid
    assert grid.width == 20
    assert grid.height == 10
    assert grid.array[0, 0] == pytest.approx(10.0)
    assert grid.array[0, 15] == pytest.approx(20.0)
    assert grid.units == METRIC_UNIT


def test_stitch_overlapping_tiles_blends_overlap() -> None:
    """Overlapping pixels are averaged between tiles."""
    t1 = _make_tile(x_offset=0.0, y_offset=100.0, fill_value=10.0)
    t2 = _make_tile(x_offset=5.0, y_offset=100.0, fill_value=30.0)

    res = stitch_dsm_grids([t1, t2])
    assert res.overlap_pixel_count > 0
    grid = res.mosaic_grid
    assert grid.width == 15
    # Non-overlapping left part has value 10.0
    assert grid.array[0, 2] == pytest.approx(10.0)
    # Overlapping center part has average: (10 + 30) / 2 = 20.0
    assert grid.array[0, 7] == pytest.approx(20.0)
    # Non-overlapping right part has value 30.0
    assert grid.array[0, 12] == pytest.approx(30.0)


def test_stitch_crs_mismatch_refused() -> None:
    """Mismatched CRS across tiles raises GeospatialProcessingError."""
    t1 = _make_tile(crs="EPSG:32643")
    t2 = _make_tile(crs="EPSG:32644")
    with pytest.raises(GeospatialProcessingError, match="differs from base CRS"):
        stitch_dsm_grids([t1, t2])


def test_stitch_non_georeferenced_refused() -> None:
    """Non-georeferenced grid raises MissingCRSError."""
    t1 = _make_tile()
    # Create non-geo tile
    non_geo = DSMGrid(
        array=t1.array,
        valid_mask=t1.valid_mask,
        width=t1.width,
        height=t1.height,
        dtype="float32",
        units=METRIC_UNIT,
        semantics=t1.semantics,
        nodata=NODATA,
        invalid_count=0,
        resampling=ResamplingPolicy.NO_RESAMPLING,
        georeferencing=GeoreferencingLevel.NON_GEOREFERENCED,
        spatial=SpatialContext(kind=SpatialKind.NOT_APPLICABLE),
        depth_model_name="test",
        calibration_method="test",
        calibration_reference="test",
        calibration_scale=1.0,
        calibration_offset=0.0,
        calibration_valid_samples=100,
        provenance=t1.provenance,
    )
    with pytest.raises(MissingCRSError, match="not georeferenced"):
        stitch_dsm_grids([non_geo])
