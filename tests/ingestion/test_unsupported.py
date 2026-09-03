"""Unsupported formats raise UnsupportedFormatError (never InvalidInput)."""

from pathlib import Path

import pytest

from depthwizard.errors import InvalidInputError, UnsupportedFormatError
from depthwizard.ingestion import inspect_input


def _write(tmp_path: Path, name: str, payload: bytes) -> Path:
    target = tmp_path / name
    target.write_bytes(payload)
    return target


def test_pdf_rejected(tmp_path: Path) -> None:
    target = _write(tmp_path, "doc.pdf", b"%PDF-1.7\n%reasonable\ntrailer\n")
    with pytest.raises(UnsupportedFormatError):
        inspect_input(target)


def test_bmp_rejected(tmp_path: Path) -> None:
    target = _write(tmp_path, "img.bmp", b"BM" + b"\x00" * 64)
    with pytest.raises(UnsupportedFormatError):
        inspect_input(target)


def test_webp_rejected(tmp_path: Path) -> None:
    target = _write(tmp_path, "img.webp", b"RIFF....WEBPVP8 " + b"\x00" * 32)
    with pytest.raises(UnsupportedFormatError):
        inspect_input(target)


def test_arbitrary_binary_rejected(tmp_path: Path) -> None:
    target = _write(tmp_path, "blob.bin", bytes(range(256)))
    with pytest.raises(UnsupportedFormatError):
        inspect_input(target)


def test_unsupported_error_is_not_invalid_input(tmp_path: Path) -> None:
    target = _write(tmp_path, "blob.bin", b"\x00\x01\x02\x03")
    with pytest.raises(UnsupportedFormatError) as exc_info:
        inspect_input(target)
    assert not isinstance(exc_info.value, InvalidInputError)
    assert "allow-list" in str(exc_info.value)
