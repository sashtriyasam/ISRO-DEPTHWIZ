"""
Frozen feature access for DA-V2-Small (M4 Stage A).

Feature source (audited against upstream `depth_anything_v2/dpt.py` @ a561b84):
    input tensor to `depth_head.scratch.output_conv1`
    (i.e. `path_1`, the highest-resolution fused DPT representation before the
    final output convolutions).

Why this representation:
    - Spatially structured dense map (not a CLS token): required for
      per-pixel height regression.
    - Deepest fused scale (`refinenet1` output): combines all four DPT scales,
      so the head sees both detail and context without a feature pyramid of
      its own.
    - 64 channels; measured (1,64,296,296) for 1024px tiles at the 518 working
      resolution: small enough for a genuinely lightweight head (~23k params),
      rich enough to test the hypothesis.
    - Reached via a read-only forward hook: no upstream modification, no
      change to the frozen `infer` path.

Backbone stays frozen: `freeze_backbone` sets eval mode + requires_grad False
for every parameter (asserted in unit tests). Gradients are disabled during
feature capture (`torch.no_grad`).
"""

from __future__ import annotations

from typing import Any

# Read-only hook target inside the official module (never modified).
FEATURE_TAP = "depth_head.scratch.output_conv1"
FEATURE_CHANNELS = 64


def _require_torch() -> Any:
    try:
        import torch  # type: ignore
    except Exception as e:
        raise RuntimeError(f"torch is required for M4 adaptation (pip install -e .[dav2]): {e}") from e
    return torch


def resolve_tap(module: Any, tap: str = FEATURE_TAP) -> Any:
    """Resolve dotted submodule path; raises with available children on failure."""
    node = module
    for part in tap.split("."):
        if not hasattr(node, part):
            children = [n for n, _ in node.named_children()] if hasattr(node, "named_children") else []
            raise AttributeError(f"Feature tap '{tap}' failed at '{part}'. Children: {children}")
        node = getattr(node, part)
    return node


def freeze_backbone(module: Any) -> dict[str, int]:
    """Freeze ALL parameters in place; returns {total, frozen, trainable} counts."""
    torch = _require_torch()
    module.eval()
    total = frozen = 0
    for p in module.parameters():
        total += p.numel()
        p.requires_grad_(False)
        frozen += p.numel()
    trainable = sum(p.numel() for p in module.parameters() if p.requires_grad)
    assert trainable == 0, "freeze_backbone must leave zero trainable backbone params"
    torch.manual_seed(0)  # no-op for determinism bookkeeping symmetry; real seed set by trainer
    return {"total": total, "frozen": frozen, "trainable": trainable}


def preprocess_rgb(rgb_uint8: Any, input_size: int = 518) -> Any:
    """Official-equivalent backbone input (audited M3 preprocessing contract).

    BGR conversion is unnecessary here (we start from RGB): BGR2RGB(/255) then
    RGB/255 are identical. Steps: RGB/255 -> keep-aspect lower-bound resize to
    multiples of 14 (INTER_CUBIC) -> ImageNet normalize -> CHW float32 tensor.
    """
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
    # Keep-aspect lower-bound scale so both sides >= input_size, then snap to x14.
    scale = max(input_size / h, input_size / w)
    nh, nw = max(14, int(round(h * scale / 14) * 14)), max(14, int(round(w * scale / 14) * 14))
    img = cv2.resize((arr.astype(np.float32) / 255.0)[:, :, ::-1], (nw, nh), interpolation=cv2.INTER_CUBIC)
    # NOTE: [:, :, ::-1] is a no-op color round-trip kept explicit: official code
    # does BGR2RGB on BGR input; our input is already RGB so values are unchanged.
    mean = np.array([0.485, 0.456, 0.406], np.float32)
    std = np.array([0.229, 0.224, 0.225], np.float32)
    img = (img - mean) / std
    return torch.from_numpy(img.transpose(2, 0, 1).astype(np.float32)).unsqueeze(0)


def capture_features(module: Any, input_tensor: Any, tap: str = FEATURE_TAP) -> Any:
    """Run frozen backbone, capture tap INPUT tensor. No grad, eval enforced."""
    torch = _require_torch()
    module.eval()
    target = resolve_tap(module, tap)
    captured: dict[str, Any] = {}

    def _hook(_mod: Any, args: Any, _out: Any) -> None:
        captured["feat"] = args[0].detach()

    handle = target.register_forward_hook(_hook)
    try:
        with torch.no_grad():
            module(input_tensor)
    finally:
        handle.remove()
    if "feat" not in captured:
        raise RuntimeError(f"Feature tap '{tap}' captured nothing")
    feat = captured["feat"]
    if feat.ndim != 4:
        raise ValueError(f"Expected 4D feature map (B,C,h,w), got {tuple(feat.shape)}")
    return feat


def extract_backbone_features(module: Any, rgb_uint8: Any, input_size: int = 518) -> Any:
    """Convenience: preprocess RGB then capture frozen features (B,C,h,w)."""
    return capture_features(module, preprocess_rgb(rgb_uint8, input_size))
