"""DEM inspection: valid metadata, rejections, units and semantics."""

from pathlib import Path

import pytest

from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.dem.inspect import inspect_dem
from depthwizard.errors import (
    GeospatialProcessingError,
    InvalidInputError,
    MissingCRSError,
    UnsupportedFormatError,
)
from depthwizard.ingestion.formats import DetectedFormat
from tests.dem.support import dem_inspection, make_dem


def test_valid_inspection(tmp_path: Path) -> None:
    inspection = dem_inspection(tmp_path)
    assert inspection.detected_format is DetectedFormat.TIFF
    assert (inspection.width, inspection.height) == (6, 5)
    assert inspection.band_count == 1
    assert inspection.dtype == "float32"
    assert inspection.nodata == -9999.0
    assert inspection.crs == "EPSG:32643"
    assert inspection.transform.as_tuple() == (99.0, 1.0, 0.0, 201.0, 0.0, -1.0)
    assert (inspection.bounds.min_x, inspection.bounds.min_y) == (99.0, 196.0)
    assert (inspection.bounds.max_x, inspection.bounds.max_y) == (105.0, 201.0)
    assert inspection.resolution == 1.0
    assert inspection.vertical_units == "meters"
    assert inspection.vertical_semantics is ElevationSemantics.TERRAIN_ELEVATION
    assert inspection.file_size > 0
    assert len(inspection.sha256) == 64


def test_checksum_deterministic(tmp_path: Path) -> None:
    first = dem_inspection(tmp_path, name="a.tif")
    second = dem_inspection(tmp_path, name="b.tif")
    assert first.sha256 == second.sha256


def test_missing_file() -> None:
    with pytest.raises(InvalidInputError, match="not found"):
        inspect_dem("no-such-dem.tif", vertical_units="meters")


def test_directory(tmp_path: Path) -> None:
    with pytest.raises(InvalidInputError, match="not a file"):
        inspect_dem(tmp_path, vertical_units="meters")


def test_empty_file(tmp_path: Path) -> None:
    target = tmp_path / "empty.tif"
    target.write_bytes(b"")
    with pytest.raises(InvalidInputError, match="empty"):
        inspect_dem(target, vertical_units="meters")


def test_unsupported_format(tmp_path: Path) -> None:
    target = tmp_path / "dem.pdf"
    target.write_bytes(b"%PDF-1.7\n")
    with pytest.raises(UnsupportedFormatError):
        inspect_dem(target, vertical_units="meters")


def test_corrupt_tiff(tmp_path: Path) -> None:
    target = tmp_path / "bad.tif"
    target.write_bytes(bytes([0x49, 0x49, 0x2A, 0x00]) + b"\x00" * 64)
    with pytest.raises(InvalidInputError):
        inspect_dem(target, vertical_units="meters")


def test_multiband_rejected(tmp_path: Path) -> None:
    with pytest.raises(InvalidInputError, match="single elevation band"):
        dem_inspection(tmp_path, count=3)


def test_non_numeric_dtype_rejected(tmp_path: Path) -> None:
    with pytest.raises(InvalidInputError, match="numeric"):
        dem_inspection(tmp_path, dtype="complex64")


def test_missing_crs(tmp_path: Path) -> None:
    with pytest.raises(MissingCRSError, match="requires a CRS"):
        dem_inspection(tmp_path, crs=None, transform=None)


def test_missing_transform(tmp_path: Path) -> None:
    make_dem(tmp_path / "notransform.tif", transform=None)
    with pytest.raises(GeospatialProcessingError, match="no geotransform"):
        inspect_dem(tmp_path / "notransform.tif", vertical_units="meters")


def test_singular_transform(tmp_path: Path) -> None:
    # A zero-determinant geotransform does not survive GTiff persistence
    # in this stack (verified): the file comes back CRS-less, so
    # inspection refuses it for missing CRS. The invertibility guard
    # itself is unit-covered in S7 for non-file paths.
    make_dem(tmp_path / "singular.tif", transform=(100.0, 0.0, 0.0, 200.0, 0.0, -0.5))
    with pytest.raises(MissingCRSError, match="requires a CRS"):
        inspect_dem(tmp_path / "singular.tif", vertical_units="meters")


def test_units_required(tmp_path: Path) -> None:
    target = make_dem(tmp_path / "dem.tif")
    with pytest.raises(GeospatialProcessingError, match="vertical_units"):
        inspect_dem(target)
    with pytest.raises(GeospatialProcessingError, match="vertical_units"):
        inspect_dem(target, vertical_units="feet")
    with pytest.raises(GeospatialProcessingError, match="vertical_units"):
        inspect_dem(target, vertical_units="")


def test_valid_units_accepted(tmp_path: Path) -> None:
    inspection = dem_inspection(tmp_path)
    assert inspection.vertical_units == "meters"
