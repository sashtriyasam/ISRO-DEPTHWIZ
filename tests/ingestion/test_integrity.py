"""Integrity: deterministic checksums, repeat reads, read-only behavior."""

import hashlib
from pathlib import Path

from depthwizard.ingestion import inspect_input
from depthwizard.ingestion.checksum import sha256_file
from tests.ingestion.fixtures import make_geotiff, make_png


def test_checksum_matches_hashlib(tmp_path: Path) -> None:
    target = make_png(tmp_path / "a.png")
    assert sha256_file(target) == hashlib.sha256(target.read_bytes()).hexdigest()


def test_checksum_chunk_size_independent(tmp_path: Path) -> None:
    target = make_png(tmp_path / "a.png")
    assert sha256_file(target, chunk_size=7) == sha256_file(target)


def test_repeat_inspection_is_equivalent(tmp_path: Path) -> None:
    target = make_geotiff(tmp_path / "scene.tif")
    first = inspect_input(target)
    second = inspect_input(target)
    assert first == second
    assert first is not second


def test_inspection_is_read_only(tmp_path: Path) -> None:
    target = make_png(tmp_path / "a.png")
    before = target.read_bytes()
    snapshot = {child.name for child in tmp_path.iterdir()}
    inspect_input(target)
    assert target.read_bytes() == before
    assert {child.name for child in tmp_path.iterdir()} == snapshot


def test_no_pixel_data_stored(tmp_path: Path) -> None:
    inspection = inspect_input(make_png(tmp_path / "a.png"))
    dumped = inspection.model_dump_json()
    assert "checker" not in dumped
    assert inspection.handle.file_size == len((tmp_path / "a.png").read_bytes())
