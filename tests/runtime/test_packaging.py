"""Runtime packaging contract: discovery, checksum, availability, offline.

Covers the ``depthwizard.runtime`` diagnostics and the service-script
registry boundary. No model inference, no network, no downloads.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from depthwizard.runtime import diagnostics as diag
from depthwizard.runtime.diagnostics import (
    CHECKPOINT_SHA256,
    resolve_checkpoint,
    sha256_file,
    verify_checkpoint,
)


def _write(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


# ---------------------------------------------------------------------------
# Checkpoint discovery order
# ---------------------------------------------------------------------------


def test_explicit_path_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An explicit argument beats every environment default."""
    target = _write(tmp_path / "a.pth", b"weights-a")
    other = _write(tmp_path / "b.pth", b"weights-b")
    monkeypatch.setenv("DW_DAV2_CKPT", str(other))
    found, location = resolve_checkpoint(explicit=target)
    assert found == target
    assert location == "explicit"


def test_env_path_used_when_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """DW_DAV2_CKPT resolves when the file exists."""
    target = _write(tmp_path / "ckpt.pth", b"weights")
    monkeypatch.setenv("DW_DAV2_CKPT", str(target))
    monkeypatch.delenv("DEPTHWIZARD_DATA", raising=False)
    found, location = resolve_checkpoint()
    assert found == target
    assert location == "env"


def test_data_dir_used_for_packaged_layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Packaged data dir is consulted when no env override exists."""
    nested = tmp_path / "data" / "checkpoints"
    nested.mkdir(parents=True)
    target = _write(nested / "depth_anything_v2_vits.pth", b"weights")
    monkeypatch.delenv("DW_DAV2_CKPT", raising=False)
    monkeypatch.setenv("DEPTHWIZARD_DATA", str(tmp_path / "data"))
    found, location = resolve_checkpoint()
    assert found == target
    assert location == "data-dir"


def test_missing_everywhere_reports_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No checkpoint anywhere resolves to absent (never fabricated)."""
    monkeypatch.setenv("DW_DAV2_CKPT", str(tmp_path / "missing.pth"))
    monkeypatch.setenv("DEPTHWIZARD_DATA", str(tmp_path / "empty"))
    found, location = resolve_checkpoint()
    assert found is None
    assert location == "absent"


# ---------------------------------------------------------------------------
# Checksum acceptance / rejection
# ---------------------------------------------------------------------------


def test_correct_sha256_accepted(tmp_path: Path) -> None:
    """A file matching its expected hash verifies."""
    target = _write(tmp_path / "ok.bin", b"depthwizard-packaging-probe")
    expected = hashlib.sha256(b"depthwizard-packaging-probe").hexdigest()
    assert sha256_file(target) == expected
    status = verify_checkpoint(target, expected)
    assert status.ok
    assert status.code == "OK"


def test_wrong_sha256_rejected(tmp_path: Path) -> None:
    """A single flipped byte fails verification (no partial trust)."""
    target = _write(tmp_path / "tampered.bin", b"depthwizard-packaging-probe!")
    expected = hashlib.sha256(b"depthwizard-packaging-probe").hexdigest()
    status = verify_checkpoint(target, expected)
    assert not status.ok
    assert status.code == "CHECKPOINT_HASH_MISMATCH"
    assert status.extra["actual"] != expected


def test_missing_file_rejected(tmp_path: Path) -> None:
    """A missing path is a missing checkpoint, not an empty hash."""
    status = verify_checkpoint(tmp_path / "gone.pth", CHECKPOINT_SHA256)
    assert not status.ok
    assert status.code == "CHECKPOINT_MISSING"


# ---------------------------------------------------------------------------
# Dependency availability (discovery only, never imports torch)
# ---------------------------------------------------------------------------


def test_present_module_discoverable() -> None:
    """Discovery reports genuinely installed modules."""
    assert diag.module_available("json") is True
    assert diag.module_available("definitely-not-a-module-xyz") is False


def test_dav2_unavailable_without_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    """The availability snapshot degrades factually when ML deps vanish."""
    real_find_spec = importlib.util.find_spec

    def fake_find_spec(name: str, *args: object, **kwargs: object) -> object:
        if name in ("torch", "torchvision", "cv2", "depth_anything_v2"):
            return None
        return real_find_spec(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)
    report = diag.availability_report()
    assert report["dav2_ready"] is False
    assert report["dav2_source_present"] is False
    # Core modules are untouched by the ML outage.
    core = report["core_modules"]
    assert isinstance(core, dict)
    assert core.get("numpy") is True


# ---------------------------------------------------------------------------
# Service registry + startup failure structure
# ---------------------------------------------------------------------------


def _load_service_script() -> object:
    """Import scripts/depthwiz_service.py without executing it."""
    import types

    path = Path("scripts/depthwiz_service.py").resolve()
    module = types.ModuleType("depthwiz_service_under_test")
    module.__dict__["__file__"] = str(path)
    code = compile(path.read_bytes(), str(path), "exec")
    exec(code, module.__dict__)
    return module


def test_registry_advertises_only_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without assets the registry is synthetic-only (factual)."""
    monkeypatch.setenv("DW_DAV2_CKPT", str(tmp_path / "missing.pth"))
    monkeypatch.setenv("DEPTHWIZARD_DATA", str(tmp_path / "empty"))
    monkeypatch.setenv("PYTHONPATH", "src")
    service = _load_service_script()
    assert isinstance(service, object)
    backends = service.build_backends()  # type: ignore[attr-defined]
    assert sorted(backends) == ["synthetic-depth"]


def test_unknown_backend_is_structured_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A real-backend request without assets is a wire error, not success."""
    monkeypatch.setenv("DW_DAV2_CKPT", str(tmp_path / "missing.pth"))
    monkeypatch.setenv("DEPTHWIZARD_DATA", str(tmp_path / "empty"))
    monkeypatch.setenv("PYTHONPATH", "src")
    service = _load_service_script()
    payload = {
        "contract_version": "1",
        "input_path": "tile.png",
        "target_semantics": "absolute_elevation_dsm",
        "backend": "depth-anything-v2-small",
        "build_mesh": False,
    }
    result = service.handle_request(payload)  # type: ignore[attr-defined]
    assert "wire_error" in result
    assert "unknown backend" in result["wire_error"]
    assert "synthetic" not in result["wire_error"].lower()


# ---------------------------------------------------------------------------
# Offline: the runtime path makes no network calls by construction
# ---------------------------------------------------------------------------


def test_no_network_imports_in_runtime() -> None:
    """No socket/HTTP/hub imports anywhere in the shipped engine.

    Provisioning (``runtime/provision.py``) is the single exception: it
    may fetch the fixed checkpoint identity, and only that identity.
    """
    banned = (
        "import socket",
        "import requests",
        "hf_hub_download",
        "snapshot_download",
        "from_pretrained",
        "torch.hub",
    )
    offenders: list[str] = []
    for path in Path("src/depthwizard").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for marker in banned:
            if marker in text:
                offenders.append(f"{path}:{marker}")
        if "urllib" in text and path.name != "provision.py":
            offenders.append(f"{path}:urllib")
    assert offenders == []


def test_provision_contacts_only_fixed_identities() -> None:
    """The only URL literals in provisioning are the fixed identities."""
    import re

    text = Path("src/depthwizard/runtime/provision.py").read_text(encoding="utf-8")
    literals = [
        url for url in re.findall(r'"(https://[^"]+)"', text) if re.search(r"https://[^/]+/\S", url)
    ]
    assert literals, "expected fixed identities in provisioning"
    for url in literals:
        assert (
            "DepthAnything/Depth-Anything-V2" in url
            or "depth-anything/Depth-Anything-V2-Small" in url
        ), f"unexpected URL in provisioning: {url}"


# ---------------------------------------------------------------------------
# runtime_check CLI: healthy core, structured failures, no downloads
# ---------------------------------------------------------------------------


def test_runtime_check_reports_core_healthy() -> None:
    """The self-check passes on a provisioned dev machine."""
    proc = subprocess.run(
        [sys.executable, "scripts/runtime_check.py"],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["healthy"] is True
    assert report["failures"] == []
    assert report["core_ready"] is True


def test_runtime_check_rejects_bad_checkpoint(tmp_path: Path) -> None:
    """An explicit checkpoint with a wrong hash fails the check."""
    target = _write(tmp_path / "bad.pth", b"not-the-real-weights")
    proc = subprocess.run(
        [sys.executable, "scripts/runtime_check.py", "--checkpoint", str(target)],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
        timeout=120,
    )
    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["healthy"] is False
    assert any("CHECKPOINT_HASH_MISMATCH" in failure for failure in report["failures"])


def test_runtime_check_require_dav2_without_assets(tmp_path: Path) -> None:
    """--require-dav2 fails loudly when assets are absent (no fallback)."""
    env = dict(os.environ)
    env["DW_DAV2_CKPT"] = str(tmp_path / "missing.pth")
    env["DEPTHWIZARD_DATA"] = str(tmp_path / "empty")
    env["PYTHONPATH"] = "src"
    proc = subprocess.run(
        [sys.executable, "scripts/runtime_check.py", "--require-dav2"],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
        env=env,
        timeout=120,
    )
    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["healthy"] is False
