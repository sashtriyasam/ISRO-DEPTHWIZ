"""Opt-in real-backbone training test (single step, 1 real tile).

Skips unless the official package + checkpoint + local GAMUS tile exist.
Never downloads anything; CPU only.
"""

import os
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")

from depthwizard.data.config import GamusConfig  # noqa: E402

try:
    import depth_anything_v2  # type: ignore  # noqa: F401

    _HAS_PACKAGE = True
except Exception:
    _HAS_PACKAGE = False


def _ckpt() -> Path | None:
    cands = [Path(os.environ["DW_DAV2_CKPT"])] if os.environ.get("DW_DAV2_CKPT") else []
    cands.append(Path("checkpoints/depth_anything_v2_vits.pth"))
    return next((c for c in cands if c.is_file()), None)


needs_real = pytest.mark.skipif(_ckpt() is None or not _HAS_PACKAGE, reason="real backbone unavailable")


@needs_real
def test_real_single_training_step():
    from depthwizard.adapt.loss import masked_l1
    from depthwizard.adapt.model import AdaptedDepthModel
    from depthwizard.depth.depth_anything_v2 import DepthAnythingV2Backend

    root = GamusConfig().resolve_root()
    img_p = root / "images/train/DC_01_25_RGB.h5"
    h_p = root / "heights/train/DC_01_25_AGL.h5"
    if not img_p.is_file() or not h_p.is_file():
        pytest.skip("real GAMUS tile unavailable")
    import h5py  # type: ignore

    with h5py.File(img_p, "r") as f:
        rgb = f["image"][()]
    with h5py.File(h_p, "r") as f:
        h = f["image"][()].astype(np.float32)
    be = DepthAnythingV2Backend(checkpoint=_ckpt(), device="cpu")
    model = AdaptedDepthModel.from_backend(be, seed=0)
    opt = torch.optim.Adam([p for p in model.head.parameters() if p.requires_grad], lr=1e-3)
    before = [p.detach().clone() for p in model.head.parameters()]
    opt.zero_grad()
    pred = model.forward(rgb, out_hw=(256, 256)).unsqueeze(0)
    tgt = torch.as_tensor(h[::4, ::4], dtype=torch.float32).unsqueeze(0).unsqueeze(0)
    assert pred.shape == tgt.shape
    loss, n = masked_l1(pred, tgt)
    assert n > 0
    loss.backward()
    opt.step()
    changed = any(not torch.equal(a, b) for a, b in zip(before, model.head.parameters()))
    assert changed, "head weights must update on a real training step"
    model.assert_frozen()
