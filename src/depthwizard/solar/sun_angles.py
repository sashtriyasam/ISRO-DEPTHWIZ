"""Solar angle resolver: metadata-first, explicit-override, hard refusal.

Resolves sun elevation and azimuth from one of two sources:

1. **Image metadata** — ``InputInspection.source_format_metadata`` keyed by
   the common tag names used by Sentinel-2, Landsat, WorldView, Pléiades and
   similar satellite image formats (``SUN_ELEVATION``, ``SUN_AZIMUTH``,
   ``SOLAR_ELEVATION``, ``SOLAR_AZIMUTH``).

2. **Explicit caller override** — the caller supplies numeric angles directly,
   overriding anything in the metadata.

If neither is available the resolver raises ``InvalidInputError``.  It never
infers angles from acquisition time, geographical position, or any other
derived data, because that inference path requires accuracy guarantees this
module cannot verify.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from depthwizard.errors import InvalidInputError
from depthwizard.ingestion.models import InputInspection
from depthwizard.solar.models import MAX_ELEVATION_DEG, MIN_ELEVATION_DEG

#: Metadata keys searched in order of preference.  Comparison is
#: case-insensitive; the first matching key wins.
_ELEVATION_KEYS: tuple[str, ...] = (
    "SUN_ELEVATION",
    "SOLAR_ELEVATION",
    "MEAN_SUN_ELEVATION",
    "sun_elevation",
    "solar_elevation",
)
_AZIMUTH_KEYS: tuple[str, ...] = (
    "SUN_AZIMUTH",
    "SOLAR_AZIMUTH",
    "MEAN_SUN_AZIMUTH",
    "sun_azimuth",
    "solar_azimuth",
)


class SunAngles(BaseModel):
    """Resolved solar geometry for one image acquisition.

    Both angles are validated at construction; the ``source`` field records
    where they came from so provenance is explicit in every downstream record.
    """

    model_config = ConfigDict(frozen=True)

    elevation_deg: float = Field(
        description="Solar elevation above the horizon, strictly inside (0, 90) degrees."
    )
    azimuth_deg: float = Field(
        description="Solar azimuth in degrees [0, 360): direction TO the sun."
    )
    source: Literal["metadata", "explicit"] = Field(
        description="Where the angles came from: image metadata or explicit caller supply."
    )

    @model_validator(mode="after")
    def _validate_angles(self) -> SunAngles:
        if not (MIN_ELEVATION_DEG < self.elevation_deg < MAX_ELEVATION_DEG):
            raise ValueError(
                f"sun elevation must lie strictly inside "
                f"({MIN_ELEVATION_DEG}, {MAX_ELEVATION_DEG}) degrees; "
                f"got {self.elevation_deg}"
            )
        if not (0.0 <= self.azimuth_deg < 360.0):
            raise ValueError(
                f"sun azimuth must lie in [0, 360) degrees; got {self.azimuth_deg}"
            )
        return self


def _search_keys(metadata: dict[str, str], keys: tuple[str, ...]) -> float | None:
    """Search ``metadata`` for any of ``keys`` (case-insensitive); return float or None."""
    upper = {k.upper(): v for k, v in metadata.items()}
    for key in keys:
        raw = upper.get(key.upper())
        if raw is not None:
            try:
                return float(raw)
            except (ValueError, TypeError):
                continue
    return None


def resolve_sun_angles(
    inspection: InputInspection,
    *,
    sun_elevation_deg: float | None = None,
    sun_azimuth_deg: float | None = None,
) -> SunAngles:
    """Resolve solar elevation and azimuth for ``inspection``.

    Resolution order:

    1. If **both** ``sun_elevation_deg`` and ``sun_azimuth_deg`` are supplied
       by the caller, they are used directly (source = ``"explicit"``).  A
       partially explicit supply (only one angle) is refused to prevent silent
       mixing of different sources.

    2. Otherwise the ``inspection.source_format_metadata`` dict is searched
       for known solar-angle tag names (source = ``"metadata"``).

    3. If neither succeeds, an :class:`~depthwizard.errors.InvalidInputError`
       is raised — sun angles are never invented.

    Parameters
    ----------
    inspection:
        Result of ``inspect_input()`` for the input image.
    sun_elevation_deg:
        Caller-supplied solar elevation in degrees.  Must be paired with
        ``sun_azimuth_deg``; supplying only one raises immediately.
    sun_azimuth_deg:
        Caller-supplied solar azimuth in degrees [0, 360).
    """
    if not isinstance(inspection, InputInspection):
        raise TypeError(
            f"inspection must be an InputInspection, got {type(inspection).__name__}"
        )

    # --- explicit caller supply ---
    both_explicit = sun_elevation_deg is not None and sun_azimuth_deg is not None
    one_explicit = (sun_elevation_deg is None) != (sun_azimuth_deg is None)
    if one_explicit:
        raise InvalidInputError(
            "sun angles must be supplied together (both elevation and azimuth) "
            "or not at all; partially explicit input is refused to prevent "
            "silent mixing of different angle sources"
        )
    if both_explicit:
        assert sun_elevation_deg is not None and sun_azimuth_deg is not None
        return SunAngles(
            elevation_deg=sun_elevation_deg,
            azimuth_deg=sun_azimuth_deg,
            source="explicit",
        )

    # --- metadata resolution ---
    meta = inspection.source_format_metadata
    elev = _search_keys(meta, _ELEVATION_KEYS)
    azim = _search_keys(meta, _AZIMUTH_KEYS)

    if elev is not None and azim is not None:
        return SunAngles(elevation_deg=elev, azimuth_deg=azim, source="metadata")

    if elev is not None or azim is not None:
        missing = "azimuth" if elev is not None else "elevation"
        raise InvalidInputError(
            f"image metadata contains sun {('elevation' if elev is not None else 'azimuth')} "
            f"but not sun {missing}; cannot resolve angles from partial metadata "
            "(supply both explicitly or ensure the metadata is complete)"
        )

    raise InvalidInputError(
        "sun angles could not be resolved: no sun-angle metadata found in the image "
        "(keys searched: SUN_ELEVATION, SUN_AZIMUTH, SOLAR_ELEVATION, SOLAR_AZIMUTH) "
        "and no explicit angles were supplied. "
        "Provide sun_elevation_deg and sun_azimuth_deg from the image acquisition record."
    )
