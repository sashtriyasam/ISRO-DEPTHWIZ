"""
Experiment-ready data interface over the frozen GAMUS contract (M2).

Wraps manifest-driven `GamusRecord` access in a deterministic,
`torch.utils.data.Dataset`-compatible object WITHOUT introducing training,
losses, optimizers, models, or benchmark metrics.

Tensor semantics (documented, raw-preserving):
    image:  float32, shape (3, H, W), range [0, 1]  (HWC uint8 -> CHW / 255).
            No ImageNet normalization here — that belongs to a future model
            transform layer, not to dataset semantics.
    height: float32, shape (1, H, W), meters (GAMUS nDSM/AGL ground truth).
            Never clipped, never redefined as absolute elevation/DSM.
    label:  int64, shape (H, W), values 0..6. The distribution stores labels
            as float32 (verified empirically, M2 probe); they are rounded to
            the nearest integer on load and rejected if non-integer or
            out-of-contract values are present.

Determinism:
    Records are consumed from an explicit manifest (path or list), re-sorted
    by (split order, sample_id) on construction, and indexed positionally.
    The dataset never re-discovers the filesystem and never resamples.
    `transform=None` (default) is the deterministic identity; any callable
    transform is applied as given and must itself be deterministic for
    reproducible experiments — the dataset does not seed it.

torch is an *optional* import: without torch, `__getitem__` returns numpy
arrays with identical shapes/dtypes (int64 label, float32 image/height).
No new required dependency is introduced by this module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from depthwizard.data.manifest import load_manifest
from depthwizard.data.schemas import GAMUS_SPLITS, GAMUS_VALID_LABELS, GamusRecord, canonical_split

EXPERIMENT_TENSOR_SPEC = {
    "image": {"dtype": "float32", "shape": "(3, H, W)", "range": "[0, 1]", "note": "CHW, raw [0,1]; no ImageNet norm"},
    "height": {"dtype": "float32", "shape": "(1, H, W)", "units": "meters", "note": "nDSM/AGL ground truth, unclipped"},
    "label": {"dtype": "int64", "shape": "(H, W)", "values": "0..6", "note": "rounded from float32 storage; validated"},
}


def _require_numpy():
    try:
        import numpy as np  # type: ignore
    except Exception as e:
        raise RuntimeError(f"numpy is required by the experiment interface: {e}") from e
    return np


def image_to_tensor(arr: Any) -> Any:
    """HWC uint8 [0,255] -> CHW float32 [0,1]. Raises on unexpected rank/dtype."""
    np = _require_numpy()
    a = np.asarray(arr)
    if a.ndim != 3 or a.shape[2] != 3:
        raise ValueError(f"RGB image must be HWC with 3 channels, got shape {a.shape}")
    if a.dtype != np.uint8:
        raise ValueError(f"RGB image must be uint8 (raw dataset semantics), got {a.dtype}")
    try:
        import torch  # type: ignore

        return torch.from_numpy(a).permute(2, 0, 1).to(torch.float32).div_(255.0)
    except ImportError:
        return (a.transpose(2, 0, 1).astype(np.float32) / 255.0)


def height_to_tensor(arr: Any) -> Any:
    """(H,W)/(H,W,1) numeric -> float32 (1,H,W) meters. No clipping. Records NaN/Inf presence for caller."""
    np = _require_numpy()
    a = np.asarray(arr)
    if a.ndim == 3 and a.shape[2] == 1:
        a = a[:, :, 0]
    if a.ndim != 2:
        raise ValueError(f"Height must be (H,W) or (H,W,1), got shape {a.shape}")
    f = a.astype(np.float32)
    try:
        import torch  # type: ignore

        return torch.from_numpy(f).unsqueeze(0)
    except ImportError:
        return f[None, :, :]


def label_to_tensor(arr: Any) -> Any:
    """(H,W) stored labels -> int64 (H,W) with values in 0..6.

    The distribution stores labels as float32 (M2 probe); integer-valued
    entries are rounded, anything else raises — never silently coerced.
    """
    np = _require_numpy()
    a = np.asarray(arr)
    if a.ndim == 3 and a.shape[2] == 1:
        a = a[:, :, 0]
    if a.ndim != 2:
        raise ValueError(f"Label must be (H,W) or (H,W,1), got shape {a.shape}")
    f = np.asarray(a, dtype=np.float64)
    if not bool((f == np.round(f)).all()):
        bad = sorted({float(v) for v in np.unique(f) if float(v) != round(float(v))})[:8]
        raise ValueError(f"Label contains non-integer values (e.g. {bad}); refusing to coerce")
    ints = {int(v) for v in np.unique(f)}
    invalid = sorted(ints - set(GAMUS_VALID_LABELS))
    if invalid:
        raise ValueError(f"Label contains out-of-contract class values {invalid} (valid {sorted(GAMUS_VALID_LABELS)})")
    try:
        import torch  # type: ignore

        return torch.from_numpy(np.round(f).astype(np.int64))
    except ImportError:
        return np.round(f).astype(np.int64)


class GamusExperimentDataset:
    """Manifest-driven, deterministic sample access for future experiments.

    Args:
        records: explicit list of GamusRecord (any order; sorted internally).
        root: dataset root for resolving relative manifest paths.
        manifest_path: alternative to `records` — load from a manifest file.
            Exactly one of `records` / `manifest_path` must be given.
        split: optional split filter (canonicalized); preserved GAMUS meaning
            (train/val/test) — never re-splits.
        transform: optional callable `(image, height, label, record) -> tuple`
            applied per sample. Default None = deterministic identity.
        load_label: if False, label loading is skipped (label=None).

    The dataset exposes `manifest_revision()` info (record hashes) so an
    experiment can log dataset revision + manifest + subset seed/size/IDs.
    """

    def __init__(
        self,
        records: Optional[Iterable[GamusRecord]] = None,
        root: Optional[Path | str] = None,
        manifest_path: Optional[Path | str] = None,
        split: Optional[str] = None,
        transform: Optional[Callable[..., tuple]] = None,
        load_label: bool = True,
    ) -> None:
        if (records is None) == (manifest_path is None):
            raise ValueError("Provide exactly one of `records` or `manifest_path`")
        if manifest_path is not None:
            data = load_manifest(manifest_path)
            recs = [GamusRecord.from_dict(d) for d in data.get("records", [])]
            self.manifest_version = data.get("version")
        else:
            recs = list(records or [])
            self.manifest_version = None
        if split is not None:
            wanted = canonical_split(split)
            recs = [r for r in recs if r.split == wanted]
        order = {s: i for i, s in enumerate(GAMUS_SPLITS)}
        recs.sort(key=lambda r: (order.get(r.split, 99), r.sample_id))
        self.records: list[GamusRecord] = recs
        self.root = Path(root) if root is not None else None
        self.split = canonical_split(split) if split is not None else None
        self.transform = transform
        self.load_label = load_label

    def __len__(self) -> int:
        return len(self.records)

    def sample_ids(self) -> list[str]:
        return [r.sample_id for r in self.records]

    def manifest_revision(self) -> dict[str, Any]:
        """Deterministic fingerprint of the exact record set (for experiment logs)."""
        return {
            "manifest_version": self.manifest_version,
            "count": len(self.records),
            "split": self.split,
            "sample_ids": self.sample_ids(),
            "record_hashes": [r.record_hash() for r in self.records],
        }

    def _resolve(self, rel: Optional[str]) -> Optional[Path]:
        if rel is None:
            return None
        p = Path(rel)
        if p.is_absolute():
            return p
        if self.root is None:
            raise FileNotFoundError(
                f"Relative manifest path '{rel}' cannot be resolved without `root`; "
                "pass root=... or manifest records with absolute paths"
            )
        return self.root / rel

    def __getitem__(self, index: int) -> dict[str, Any]:
        from depthwizard.data.adapter import _load_array_h5

        record = self.records[index]  # IndexError on out-of-range (positional, deterministic)
        img_path = self._resolve(record.image_path)
        h_path = self._resolve(record.height_path)
        l_path = self._resolve(record.label_path)
        if img_path is None or not img_path.is_file():
            raise FileNotFoundError(f"Missing image file for sample '{record.sample_id}': {img_path}")
        if h_path is None or not h_path.is_file():
            raise FileNotFoundError(f"Missing height file for sample '{record.sample_id}': {h_path}")
        image_raw, _, _ = _load_array_h5(img_path)
        height_raw, _, _ = _load_array_h5(h_path)
        label_raw = None
        if self.load_label and l_path is not None and l_path.is_file():
            label_raw, _, _ = _load_array_h5(l_path)
        image = image_to_tensor(image_raw)
        height = height_to_tensor(height_raw)
        label = label_to_tensor(label_raw) if label_raw is not None else None
        # Spatial alignment guard (tensor shapes, no silent resize/crop).
        h_img, w_img = int(image.shape[1]), int(image.shape[2])
        if int(height.shape[1]) != h_img or int(height.shape[2]) != w_img:
            raise ValueError(
                f"Shape mismatch for '{record.sample_id}': image {(h_img, w_img)} vs "
                f"height {(int(height.shape[1]), int(height.shape[2]))}"
            )
        if label is not None and (int(label.shape[0]) != h_img or int(label.shape[1]) != w_img):
            raise ValueError(
                f"Shape mismatch for '{record.sample_id}': image {(h_img, w_img)} vs "
                f"label {(int(label.shape[0]), int(label.shape[1]))}"
            )
        if self.transform is not None:
            image, height, label = self.transform(image, height, label, record)
        return {
            "sample_id": record.sample_id,
            "split": record.split,
            "image": image,
            "height": height,
            "label": label,
            "metadata": {
                "source": record.source,
                "manifest_version": self.manifest_version,
                "image_path": str(img_path),
                "height_path": str(h_path),
                "label_path": str(l_path) if l_path is not None else None,
                "tensor_spec": "image CHW float32 [0,1]; height 1HW float32 meters (nDSM/AGL); label HW int64 0..6",
                "height_is_ndsm_agl_ground_truth": True,
            },
        }

    def __repr__(self) -> str:
        return f"GamusExperimentDataset(n={len(self)}, split={self.split}, manifest_version={self.manifest_version})"


# Optional torch Dataset registration: makes isinstance(..., torch.utils.data.Dataset)
# true when torch is installed, without requiring torch otherwise.
try:
    from torch.utils.data import Dataset as _TorchDataset  # type: ignore

    class GamusTorchDataset(GamusExperimentDataset, _TorchDataset):  # type: ignore
        """Same contract as GamusExperimentDataset, also a torch Dataset."""

except ImportError:  # pragma: no cover - torch-absent environments
    GamusTorchDataset = GamusExperimentDataset  # type: ignore
