"""SIH Mode-A / Mode-B architectural boundary tests.

Mode A (non-georeferenced PNG/JPG): relative geometry only — no
metric units, no CRS, mesh in a pixel-local frame.
Mode B (georeferenced GeoTIFF): relative ML output, then explicit
calibration to metric products with CRS/transform preserved.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from depthwizard.backends.synthetic import SyntheticDepthBackend
from depthwizard.contracts.artifacts import DepthResult, ImageResolution
from depthwizard.contracts.semantics import (
    DepthScale,
    ElevationSemantics,
    GeoreferencingLevel,
)
from depthwizard.contracts.spatial import SpatialContext, SpatialKind
from depthwizard.dsm.rasterize import rasterize_height_product
from depthwizard.errors import InvalidInputError
from depthwizard.height import create_scientific_height_product
from depthwizard.mesh.build import build_terrain_mesh
from depthwizard.mesh.models import CoordinateFrame
from depthwizard.rdsm.mesh import build_relative_mesh
from depthwizard.rdsm.pipeline import run_relative_path
from depthwizard.rdsm.rasterize import rasterize_relative_surface
from tests.height.support import exact_calibration
from tests.ingestion.fixtures import make_png


def make_rgb_geotiff(path: Path) -> Path:
    """Write a 5x4 three-band uint8 GeoTIFF (EPSG:32643)."""
    import rasterio
    from rasterio.crs import CRS
    from rasterio.transform import Affine

    width, height = 5, 4
    grid = np.arange(width * height, dtype="uint8").reshape(height, width)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=3,
        dtype="uint8",
        crs=CRS.from_string("EPSG:32643"),
        transform=Affine(0.5, 0.0, 100.0, 0.0, -0.5, 200.0),
        nodata=0,
    ) as dst:
        dst.write(grid, 1)
        dst.write(grid, 2)
        dst.write(grid, 3)
    return path


def _metric_result() -> DepthResult:
    resolution = ImageResolution(width=2, height=2)
    return DepthResult(
        model_name="m",
        input_resolution=resolution,
        output_resolution=resolution,
        depth_scale=DepthScale.METRIC,
        elevation_semantics=ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
        georeferencing=GeoreferencingLevel.NON_GEOREFERENCED,
        depth_values=(1.0, 2.0, 3.0, 4.0),
        units="meters",
        spatial=SpatialContext(kind=SpatialKind.NOT_APPLICABLE),
    )


def test_mode_a_png_relative_end_to_end(tmp_path: Path) -> None:
    """PNG → relative depth → rDSM → local mesh, never metric."""
    target = make_png(tmp_path / "a.png")
    outcome = run_relative_path(str(target), SyntheticDepthBackend())
    assert outcome.depth.depth_scale is DepthScale.RELATIVE
    assert outcome.depth.units is None
    assert outcome.grid.units is None
    assert outcome.grid.semantics is ElevationSemantics.RELATIVE_SURFACE_RDSM
    assert outcome.grid.georeferencing is GeoreferencingLevel.NON_GEOREFERENCED
    assert outcome.mesh.units is None
    assert outcome.mesh.frame is CoordinateFrame.LOCAL
    assert outcome.mesh.vertex_count == 8 * 6
    assert outcome.input_checksum is not None


def test_mode_a_mesh_matches_metric_topology(tmp_path: Path) -> None:
    """Relative and metric meshes share topology for identical validity."""
    target = make_png(tmp_path / "a.png")
    outcome = run_relative_path(str(target), SyntheticDepthBackend())
    calibration = exact_calibration(
        ElevationSemantics.HEIGHT_AGL_NDSM,
        source_checksum=outcome.input_checksum,
    )
    product = create_scientific_height_product(
        outcome.depth, calibration, ElevationSemantics.HEIGHT_AGL_NDSM
    )
    metric_mesh = build_terrain_mesh(rasterize_height_product(product))
    assert outcome.mesh.vertex_count == metric_mesh.vertex_count
    assert outcome.mesh.triangle_count == metric_mesh.triangle_count
    assert metric_mesh.units == "meters"
    assert outcome.mesh.units is None


def test_mode_b_geotiff_preserves_crs(tmp_path: Path) -> None:
    """Georeferenced input keeps CRS through the relative path untouched."""
    target = make_rgb_geotiff(tmp_path / "scene.tif")
    outcome = run_relative_path(str(target), SyntheticDepthBackend())
    assert outcome.depth.units is None
    assert outcome.mesh.frame is CoordinateFrame.LOCAL
    assert outcome.grid.spatial.kind is SpatialKind.PRESENT
    assert outcome.grid.spatial.details is not None
    assert outcome.grid.spatial.details.crs == "EPSG:32643"


def test_relative_grid_rejects_metric_source() -> None:
    """A metric DepthResult can never become an rDSM grid."""
    with pytest.raises(InvalidInputError, match="RELATIVE"):
        rasterize_relative_surface(_metric_result())


def test_relative_mesh_rejects_metric_grid(tmp_path: Path) -> None:
    """The relative mesher refuses metric DSM grids (no reinterpretation)."""
    from depthwizard.dsm.grid import DSMGrid

    target = make_png(tmp_path / "a.png")
    outcome = run_relative_path(str(target), SyntheticDepthBackend())
    calibration = exact_calibration(
        ElevationSemantics.HEIGHT_AGL_NDSM,
        source_checksum=outcome.input_checksum,
    )
    product = create_scientific_height_product(
        outcome.depth, calibration, ElevationSemantics.HEIGHT_AGL_NDSM
    )
    metric_grid = rasterize_height_product(product)
    assert isinstance(metric_grid, DSMGrid)
    with pytest.raises(TypeError, match="RelativeSurfaceGrid"):
        build_relative_mesh(metric_grid)  # type: ignore[arg-type]


def test_metric_product_requires_calibration_object(tmp_path: Path) -> None:
    """Metres demand a real CalibrationResult, never a bare mapping."""
    from depthwizard.calibration.models import CalibrationResult

    target = make_png(tmp_path / "a.png")
    outcome = run_relative_path(str(target), SyntheticDepthBackend())
    with pytest.raises(TypeError, match="CalibrationResult"):
        create_scientific_height_product(
            outcome.depth,
            {"scale": 2.5, "offset": 10.0},  # type: ignore[arg-type]
            ElevationSemantics.HEIGHT_AGL_NDSM,
        )
    assert issubclass(CalibrationResult, object)


def test_relative_values_never_labelled_metres(tmp_path: Path) -> None:
    """rDSM grid and mesh carry no metre claim anywhere in the payload."""
    target = make_png(tmp_path / "a.png")
    outcome = run_relative_path(str(target), SyntheticDepthBackend())
    payload = json.dumps(
        {
            "grid_units": outcome.grid.units,
            "mesh_units": outcome.mesh.units,
            "semantics": outcome.grid.semantics.value,
        }
    )
    assert "meters" not in payload
