"""Solar-shadow integration: image → height constraints.

``solar_observations_from_image`` is the single public function: it chains
shadow detection, sun-angle resolution, and height estimation into a list of
``ShadowHeightConstraint`` objects that callers can use as independent height
cues.

These constraints are NOT calibration replacements and NOT automatic ground
truth.  The returned objects carry full provenance (sun source, detection
method, GSD source, assumptions) so that every downstream decision is
auditable.

Constraints with quality ``"occluded"`` or ``"uncertain"`` are included but
flagged; callers may choose to filter them.  Ambiguous-direction observations
are silently skipped (``estimate_height`` raises; this function catches and
skips) and recorded in the returned ``skipped_count``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray
else:
    from numpy.typing import NDArray
from depthwizard.errors import InvalidInputError
from depthwizard.ingestion.models import InputInspection
from depthwizard.solar.geometry import estimate_height
from depthwizard.solar.models import PixelPoint, ShadowObservation
from depthwizard.solar.shadow_detect import (
    gsd_from_inspection,
    is_north_up,
    region_pixels,
    segment_shadows,
)
from depthwizard.solar.sun_angles import SunAngles, resolve_sun_angles


def load_image_rgb(inspection: InputInspection) -> NDArray[np.uint8]:
    """Load image pixels as HWC uint8 RGB (shared loader, see ``ingestion.pixels``)."""
    from depthwizard.ingestion.pixels import load_model_rgb

    return load_model_rgb(inspection).rgb


@dataclass(frozen=True)
class SolarIntegrationResult:
    """Result of one solar-shadow integration pass over an image.

    ``constraints`` carries the accepted height cues; ``skipped_count``
    records how many regions were detected but skipped (direction
    contradiction, zero-length shadow, etc.).  ``refused_reason`` is
    non-None only when the integration could not run at all (no sun angles,
    no numpy, etc.).
    """

    constraints: tuple[Any, ...]
    skipped_count: int
    detected_count: int
    refused_reason: str | None = None

    @property
    def count(self) -> int:
        return len(self.constraints)


def solar_observations_from_image(
    inspection: InputInspection,
    rgb_array: object,
    *,
    sun_elevation_deg: float | None = None,
    sun_azimuth_deg: float | None = None,
    min_area_px: int = 20,
    gsd_override: float | None = None,
    assume_north_up: bool = False,
) -> SolarIntegrationResult:
    """Derive shadow height constraints from one image.

    Parameters
    ----------
    inspection:
        ``InputInspection`` result for the source image (provides metadata
        for sun-angle resolution and GSD extraction).
    rgb_array:
        HxWx3 uint8 NumPy array of the image pixels.
    sun_elevation_deg:
        Explicit solar elevation override.  Must be paired with
        ``sun_azimuth_deg``.  When both are ``None`` the function reads
        sun angles from ``inspection.source_format_metadata``.
    sun_azimuth_deg:
        Explicit solar azimuth override (see above).
    min_area_px:
        Minimum shadow region area in pixels (passed to ``detect_shadows``).
    gsd_override:
        Force a specific GSD (m/px) instead of reading it from the
        inspection's affine transform.  Only for cases where the caller has
        an independent GSD measurement; ``None`` uses the transform (which
        must be a projected metric CRS: degrees are never treated as metres).
    assume_north_up:
        Caller declares that image rows run north to south. Required for
        inputs without a north-up transform (e.g. PNG), because the shadow is
        measured along the direction opposite the sun azimuth.

    Returns
    -------
    SolarIntegrationResult
        Always returns a result; ``refused_reason`` is set when no
        angles or GSD are available and no constraints can be produced.
    """
    if not isinstance(inspection, InputInspection):
        raise TypeError(f"inspection must be an InputInspection, got {type(inspection).__name__}")

    # --- resolve sun angles ---
    try:
        sun_angles: SunAngles = resolve_sun_angles(
            inspection,
            sun_elevation_deg=sun_elevation_deg,
            sun_azimuth_deg=sun_azimuth_deg,
        )
    except InvalidInputError as exc:
        return SolarIntegrationResult(
            constraints=(),
            skipped_count=0,
            detected_count=0,
            refused_reason=str(exc),
        )

    # --- resolve GSD ---
    gsd: float | None = (
        gsd_override if gsd_override is not None else gsd_from_inspection(inspection)
    )
    if gsd is None or not (math.isfinite(gsd) and gsd > 0.0):
        return SolarIntegrationResult(
            constraints=(),
            skipped_count=0,
            detected_count=0,
            refused_reason=(
                "GSD (ground sampling distance) could not be resolved from the "
                "image transform.  Shadow trig requires a metric pixel size from a "
                "projected metre CRS with square, axis-aligned pixels; supply "
                "gsd_override for other inputs."
            ),
        )

    # --- orientation: shadows are measured along (sun azimuth + 180°) ---
    if not (is_north_up(inspection) or assume_north_up):
        return SolarIntegrationResult(
            constraints=(),
            skipped_count=0,
            detected_count=0,
            refused_reason=(
                "Image orientation is unknown: the shadow direction cannot be related "
                "to the sun azimuth. Use a north-up georeferenced raster or declare "
                "the image north-up explicitly."
            ),
        )
    shadow_azimuth = math.radians((sun_angles.azimuth_deg + 180.0) % 360.0)
    # Pixel frame: north = -row, east = +col.
    dir_row = -math.cos(shadow_azimuth)
    dir_col = math.sin(shadow_azimuth)
    expected_angle = math.degrees(math.atan2(dir_row, dir_col))

    # --- shadow detection ---
    import importlib.util

    if importlib.util.find_spec("numpy") is None:
        return SolarIntegrationResult(
            constraints=(),
            skipped_count=0,
            detected_count=0,
            refused_reason="numpy is required for shadow detection but is not installed.",
        )

    from typing import cast

    import numpy as np

    labels, regions = segment_shadows(cast(np.ndarray, rgb_array), min_area_px=min_area_px)
    pixels = region_pixels(labels)

    source_id = inspection.handle.display_name
    source_checksum = inspection.handle.sha256

    constraints = []
    skipped = 0

    for region in regions:
        rows, cols = pixels[region.region_id]
        # Extent along the shadow direction: the foot is the pixel nearest the
        # sun, the tip the farthest; length spans the whole shadow.
        projection = rows * dir_row + cols * dir_col
        p_min, p_max = float(projection.min()), float(projection.max())
        c_row, c_col = float(rows.mean()), float(cols.mean())
        p_mid = c_row * dir_row + c_col * dir_col
        # Foot and tip on the region's central axis along the shadow direction.
        base = PixelPoint(
            row=int(round(c_row + dir_row * (p_min - p_mid))),
            col=int(round(c_col + dir_col * (p_min - p_mid))),
        )
        tip = PixelPoint(
            row=int(round(c_row + dir_row * (p_max - p_mid))),
            col=int(round(c_col + dir_col * (p_max - p_mid))),
        )
        length_px = p_max - p_min + 1.0
        if tip == base:
            skipped += 1
            continue

        try:
            obs = ShadowObservation(
                source_input_id=source_id,
                source_checksum=source_checksum,
                base=base,
                tip=tip,
                shadow_length_px=length_px,
                gsd_m_per_px=gsd,
                sun_elevation_deg=sun_angles.elevation_deg,
                sun_azimuth_deg=sun_angles.azimuth_deg,
                expected_shadow_angle_deg=expected_angle,
                angle_tolerance_deg=15.0,
                method=f"otsu-luminance-v2-azimuth-extent;sun-source={sun_angles.source}",
                quality=region.quality,
            )
        except (ValueError, TypeError):
            skipped += 1
            continue

        try:
            constraint = estimate_height(obs)
        except InvalidInputError:
            # Direction contradiction or non-positive height — skip.
            skipped += 1
            continue

        constraints.append(constraint)

    return SolarIntegrationResult(
        constraints=tuple(constraints),
        skipped_count=skipped,
        detected_count=len(regions),
        refused_reason=None,
    )
