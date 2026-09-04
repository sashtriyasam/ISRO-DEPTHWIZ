"""
DepthBackend / DepthResult contracts.

`DepthResult` carries a scale-ambiguous monocular prediction plus the metadata
needed to interpret it honestly:

    scale_semantics = "relative", is_metric = False  (frozen DA-V2 baseline)

Rule A/B enforcement: there is intentionally NO method converting the
prediction to meters. `metric_height()` exists only to raise an actionable
error directing callers to Shivam's calibration subsystem (not implemented
here). Any future metric backend must set `is_metric=True` explicitly with
calibration provenance — the default constructor refuses `is_metric=True`
without it.
"""

from __future__ import annotations

import abc
import dataclasses
from typing import Any, Optional


@dataclasses.dataclass
class DepthResult:
    """Single-image depth inference result (relative unless proven metric)."""

    prediction: Any  # numpy ndarray, shape (H, W), float — source-image size
    scale_semantics: str = "relative"  # "relative" | "metric"
    is_metric: bool = False
    model_name: str = "unknown"
    checkpoint_id: Optional[str] = None
    checkpoint_sha: Optional[str] = None
    upstream_revision: Optional[str] = None
    device: str = "cpu"
    input_size: Optional[int] = None
    input_shape: Optional[tuple[int, int]] = None  # (H, W) of source image
    preprocessing: Optional[dict[str, Any]] = None
    valid_mask: Optional[Any] = None  # bool ndarray (H, W) or None (= all finite)
    confidence: Optional[Any] = None  # reserved; DA-V2 provides none -> None
    inference_time_s: Optional[float] = None
    calibration_provenance: Optional[str] = None  # required when is_metric=True

    def __post_init__(self) -> None:
        import numpy as np  # type: ignore

        self.prediction = np.asarray(self.prediction)
        if self.prediction.ndim != 2:
            raise ValueError(f"DepthResult.prediction must be 2D (H, W), got {self.prediction.shape}")
        if self.scale_semantics not in ("relative", "metric"):
            raise ValueError(f"scale_semantics must be 'relative' or 'metric', got {self.scale_semantics!r}")
        if self.is_metric or self.scale_semantics == "metric":
            if not (self.is_metric and self.scale_semantics == "metric" and self.calibration_provenance):
                raise ValueError(
                    "Metric depth requires is_metric=True, scale_semantics='metric' AND "
                    "calibration_provenance set. Relative output must not be marked metric. "
                    "(Rules A/B — see Shivam's calibration subsystem for metric conversion.)"
                )
        if self.valid_mask is not None:
            self.valid_mask = np.asarray(self.valid_mask, dtype=bool)
            if self.valid_mask.shape != self.prediction.shape:
                raise ValueError("valid_mask shape must match prediction shape")

    @property
    def shape(self) -> tuple[int, int]:
        return (int(self.prediction.shape[0]), int(self.prediction.shape[1]))

    @property
    def finite_coverage(self) -> float:
        import numpy as np  # type: ignore

        return float(np.isfinite(self.prediction).mean())

    def metric_height(self) -> Any:
        """Always raises: relative output cannot become metric height here."""
        raise NotImplementedError(
            "DepthResult holds scale-ambiguous relative depth (Rules A/B). "
            "Metric conversion is Shivam's calibration subsystem concern, not M3 inference."
        )

    def to_dict(self, include_arrays: bool = False) -> dict[str, Any]:
        import numpy as np  # type: ignore

        pred = np.asarray(self.prediction, dtype=np.float64)
        finite = np.isfinite(pred)
        d: dict[str, Any] = {
            "scale_semantics": self.scale_semantics,
            "is_metric": self.is_metric,
            "model_name": self.model_name,
            "checkpoint_id": self.checkpoint_id,
            "checkpoint_sha": self.checkpoint_sha,
            "upstream_revision": self.upstream_revision,
            "device": self.device,
            "input_size": self.input_size,
            "input_shape": list(self.input_shape) if self.input_shape else None,
            "preprocessing": self.preprocessing,
            "shape": [int(pred.shape[0]), int(pred.shape[1])],
            "finite_coverage": float(finite.mean()),
            "pred_min": float(pred[finite].min()) if finite.any() else None,
            "pred_max": float(pred[finite].max()) if finite.any() else None,
            "pred_mean": float(pred[finite].mean()) if finite.any() else None,
            "pred_std": float(pred[finite].std()) if finite.any() else None,
            "inference_time_s": self.inference_time_s,
            "calibration_provenance": self.calibration_provenance,
        }
        if include_arrays:
            d["prediction"] = pred.tolist()
        return d


class DepthBackend(abc.ABC):
    """Abstract frozen-inference backend. Implementations must not train."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        ...

    @property
    @abc.abstractmethod
    def is_loaded(self) -> bool:
        ...

    @abc.abstractmethod
    def load(self) -> None:
        """Load weights into memory (idempotent)."""
        ...

    @abc.abstractmethod
    def infer(self, image_rgb: Any) -> DepthResult:
        """Run frozen inference on an HWC uint8 RGB image -> DepthResult.

        Output is source-image sized. Implementations must document scale
        semantics; relative output must carry is_metric=False.
        """
        ...

    def close(self) -> None:
        """Release resources (default: no-op)."""
        return None

    def config_dict(self) -> dict[str, Any]:
        return {"backend": self.name}
