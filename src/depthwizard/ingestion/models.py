"""Typed immutable input handle and inspection result.

``InputHandle`` is the lightweight identity record (path, size, checksum).
``InputInspection`` is the full read-only inspection outcome, reusing the
foundation spatial contracts instead of inventing new representations.

Pixel data is never stored here — only metadata.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from depthwizard.contracts.semantics import GeoreferencingLevel
from depthwizard.contracts.spatial import SpatialContext, SpatialKind
from depthwizard.errors import InvalidInputError
from depthwizard.ingestion.checksum import sha256_file
from depthwizard.ingestion.formats import DetectedFormat


class InspectionStatus(str, Enum):
    """Validation outcome. Only valid inputs are returned (invalid raises)."""

    VALID = "valid"


class InputHandle(BaseModel):
    """Identity of an input file: where it is, how big, what it hashes to."""

    model_config = ConfigDict(frozen=True)

    source_path: str = Field(description="Path as supplied by the caller (not absolutised).")
    display_name: str = Field(description="Basename for diagnostics; no directory leaked.")
    file_size: int = Field(gt=0, description="File size in bytes; zero-byte files are invalid.")
    sha256: str = Field(min_length=64, max_length=64, description="Hex SHA-256 of file bytes.")

    @classmethod
    def from_path(cls, path: str | Path) -> InputHandle:
        """Build a handle, validating file safety (read-only, no writes).

        Raises :class:`InvalidInputError` for missing paths, directories,
        empty files and unreadable files.
        """
        candidate = Path(path)
        display = candidate.name or str(candidate)
        try:
            is_file = candidate.is_file()
        except OSError as exc:
            raise InvalidInputError(f"unreadable input path: {display}: {exc}") from exc
        if not is_file:
            if candidate.exists():
                raise InvalidInputError(f"input is not a file (directory?): {display}")
            raise InvalidInputError(f"input file not found: {display}")
        try:
            size = candidate.stat().st_size
        except OSError as exc:
            raise InvalidInputError(f"unreadable input file: {display}: {exc}") from exc
        if size == 0:
            raise InvalidInputError(f"input file is empty (0 bytes): {display}")
        return cls(
            source_path=str(candidate),
            display_name=display,
            file_size=size,
            sha256=sha256_file(candidate),
        )


class InputInspection(BaseModel):
    """Complete read-only inspection outcome for one input file."""

    model_config = ConfigDict(frozen=True)

    handle: InputHandle
    detected_format: DetectedFormat
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    band_count: int | None = Field(default=None, gt=0)
    dtype: str | None = Field(
        default=None,
        description="Sample type descriptor: Pillow mode ('RGB','L',...) or "
        "raster dtype name ('uint8',...). None when mixed/unknown.",
    )
    georeferencing: GeoreferencingLevel
    spatial: SpatialContext
    source_format_metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Reader name/version, driver, mode and other format facts.",
    )
    status: InspectionStatus = InspectionStatus.VALID

    @model_validator(mode="after")
    def _check_spatial_honesty(self) -> InputInspection:
        if self.georeferencing is GeoreferencingLevel.NON_GEOREFERENCED:
            if self.spatial.kind is SpatialKind.PRESENT:
                raise ValueError("NON_GEOREFERENCED input must not carry PRESENT spatial details")
        if self.spatial.kind is SpatialKind.PRESENT and self.georeferencing not in (
            GeoreferencingLevel.GEOREFERENCED_NO_ELEVATION_REFERENCE,
            GeoreferencingLevel.GEOREFERENCED_WITH_DEM,
            GeoreferencingLevel.GEOREFERENCED_WITH_GCP,
        ):
            raise ValueError("PRESENT spatial details require a georeferenced level")
        return self
