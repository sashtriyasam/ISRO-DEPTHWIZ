"""
Lightweight height-regression head (M4 Stage A).

Architecture (chosen for the 64ch fused DPT feature map):

    frozen (B,64,h,w)  [~1/4 of 518 working resolution]
      -> Conv3x3(64->32) + BN + ReLU
      -> Conv3x3(32->16) + BN + ReLU
      -> Conv1x1(16->1)            (no final nonlinearity: negatives preserved)
      -> bilinear upsample to (1024,1024)

~23k trainable parameters vs 24.8M frozen. No transformers, no attention, no
U-Net, no pyramid — one controlled factor (the head) on top of frozen features.
"""

from __future__ import annotations

from typing import Any


def _require_torch() -> Any:
    try:
        import torch  # type: ignore
    except Exception as e:
        raise RuntimeError(f"torch is required for M4 adaptation (pip install -e .[dav2]): {e}") from e
    return torch


HEAD_SPEC = {
    "in_channels": 64,
    "blocks": ["conv3x3(64->32)+BN+ReLU", "conv3x3(32->16)+BN+ReLU", "conv1x1(16->1)"],
    "upsample": "bilinear to target HxW (continuous, height-appropriate)",
    "final_nonlinearity": "none (negative heights preserved)",
}


class HeightHead:
    """Thin wrapper holding a torch head module + spec (torch-optional import)."""

    def __init__(self, module: Any) -> None:
        self.module = module

    @property
    def spec(self) -> dict[str, Any]:
        return dict(HEAD_SPEC)


def build_head(in_channels: int = 64) -> HeightHead:
    """Build the lightweight head with Kaiming init (caller seeds torch first)."""
    _require_torch()
    import torch.nn as nn  # type: ignore

    if in_channels != 64:
        raise ValueError(f"M4 head expects 64ch fused features, got {in_channels}")
    module = nn.Sequential(
        nn.Conv2d(64, 32, kernel_size=3, padding=1),
        nn.BatchNorm2d(32),
        nn.ReLU(inplace=True),
        nn.Conv2d(32, 16, kernel_size=3, padding=1),
        nn.BatchNorm2d(16),
        nn.ReLU(inplace=True),
        nn.Conv2d(16, 1, kernel_size=1),
    )
    for m in module.modules():
        if isinstance(m, nn.Conv2d):
            nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
            if m.bias is not None:
                nn.init.zeros_(m.bias)
    return HeightHead(module)


def forward_head(head: HeightHead, features: Any, out_hw: tuple[int, int] = (1024, 1024)) -> Any:
    """features (B,C,h,w) -> (B,1,H,W) meters. Raises on channel mismatch."""
    _require_torch()
    import torch.nn.functional as F  # type: ignore

    if int(features.shape[1]) != 64:
        raise ValueError(f"Head expects 64 input channels, got {int(features.shape[1])}")
    y = head.module(features)
    y = F.interpolate(y, size=(int(out_hw[0]), int(out_hw[1])), mode="bilinear", align_corners=True)
    return y


def count_parameters(module: Any) -> dict[str, int]:
    total = sum(p.numel() for p in module.parameters())
    trainable = sum(p.numel() for p in module.parameters() if p.requires_grad)
    return {"total": total, "trainable": trainable, "frozen": total - trainable}
