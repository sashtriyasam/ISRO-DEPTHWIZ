"""Opt-in real-model tests: run only when checkpoint + package are available.

Never downloads weights in CI. Skips cleanly otherwise. The 3-tile bring-up
dataset (M2, git-ignored) is used when present; else the test still skips.
"""

import os
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

from depthwizard.data.config import GamusConfig  # noqa: E402

try:
    import depth_anything_v2  # type: ignore  # noqa: F401

    _HAS_PACKAGE = True
except Exception:
    _HAS_PACKAGE = False


def _ckpt() -> Path | None:
    env = os.environ.get("DW_DAV2_CKPT")
    cands = [Path(env)] if env else []
    cands.append(Path("checkpoints/depth_anything_v2_vits.pth"))
    for c in cands:
        if c.is_file():
            return c
    return None


_CKPT = _ckpt()
needs_real = pytest.mark.skipif(
    _CKPT is None or not _HAS_PACKAGE, reason="real DA-V2 weights/package unavailable"
)


def _root() -> Path | None:
    for c in ([Path(os.environ["GAMUS_ROOT"])] if os.environ.get("GAMUS_ROOT") else []):
        if (c / "images").exists():
            return c
    r = GamusConfig().resolve_root()
    return r if (r / "images").exists() else None


@needs_real
def test_real_backend_infer_source_sized():
    from depthwizard.depth.depth_anything_v2 import DepthAnythingV2Backend

    be = DepthAnythingV2Backend(checkpoint=_CKPT, device="cpu")
    be.load()
    assert be.is_loaded
    rng = np.random.default_rng(0)
    res = be.infer(rng.integers(0, 256, (64, 48, 3)).astype(np.uint8))
    assert res.shape == (64, 48) and res.scale_semantics == "relative" and not res.is_metric


@needs_real
def test_real_experiment_single_tile_smoke(tmp_path):
    root = _root()
    if root is None:
        pytest.skip("no local GAMUS root")
    from depthwizard.data.manifest import discover_records
    from depthwizard.depth.depth_anything_v2 import DepthAnythingV2Backend
    from depthwizard.experiments.depth_anything_v2 import run_experiment

    recs = discover_records(root, splits=["train"])[:1]
    assert recs, "expected at least one train tile"
    import json

    mp = tmp_path / "m.json"
    mp.write_text(json.dumps({"version": "1.0", "source": "gamus", "root": root.as_posix(), "records": [r.to_dict() for r in recs]}), encoding="utf-8")
    be = DepthAnythingV2Backend(checkpoint=_CKPT, device="cpu")
    res = run_experiment(manifest=mp, output=tmp_path / "exp", split="train", root=root, backend=be)
    assert res["n_samples"] == 1 and res["per_sample"][0]["pred_shape"] == [1024, 1024]
