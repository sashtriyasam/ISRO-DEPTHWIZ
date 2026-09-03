"""Supported-format ingestion: PNG, JPEG, plain TIFF, GeoTIFF."""

from pathlib import Path

from depthwizard.contracts.semantics import GeoreferencingLevel
from depthwizard.contracts.spatial import SpatialKind
from depthwizard.ingestion import DetectedFormat, InspectionStatus, inspect_input
from tests.ingestion.fixtures import (
    JPEG_SIZE,
    PNG_SIZE,
    TIFF_SIZE,
    make_geotiff,
    make_jpeg,
    make_plain_tiff,
    make_png,
)


def test_valid_png(tmp_path: Path) -> None:
    inspection = inspect_input(make_png(tmp_path / "sample.png"))
    assert inspection.detected_format is DetectedFormat.PNG
    assert (inspection.width, inspection.height) == PNG_SIZE
    assert inspection.band_count == 3
    assert inspection.dtype == "RGB"
    assert inspection.georeferencing is GeoreferencingLevel.NON_GEOREFERENCED
    assert inspection.spatial.kind is SpatialKind.NOT_APPLICABLE
    assert inspection.spatial.details is None
    assert inspection.status is InspectionStatus.VALID
    assert len(inspection.handle.sha256) == 64
    assert inspection.handle.file_size > 0


def test_valid_jpeg(tmp_path: Path) -> None:
    inspection = inspect_input(make_jpeg(tmp_path / "photo.jpeg"))
    assert inspection.detected_format is DetectedFormat.JPEG
    assert (inspection.width, inspection.height) == JPEG_SIZE
    assert inspection.band_count == 3
    assert inspection.dtype == "RGB"
    assert inspection.georeferencing is GeoreferencingLevel.NON_GEOREFERENCED
    assert inspection.status is InspectionStatus.VALID


def test_uppercase_suffix_handled(tmp_path: Path) -> None:
    inspection = inspect_input(make_jpeg(tmp_path / "PHOTO.JpG"))
    assert inspection.detected_format is DetectedFormat.JPEG
    assert inspection.georeferencing is GeoreferencingLevel.NON_GEOREFERENCED


def test_content_sniffed_without_suffix(tmp_path: Path) -> None:
    raw = make_png(tmp_path / "sample.png").read_bytes()
    suffixless = tmp_path / "mystery"
    suffixless.write_bytes(raw)
    inspection = inspect_input(suffixless)
    assert inspection.detected_format is DetectedFormat.PNG
    assert (inspection.width, inspection.height) == PNG_SIZE


def test_plain_tiff_without_crs(tmp_path: Path) -> None:
    inspection = inspect_input(make_plain_tiff(tmp_path / "plain.tif"))
    assert inspection.detected_format is DetectedFormat.TIFF
    assert (inspection.width, inspection.height) == TIFF_SIZE
    assert inspection.band_count == 1
    assert inspection.dtype == "uint8"
    # No CRS: valid input, but not georeferenced. Identity fallback
    # transform must not be mistaken for georeferencing.
    assert inspection.georeferencing is GeoreferencingLevel.NON_GEOREFERENCED
    assert inspection.spatial.kind is SpatialKind.UNAVAILABLE
    assert inspection.spatial.details is None


def test_geotiff_with_crs(tmp_path: Path) -> None:
    inspection = inspect_input(make_geotiff(tmp_path / "scene.tiff"))
    assert inspection.detected_format is DetectedFormat.TIFF
    assert (inspection.width, inspection.height) == TIFF_SIZE
    assert inspection.band_count == 2
    assert inspection.dtype == "uint8"
    assert inspection.georeferencing is GeoreferencingLevel.GEOREFERENCED_NO_ELEVATION_REFERENCE
    assert inspection.spatial.kind is SpatialKind.PRESENT
    details = inspection.spatial.details
    assert details is not None
    assert details.crs == "EPSG:32643"
    assert details.transform is not None
    # GDAL tag order: (x-origin, pixel-width, row-rot, y-origin, col-rot, pixel-height).
    assert details.transform.as_tuple() == (100.0, 0.5, 0.0, 200.0, 0.0, -0.5)
    assert details.bounds is not None
    assert (details.bounds.min_x, details.bounds.min_y) == (100.0, 198.0)
    assert (details.bounds.max_x, details.bounds.max_y) == (102.5, 200.0)
    assert details.resolution_gsd == 0.5
    assert details.nodata == 0.0
    assert (details.raster_width, details.raster_height) == TIFF_SIZE
    # Never DEM/GCP-supported from inspection alone.
    assert inspection.georeferencing not in (
        GeoreferencingLevel.GEOREFERENCED_WITH_DEM,
        GeoreferencingLevel.GEOREFERENCED_WITH_GCP,
    )
