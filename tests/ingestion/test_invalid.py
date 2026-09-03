"""Invalid-input mapping: every failure becomes InvalidInputError."""

from pathlib import Path

import pytest

from depthwizard.errors import InvalidInputError
from depthwizard.ingestion import InputHandle, inspect_input
from tests.ingestion.fixtures import make_jpeg, make_png


def test_missing_path() -> None:
    with pytest.raises(InvalidInputError, match="not found"):
        inspect_input("does-not-exist.png")


def test_directory_instead_of_file(tmp_path: Path) -> None:
    with pytest.raises(InvalidInputError, match="not a file"):
        inspect_input(tmp_path)


def test_empty_file(tmp_path: Path) -> None:
    empty = tmp_path / "empty.png"
    empty.write_bytes(b"")
    with pytest.raises(InvalidInputError, match="empty"):
        inspect_input(empty)


def test_corrupt_jpeg_content(tmp_path: Path) -> None:
    bad = tmp_path / "bad.jpg"
    bad.write_bytes(b"\xff\xd8\xff not a real jpeg payload \x00\x01\x02")
    with pytest.raises(InvalidInputError):
        inspect_input(bad)


def test_truncated_png(tmp_path: Path) -> None:
    raw = make_png(tmp_path / "good.png").read_bytes()
    truncated = tmp_path / "cut.png"
    truncated.write_bytes(raw[:16])
    with pytest.raises(InvalidInputError):
        inspect_input(truncated)


def test_corrupt_tiff(tmp_path: Path) -> None:
    bad = tmp_path / "bad.tif"
    bad.write_bytes(bytes([0x49, 0x49, 0x2A, 0x00]) + b"\x00" * 64)
    with pytest.raises(InvalidInputError):
        inspect_input(bad)


def test_mislabeled_content_rejected(tmp_path: Path) -> None:
    raw = make_png(tmp_path / "good.png").read_bytes()
    fake = tmp_path / "fake.jpg"
    fake.write_bytes(raw)
    with pytest.raises(InvalidInputError, match="mislabeled"):
        inspect_input(fake)


def test_handle_from_path_validates(tmp_path: Path) -> None:
    handle = InputHandle.from_path(make_jpeg(tmp_path / "a.jpg"))
    assert handle.display_name == "a.jpg"
    assert handle.file_size > 0
    with pytest.raises(InvalidInputError):
        InputHandle.from_path(tmp_path / "missing.jpg")


def test_domain_errors_do_not_leak_library_types(tmp_path: Path) -> None:
    bad = tmp_path / "bad.jpg"
    bad.write_bytes(b"garbage-bytes-not-an-image")
    with pytest.raises(InvalidInputError) as exc_info:
        inspect_input(bad)
    assert not isinstance(exc_info.value, OSError)
