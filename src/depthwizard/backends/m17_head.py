"""Inference-only M17 adaptation head runtime (no training code).

Ports ONLY the forward path of the M17 research implementation
(``origin/feat/shravan-m17-structural-adapt``,
``src/depthwizard/adapt/{features,head}.py``): frozen DA-V2-Small feature
tap (``depth_head.scratch.output_conv1`` input, 64ch) + the 23,201-parameter
height head (conv3x3 64->32 + BN + ReLU, conv3x3 32->16 + BN + ReLU,
conv1x1 16->1, bilinear upsample) + frozen M10 z-score inverse.

Deliberately NOT ported: loss functions, target scaling, optimizer,
training loop, seeds, augmentation, manifests. Training stays in the
research branches; this module can only run frozen weights.

Output: nDSM-scale meters (H, W) float64 numpy, source grid.
"""

from __future__ import annotations

from typing import Any

#: Frozen M10 z-score statistics for head I/O (part of the frozen
#: M17 candidate definition — never recomputed here).
M10_ZMU = 8.037330237035235
M10_ZSIGMA = 10.304011604437477

#: Read-only hook target inside the official DA-V2 module (never modified).
FEATURE_TAP = "depth_head.scratch.output_conv1"
FEATURE_CHANNELS = 64

#: Exact trainable parameter count of the M17 head (asserted in tests).
HEAD_PARAM_COUNT = 23201


def _require_torch() -> Any:
    try:
        import torch  # type: ignore
    except Exception as e:
        raise RuntimeError(f"torch is required for M17 head inference: {e}") from e
    return torch


def build_head() -> Any:
    """Build the M17 head architecture (weights always loaded from checkpoint)."""
    _require_torch()
    import torch.nn as nn  # type: ignore

    return nn.Sequential(
        nn.Conv2d(64, 32, kernel_size=3, padding=1),
        nn.BatchNorm2d(32),
        nn.ReLU(inplace=True),
        nn.Conv2d(32, 16, kernel_size=3, padding=1),
        nn.BatchNorm2d(16),
        nn.ReLU(inplace=True),
        nn.Conv2d(16, 1, kernel_size=1),
    )


def count_head_parameters(head: Any) -> int:
    """Total parameters (must equal HEAD_PARAM_COUNT for the M17 architecture)."""
    return sum(int(p.numel()) for p in head.parameters())


def freeze_module(module: Any) -> None:
    """Eval mode + requires_grad False, in place (inference only)."""
    _require_torch()
    module.eval()
    for p in module.parameters():
        p.requires_grad_(False)


def _resolve_tap(module: Any, tap: str = FEATURE_TAP) -> Any:
    node = module
    for part in tap.split("."):
        if not hasattr(node, part):
            raise AttributeError(f"Feature tap '{tap}' failed at '{part}'")
        node = getattr(node, part)
    return node


def preprocess_rgb(rgb_uint8: Any, input_size: int = 518) -> Any:
    """Official-equivalent backbone input: RGB/255 -> keep-aspect resize to
    multiples of 14 (INTER_CUBIC) -> ImageNet normalize -> CHW float32."""
    import numpy as np  # type: ignore

    torch = _require_torch()
    try:
        import cv2  # type: ignore
    except Exception as e:
        raise RuntimeError(f"opencv-python required for backbone preprocessing: {e}") from e
    arr = np.asarray(rgb_uint8)
    if arr.ndim != 3 or arr.shape[2] != 3 or arr.dtype != np.uint8:
        raise ValueError(f"Expected HWC uint8 RGB, got shape {arr.shape} dtype {arr.dtype}")
    h, w = int(arr.shape[0]), int(arr.shape[1])
    scale = max(input_size / h, input_size / w)
    nh, nw = max(14, int(round(h * scale / 14) * 14)), max(14, int(round(w * scale / 14) * 14))
    img = cv2.resize(
        (arr.astype(np.float32) / 255.0)[:, :, ::-1],
        (nw, nh),
        interpolation=cv2.INTER_CUBIC,
    )
    mean = np.array([0.485, 0.456, 0.406], np.float32)
    std = np.array([0.229, 0.224, 0.225], np.float32)
    img = (img - mean) / std
    return torch.from_numpy(img.transpose(2, 0, 1).astype(np.float32)).unsqueeze(0)


def capture_features(backbone_module: Any, rgb_uint8: Any, input_size: int = 518) -> Any:
    """Run frozen backbone, capture tap INPUT tensor (B,64,h,w). No grad."""
    torch = _require_torch()
    backbone_module.eval()
    target = _resolve_tap(backbone_module)
    captured: dict[str, Any] = {}

    def _hook(_mod: Any, args: Any, _out: Any) -> None:
        captured["feat"] = args[0].detach()

    handle = target.register_forward_hook(_hook)
    try:
        with torch.no_grad():
            tensor = preprocess_rgb(rgb_uint8, input_size)
            try:
                tensor = tensor.to(next(backbone_module.parameters()).device)
            except StopIteration:
                pass
            backbone_module(tensor)
    finally:
        handle.remove()
    if "feat" not in captured:
        raise RuntimeError(f"Feature tap '{FEATURE_TAP}' captured nothing")
    feat = captured["feat"]
    if feat.ndim != 4 or int(feat.shape[1]) != FEATURE_CHANNELS:
        raise ValueError(f"Expected 4D 64ch feature map, got {tuple(feat.shape)}")
    return feat


def predict_meters(
    backbone_module: Any,
    head_module: Any,
    rgb_uint8: Any,
    out_hw: tuple[int, int],
    mu: float = M10_ZMU,
    sigma: float = M10_ZSIGMA,
    input_size: int = 518,
) -> Any:
    """RGB uint8 HWC -> nDSM-scale meters (H, W) float64 numpy. No grad."""
    import numpy as np  # type: ignore

    torch = _require_torch()
    import torch.nn.functional as F  # type: ignore

    backbone_module.eval()
    head_module.eval()
    with torch.no_grad():
        feats = capture_features(backbone_module, rgb_uint8, input_size)
        try:
            feats = feats.to(next(head_module.parameters()).device)
        except StopIteration:
            pass
        z = head_module(feats)
        z = F.interpolate(
            z, size=(int(out_hw[0]), int(out_hw[1])), mode="bilinear", align_corners=True
        )
    meters = np.asarray((z.squeeze(0).squeeze(0).detach().cpu()), dtype=np.float64)
    meters = meters * float(sigma) + float(mu)
    return meters.reshape(int(out_hw[0]), int(out_hw[1]))
