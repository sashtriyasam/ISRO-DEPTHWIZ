"""Gated real-data evaluation (explicit local assets only, never CI).

Runs the canonical CLI on a tiny local manifest when requested:

  DW_EVAL_REAL=1 GAMUS_ROOT=<dir> pytest tests/evaluation/test_real_data.py

Asserts structural properties (counts, units, finiteness, protocol
labels) — never accuracy thresholds, so the test cannot become
tuning-by-accident.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest

_MANIFEST = os.environ.get("DW_EVAL_MANIFEST", "manifests/gamus-tiny-smoke.json")
_GATED = os.environ.get("DW_EVAL_REAL", "0") == "1"
_SKIP = "Real-data evaluation skipped: set DW_EVAL_REAL=1 with local GAMUS assets"


@pytest.mark.skipif(not _GATED, reason=_SKIP)
def test_real_evaluation_structure(tmp_path: Path) -> None:
    """Real CLI run produces a structurally valid run document."""
    output = tmp_path / "run.json"
    env = dict(os.environ)
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/evaluate.py",
            "--dataset",
            "gamus",
            "--manifest",
            _MANIFEST,
            "--split",
            "test",
            "--backend",
            "depth-anything-v2-small",
            "--stride",
            "8",
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
        env=env,
        timeout=1800,
    )
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    run = json.loads(output.read_text(encoding="utf-8"))
    assert run["sample_count"] >= 1
    assert run["valid_pixels"] > 0
    assert run["units"] == "meters"
    assert run["calibration_protocol"] == "control-stride"
    assert run["alignment_protocol"] == "native-pixel"
    for key in ("pooled_mae", "pooled_rmse", "pooled_r_squared"):
        assert math.isfinite(run[key])
    for sample in run["per_sample"]:
        assert sample["metrics"]["coverage_fraction"] > 0
        assert sample["calibration_controls"] > 0
        assert sample["metrics"]["units"] == "meters"
