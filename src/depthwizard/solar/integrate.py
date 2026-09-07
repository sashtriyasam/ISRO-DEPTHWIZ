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
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

from depthwizard.errors import InvalidInputError
from depthwizard.ingestion.models import InputInspection
from depthwizard.solar.geometry import estimate_height
from depthwizard.solar.models import PixelPoint, ShadowObservation
from depthwizard.solar.shadow_detect import ShadowRegion, detect_shadows, gsd_from_inspection
from depthwizard.solar.sun_angles import SunAngles, resolve_sun_angles


def load_image_rgb(inspection: InputInspection) -> np.ndarray:
    """Load image pixels as HWC uint8 RGB from an InputInspection."""
    import numpy as np

    path = Path(inspection.handle.source_path)
    fmt = inspection.detected_format

    if fmt.value in ("png", "jpeg"):
        from PIL import Image

        with Image.open(path) as img:
            img.load()
            if img.mode != "RGB":
                rgb_img = img.convert("RGB")
                return np.array(rgb_img, dtype=np.uint8)
            return np.array(img, dtype=np.uint8)

    if fmt.value == "tiff":
        try:
            import rasterio

            with rasterio.open(path) as ds:
                bands = ds.count
                if bands >= 3:
                    data = ds.read((1, 2, 3))
                    return np.transpose(data, (1, 2, 0)).astype(np.uint8)
                elif bands == 1:
                    gray = ds.read(1)
                    return np.stack([gray, gray, gray], axis=-1).astype(np.uint8)
        except Exception:
            pass
        from PIL import Image

        with Image.open(path) as img:
            img.load()
            rgb_img = img.convert("RGB")
            return np.array(rgb_img, dtype=np.uint8)

    raise InvalidInputError(
        f"Unsupported format for RGB loading: {fmt.value} ({inspection.handle.display_name})"
    )


@dataclass(frozen=True)
class SolarIntegrationResult:
    """Result of one solar-shadow integration pass over an image.

    ``constraints`` carries the accepted height cues; ``skipped_count``
    records how many regions were detected but skipped (direction
    contradiction, zero-length shadow, etc.).  ``refused_reason`` is
    non-None only when the integration could not run at all (no sun angles,
    no numpy, etc.).
    """

    constraints: tuple  # tuple[ShadowHeightConstraint, ...]
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
        an independent GSD measurement; ``None`` uses the transform.

    Returns
    -------
    SolarIntegrationResult
        Always returns a result; ``refused_reason`` is set when no
        angles or GSD are available and no constraints can be produced.
    """
    if not isinstance(inspection, InputInspection):
        raise TypeError(
            f"inspection must be an InputInspection, got {type(inspection).__name__}"
        )

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
    gsd: float | None = gsd_override if gsd_override is not None else gsd_from_inspection(
        inspection
    )
    if gsd is None or not (math.isfinite(gsd) and gsd > 0.0):
        return SolarIntegrationResult(
            constraints=(),
            skipped_count=0,
            detected_count=0,
            refused_reason=(
                "GSD (ground sampling distance) could not be resolved from the "
                "image transform.  Shadow trig requires a metric pixel size; "
                "supply gsd_override for non-georeferenced inputs."
            ),
        )

    # --- shadow detection ---
    import importlib.util

    if importlib.util.find_spec("numpy") is None:
        return SolarIntegrationResult(
            constraints=(),
            skipped_count=0,
            detected_count=0,
            refused_reason="numpy is required for shadow detection but is not installed.",
        )

    regions: list[ShadowRegion] = detect_shadows(rgb_array, min_area_px=min_area_px)

    source_id = inspection.handle.display_name
    source_checksum = inspection.handle.sha256

    constraints = []
    skipped = 0

    for region in regions:
        # Shadow base = region centroid (representative structure foot)
        base = PixelPoint(row=int(round(region.centroid_row)), col=int(round(region.centroid_col)))
        tip = PixelPoint(row=region.tip_row, col=region.tip_col)

        # Shadow length in pixels (Euclidean distance from centroid to tip)
        length_px = math.hypot(tip.row - base.row, tip.col - base.col)
        if length_px <= 0.0:
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
                method=f"otsu-luminance-v1;sun-source={sun_angles.source}",
                quality=region.quality,
            )
        except (ValueError, TypeError):
            skipped += 1
            continue

        try:
            constraint = estimate_height(obs)
        except InvalidInputError:
            # Direction contradiction or non-positive height — skip silently.
            skipped += 1
            continue

        constraints.append(constraint)

    return SolarIntegrationResult(
        constraints=tuple(constraints),
        skipped_count=skipped,
        detected_count=len(regions),
        refused_reason=None,
    )
