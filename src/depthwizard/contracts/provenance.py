"""Product provenance: who made this product, from what, and how.

Every field is optional. Genuinely unavailable information is ``None`` —
never fabricated. A DEM/GCP-supported product must record its calibration
reference here; a plain PNG/JPG carries no CRS and no metre claim.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductProvenance(BaseModel):
    """Provenance / metadata that can eventually describe any product."""

    model_config = ConfigDict(frozen=True)

    source_input_id: str | None = None
    input_checksum: str | None = Field(
        default=None, description="Checksum of the source input, when known."
    )
    model_name: str | None = None
    model_version: str | None = None
    checkpoint_id: str | None = None
    calibration_method: str | None = Field(
        default=None, description="How relative output was scaled, e.g. 'dem_affine'."
    )
    calibration_reference: str | None = Field(
        default=None, description="Reference used for calibration (DEM id, GCP set id)."
    )
    calibration_params: tuple[float, ...] | None = Field(
        default=None, description="Calibration parameters (e.g. scale, offset), if any."
    )
    software_version: str | None = None
    code_commit: str | None = None
    generated_at: datetime | None = None
    units: str | None = Field(
        default=None,
        description="Numerical units of the product values, e.g. 'meters'. "
        "None for unitless/relative products.",
    )
    semantic_meaning: str | None = Field(
        default=None,
        description="Human-readable meaning of the values, e.g. 'relative_depth'.",
    )
