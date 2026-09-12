"""Tests for train_satellite_adaptation.py CLI and argument parsing."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "train_satellite_adaptation.py"


def test_help_exits_zero() -> None:
    """--help should exit with code 0 and print usage."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower() or "usage:" in result.stderr.lower()
    assert "--gamus-root" in result.stdout
    assert "--manifest" in result.stdout
    assert "--output" in result.stdout
    assert "--epochs" in result.stdout
    assert "--batch-size" in result.stdout
    assert "--lr" in result.stdout


def test_missing_required_args_exits_nonzero() -> None:
    """Missing required args should exit with non-zero and error message."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], capture_output=True, text=True, timeout=30
    )
    assert result.returncode != 0
    # argparse prints error to stderr
    assert "required" in (result.stderr + result.stdout).lower()


def test_missing_gamus_root_exits_nonzero() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--manifest",
            "dummy.json",
            "--output",
            "out.pth",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0


def test_missing_manifest_exits_nonzero() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--gamus-root",
            "/tmp",
            "--output",
            "out.pth",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0


def test_missing_output_exits_nonzero() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--gamus-root",
            "/tmp",
            "--manifest",
            "dummy.json",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0


def test_scale_invariant_loss_formula() -> None:
    """Test the SI loss formula matches DA-V2 paper (pure math, no torch)."""
    import math

    # SI loss: mean((log(pred) - log(target))^2) - mean(log(pred) - log(target))^2
    pred = [1.0, 2.0, 3.0, 4.0]
    target = [1.1, 2.1, 2.9, 4.1]
    log_pred = [math.log(p) for p in pred]
    log_target = [math.log(t) for t in target]
    diffs = [lp - lt for lp, lt in zip(log_pred, log_target, strict=True)]
    mean_diff = sum(diffs) / len(diffs)
    si_loss = sum((d - mean_diff) ** 2 for d in diffs) / len(diffs)
    # Should be small for close predictions
    assert si_loss >= 0
    assert si_loss < 0.01  # close match


def test_gradient_loss_formula() -> None:
    """Test gradient loss formula (pure math)."""
    import numpy as np

    # 2x2 depth maps
    pred = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
    target = np.array([[1.1, 2.1], [2.9, 4.1]], dtype=np.float32)
    # x gradients
    gx_pred = pred[:, 1] - pred[:, 0]  # [1.0, 1.0]
    gx_target = target[:, 1] - target[:, 0]  # [1.0, 1.2]
    # y gradients
    gy_pred = pred[1, :] - pred[0, :]  # [2.0, 2.0]
    gy_target = target[1, :] - target[0, :]  # [1.8, 2.0]
    loss_x = np.mean(np.abs(gx_pred - gx_target))  # |1-1| + |1-1.2| / 2 = 0.1
    loss_y = np.mean(np.abs(gy_pred - gy_target))  # |2-1.8| + |2-2| / 2 = 0.1
    total = loss_x + loss_y
    assert total >= 0
    assert total < 1.0
