"""Public ingestion API: ``inspect_input(path) -> InputInspection``.

Small, deterministic and read-only: no registry, cache, database or
async machinery. A supported non-georeferenced image is valid input —
absence of georeferencing is not an ingestion failure.
"""

from __future__ import annotations

from pathlib import Path

from depthwizard.ingestion import readers
from depthwizard.ingestion.formats import DetectedFormat, resolve_format
from depthwizard.ingestion.models import InputHandle, InputInspection


def inspect_input(path: str | Path) -> InputInspection:
    """Inspect an input file and return its typed inspection result.

    Raises :class:`InvalidInputError` for missing/directory/empty/
    corrupt/unreadable inputs and :class:`UnsupportedFormatError` for
    formats outside the allow-list. Never raises ``MissingCRSError``:
    a PNG/JPEG without CRS is a valid supported input state.
    """
    handle = InputHandle.from_path(path)
    candidate = Path(handle.source_path)
    detected = resolve_format(candidate)
    if detected is DetectedFormat.TIFF:
        facts = readers.inspect_geotiff(candidate, handle.display_name)
    else:
        facts = readers.inspect_pillow(candidate, handle.display_name, detected)
    return InputInspection(
        handle=handle,
        detected_format=facts.detected_format,
        width=facts.width,
        height=facts.height,
        band_count=facts.band_count,
        dtype=facts.dtype,
        georeferencing=facts.georeferencing,
        spatial=facts.spatial,
        source_format_metadata=facts.source_format_metadata,
    )
