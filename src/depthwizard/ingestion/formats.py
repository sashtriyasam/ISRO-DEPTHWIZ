"""File-format detection for input ingestion.

Detection is content-led: the filename suffix is a hint, but the first
bytes of the file (magic signatures) decide. A supported suffix with
unrelated content is never accepted on suffix alone.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from depthwizard.errors import InvalidInputError, UnsupportedFormatError

_PNG_MAGIC = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
_JPEG_MAGIC = bytes([0xFF, 0xD8, 0xFF])
_TIFF_MAGIC_LE = bytes([0x49, 0x49, 0x2A, 0x00])
_TIFF_MAGIC_BE = bytes([0x4D, 0x4D, 0x00, 0x2A])

_SUFFIX_MAP: dict[str, DetectedFormat] = {}


class DetectedFormat(str, Enum):
    """Formats the ingestion layer can safely validate."""

    PNG = "png"
    JPEG = "jpeg"
    TIFF = "tiff"


_SUFFIX_MAP.update(
    {
        ".png": DetectedFormat.PNG,
        ".jpg": DetectedFormat.JPEG,
        ".jpeg": DetectedFormat.JPEG,
        ".tif": DetectedFormat.TIFF,
        ".tiff": DetectedFormat.TIFF,
    }
)

#: Public allow-list of supported filename suffixes (single source of
#: truth; service capabilities and validators reuse this).
SUPPORTED_SUFFIXES: tuple[str, ...] = tuple(sorted(_SUFFIX_MAP))


def sniff_signature(header: bytes) -> DetectedFormat | None:
    """Identify a supported format from leading file bytes (no I/O)."""
    if header.startswith(_PNG_MAGIC):
        return DetectedFormat.PNG
    if header.startswith(_JPEG_MAGIC):
        return DetectedFormat.JPEG
    if header.startswith((_TIFF_MAGIC_LE, _TIFF_MAGIC_BE)):
        return DetectedFormat.TIFF
    return None


def read_header(path: Path, size: int = 10) -> bytes:
    """Read leading bytes for signature sniffing."""
    try:
        with open(path, "rb") as handle:
            return handle.read(size)
    except OSError as exc:
        raise InvalidInputError(f"unreadable input file: {path.name}: {exc}") from exc


def resolve_format(path: Path) -> DetectedFormat:
    """Resolve the ingestion format for a path using suffix hint + content.

    A recognised suffix selects the claimed format and the reader then
    verifies the content actually decodes as that format (mislabeled or
    corrupt files raise :class:`InvalidInputError`). Unknown suffixes
    fall back to content sniffing, so a valid image with an unusual name
    is still handled. Content matching no supported signature raises
    :class:`UnsupportedFormatError`.
    """
    suffix_hint = _SUFFIX_MAP.get(path.suffix.lower())
    if suffix_hint is not None:
        return suffix_hint
    sniffed = sniff_signature(read_header(path))
    if sniffed is not None:
        return sniffed
    raise UnsupportedFormatError(
        f"unsupported input format: {path.name or str(path)} "
        "(extension and content are not in the allow-list: "
        ".png, .jpg, .jpeg, .tif, .tiff)"
    )
