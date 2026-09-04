"""Overwrite safety and destination path validation."""

from pathlib import Path

import pytest

from depthwizard.errors import ExportError
from depthwizard.export import ExportOptions, export_geotiff
from tests.export.support import agl_grid


def test_existing_target_refused(tmp_path: Path) -> None:
    grid = agl_grid(tmp_path)
    target = tmp_path / "dsm.tif"
    export_geotiff(grid, target)
    before = target.read_bytes()
    with pytest.raises(ExportError, match="already exists"):
        export_geotiff(grid, target)
    assert target.read_bytes() == before


def test_explicit_overwrite_replaces(tmp_path: Path) -> None:
    grid = agl_grid(tmp_path)
    target = tmp_path / "dsm.tif"
    target.write_bytes(b"stale-content")
    result = export_geotiff(grid, target, ExportOptions(overwrite=True))
    assert result.verified is True
    assert target.read_bytes() != b"stale-content"


def test_directory_target_rejected(tmp_path: Path) -> None:
    grid = agl_grid(tmp_path)
    with pytest.raises(ExportError, match="directory"):
        export_geotiff(grid, tmp_path)


def test_bad_suffix_rejected(tmp_path: Path) -> None:
    grid = agl_grid(tmp_path)
    with pytest.raises(ExportError, match="suffix"):
        export_geotiff(grid, tmp_path / "dsm.png")


def test_missing_parent_rejected(tmp_path: Path) -> None:
    grid = agl_grid(tmp_path)
    with pytest.raises(ExportError, match="parent directory"):
        export_geotiff(grid, tmp_path / "no-such-dir" / "dsm.tif")
