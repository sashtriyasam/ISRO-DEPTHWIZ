"""
Adapted research model: frozen DA-V2-Small backbone + trainable HeightHead.

Output semantics: metric GAMUS nDSM/AGL prediction (research evaluation only).
This is a SEPARATE type from `DepthAnythingV2Backend` (relative depth) — the
frozen backend's semantics are never modified. Not wired into any production
pipeline; no calibration engine involvement.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from depthwizard.adapt.features import (
    FEATURE_CHANNELS,
    FEATURE_TAP,
    capture_features,
    extract_backbone_features,
    freeze_backbone,
    preprocess_rgb,
)
from depthwizard.adapt.head import HeightHead, build_head, count_parameters, forward_head
from depthwizard.adapt.loss import TargetScale

OUTPUT_SEMANTICS = "gamus-ndsm-agl-metric (research evaluation only; not calibrated elevation)"


class AdaptedDepthModel:
    """Frozen backbone + lightweight head. Backbone params require_grad False forever."""

    def __init__(
        self,
        backbone: Any,
        head: Optional[Any] = None,
        input_size: int = 518,
        target_scale: Optional[TargetScale] = None,
    ) -> None:
        self.backbone = backbone
        if head is None:
            raise ValueError("AdaptedDepthModel requires an explicit head (use from_backend or pass build_head())")
        self.head_holder = head if isinstance(head, HeightHead) else HeightHead(head)
        self.head = self.head_holder.module
        self.input_size = int(input_size)
        self.feature_tap = FEATURE_TAP
        self.output_semantics = OUTPUT_SEMANTICS
        self.target_scale = target_scale or TargetScale(mode="raw")
        freeze_report = freeze_backbone(self.backbone)
        self.backbone_params = freeze_report
        if self.head is not None:
            for p in self.head.parameters():
                p.requires_grad_(True)

    @classmethod
    def from_backend(cls, backend: Any, input_size: int = 518, seed: int = 0) -> "AdaptedDepthModel":
        """Build from a loaded DepthAnythingV2Backend (backbone frozen in place)."""
        torch = _require_torch()
        torch.manual_seed(seed)
        head = build_head(FEATURE_CHANNELS)
        return cls(backend.torch_module, head=head, input_size=input_size)

    def parameter_report(self) -> dict[str, int]:
        head_counts = count_parameters(self.head) if self.head is not None else {"total": 0, "trainable": 0, "frozen": 0}
        return {
            "backbone_total": self.backbone_params["total"],
            "backbone_trainable": 0,
            "head_total": head_counts["total"],
            "head_trainable": head_counts["trainable"],
            "total": self.backbone_params["total"] + head_counts["total"],
            "trainable": head_counts["trainable"],
        }

    def assert_frozen(self) -> None:
        bad = [n for n, p in self.backbone.named_parameters() if p.requires_grad]
        if bad:
            raise AssertionError(f"Backbone UNFROZEN params: {bad[:5]} (M4 prohibits fine-tuning)")

    def forward_features(self, rgb_uint8: Any) -> Any:
        self.assert_frozen()
        return extract_backbone_features(self.backbone, rgb_uint8, self.input_size)

    def forward(self, rgb_uint8: Any, out_hw: tuple[int, int] = (1024, 1024)) -> Any:
        """RGB uint8 HWC -> (1,H,W) prediction tensor in model's output space (grad enabled for head)."""
        torch = _require_torch()
        self.assert_frozen()
        self.backbone.eval()
        with torch.no_grad():
            feats = capture_features(self.backbone, preprocess_rgb(rgb_uint8, self.input_size))
        return forward_head(self.head_holder, feats, out_hw).squeeze(0)

    def predict_height(self, rgb_uint8: Any, out_hw: tuple[int, int] = (1024, 1024)) -> Any:
        """No-grad inference -> numpy (H,W) meters. Applies inverse target normalization if configured."""
        torch = _require_torch()
        import numpy as np  # type: ignore

        self.backbone.eval()
        self.head.eval()
        with torch.no_grad():
            out = self.forward(rgb_uint8, out_hw)
        # Apply inverse target normalization to get meters
        return np.asarray(self.target_scale.inverse(out.detach()).cpu()).reshape(out_hw[0], out_hw[1])

    def save_head(self, path: Path | str, extra: Optional[dict] = None) -> Path:
        """Persist head state + config (backbone weights referenced, never copied)."""
        torch = _require_torch()
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "head_state": self.head.state_dict(),
            "input_size": self.input_size,
            "feature_tap": self.feature_tap,
            "output_semantics": self.output_semantics,
            "extra": extra or {},
        }
        torch.save(payload, str(out))
        return out

    def load_head(self, path: Path | str) -> dict:
        torch = _require_torch()
        payload = torch.load(str(path), map_location="cpu", weights_only=False)
        self.head.load_state_dict(payload["head_state"])
        return payload


def _require_torch() -> Any:
    try:
        import torch  # type: ignore
    except Exception as e:
        raise RuntimeError(f"torch is required for M4/M7 adaptation (pip install -e .[dav2]): {e}") from e
    return torch