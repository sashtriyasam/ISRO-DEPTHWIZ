"""Tests for packaged checkpoint discovery (fixture-based, no weights/torch)."""

from depthwizard.backends.depth_anything_v2 import CHECKPOINT_FILE
from depthwizard.runtime import diagnostics as diag


def _make_tree(root, with_file: bool):
    pkg = root / "src" / "depthwizard"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    if with_file:
        ckpt_dir = root / "checkpoints"
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        (ckpt_dir / CHECKPOINT_FILE).write_bytes(b"fake-bytes")


def test_sibling_checkpoint_found_in_packaged_layout(tmp_path):
    _make_tree(tmp_path, with_file=True)
    found = diag.sibling_checkpoint(tmp_path / "src" / "depthwizard")
    assert found is not None
    assert found.name == CHECKPOINT_FILE


def test_sibling_checkpoint_absent_returns_none(tmp_path):
    _make_tree(tmp_path, with_file=False)
    assert diag.sibling_checkpoint(tmp_path / "src" / "depthwizard") is None


def test_resolve_checkpoint_prefers_data_dir(tmp_path, monkeypatch):
    data = tmp_path / "data"
    (data / "checkpoints").mkdir(parents=True)
    (data / "checkpoints" / CHECKPOINT_FILE).write_bytes(b"fake-bytes")
    monkeypatch.setenv("DEPTHWIZARD_DATA", str(data))
    monkeypatch.delenv("DW_DAV2_CKPT", raising=False)
    path, location = diag.resolve_checkpoint()
    assert location == "data-dir"
    assert path is not None and path.name == CHECKPOINT_FILE


def test_resolve_checkpoint_explicit_missing_reports_absent(tmp_path):
    path, location = diag.resolve_checkpoint(explicit=tmp_path / "nope.pth")
    assert path is None
    assert location == "absent"


def test_verify_checkpoint_rejects_wrong_hash(tmp_path):
    bad = tmp_path / "bad.pth"
    bad.write_bytes(b"not-the-checkpoint")
    status = diag.verify_checkpoint(bad)
    assert status.ok is False
    assert status.code == "CHECKPOINT_HASH_MISMATCH"


def test_module_available_probes_without_importing():
    assert diag.module_available("json") is True
    assert diag.module_available("depthwizard.no_such_module_xyz") is False
