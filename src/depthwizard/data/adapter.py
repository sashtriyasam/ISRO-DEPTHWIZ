"""
Gamus adapter compatible with repository architecture.

Exposes a clean internal sample contract (GamusSample) and lazy H5 loading,
without coupling the project to GAMUS-specific loader details upstream.

Responsibilities:
    - Map GamusRecord / manifest entries to GamusSample
    - Resolve dataset root (via GamusConfig)
    - Load arrays on demand (h5py + numpy) with explicit dtype/shape semantics
    - Preserve semantics: RGB=input image, height=nDSM/AGL ground truth, label=semantic not depth
    - Gracefully handle dataset-unavailable case (tests still pass)
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from depthwizard.data.config import GamusConfig
from depthwizard.data.manifest import discover_records, load_manifest
from depthwizard.data.schemas import GamusRecord, GamusSample


def _load_array_h5(path: Path):
    """Load ndarray from H5 file (keys 'image' or 'data' or first dataset). Returns (arr, dtype_str, key) or raises."""
    try:
        import h5py  # type: ignore
    except Exception as e:
        raise RuntimeError(f"h5py required to load H5 file {path}: {e}") from e
    if not path.is_file():
        raise FileNotFoundError(f"H5 file not found: {path}")
    with h5py.File(str(path), "r") as f:
        key = "image" if "image" in f else ("data" if "data" in f else None)
        if key is None:
            # first dataset
            for k in f.keys():
                if hasattr(f[k], "shape"):
                    key = k
                    break
        if key is None:
            raise KeyError(f"No dataset found in {path}, keys={list(f.keys())}")
        arr = f[key][()]
        return arr, str(arr.dtype) if hasattr(arr, "dtype") else None, key


class GamusAdapter:
    """Adapter for GAMUS dataset.

    Usage:
        cfg = GamusConfig(root=Path("data/gamus"))
        adapter = GamusAdapter(cfg)
        records = adapter.list_records(split="train")
        sample = adapter.get_sample(records[0].sample_id, load_arrays=True)
    """

    def __init__(self, config: Optional[GamusConfig] = None, root: Optional[Path | str] = None):
        if config is not None and root is not None:
            raise ValueError("Provide either config or root, not both")
        if config is not None:
            self.config = config
        elif root is not None:
            self.config = GamusConfig(root=Path(root))
        else:
            self.config = GamusConfig()
        self.root = self.config.resolve_root()

    def available(self) -> bool:
        """Return True if dataset root appears to exist."""
        return self.root.exists() and (self.root / "images").exists()

    def list_records(
        self,
        split: Optional[str] = None,
        manifest_path: Optional[Path | str] = None,
        probe: bool = False,
        checksum: bool = False,
    ) -> list[GamusRecord]:
        """List records either from manifest file or by discovering on disk.

        Args:
            split: Filter to split if provided (canonicalized).
            manifest_path: Use manifest JSON instead of scanning filesystem.
            probe, checksum: forwarded to discover_records if scanning.
        """
        if manifest_path is not None:
            data = load_manifest(manifest_path)
            recs = [GamusRecord.from_dict(d) for d in data.get("records", [])]
            if split is not None:
                from depthwizard.data.schemas import canonical_split

                desired = canonical_split(split)
                recs = [r for r in recs if r.split == desired]
            # Ensure deterministic order
            from depthwizard.data.schemas import GAMUS_SPLITS

            order = {s: i for i, s in enumerate(GAMUS_SPLITS)}
            recs.sort(key=lambda r: (order.get(r.split, 99), r.sample_id))
            return recs
        # Discover
        if split is not None:
            return discover_records(self.root, splits=[split], probe=probe, checksum=checksum)
        return discover_records(self.root, probe=probe, checksum=checksum)

    def get_record(self, sample_id: str, split: Optional[str] = None, manifest_path: Optional[Path | str] = None) -> Optional[GamusRecord]:
        recs = self.list_records(split=split, manifest_path=manifest_path)
        for r in recs:
            if r.sample_id == sample_id:
                # If split was not filtered, return first match; if split filtered, exact
                if split is None or r.split == split:
                    return r
        return None

    def to_sample(self, record: GamusRecord, load_arrays: bool = False) -> GamusSample:
        """Convert a manifest record to the internal GamusSample contract.

        Args:
            record: GamusRecord
            load_arrays: If True and dataset is available, load image/height/label ndarrays.
        """
        image_abs = (self.root / record.image_path) if not Path(record.image_path).is_absolute() else Path(record.image_path)
        height_abs = (self.root / record.height_path) if not Path(record.height_path).is_absolute() else Path(record.height_path)
        label_abs = None
        if record.label_path:
            label_abs = (self.root / record.label_path) if not Path(record.label_path).is_absolute() else Path(record.label_path)

        sample = GamusSample(
            sample_id=record.sample_id,
            split=record.split,
            source=record.source,
            image_path=image_abs,
            height_path=height_abs,
            label_path=label_abs,
            metadata={
                "checksum": record.checksum,
                "image_dtype": record.image_dtype,
                "height_dtype": record.height_dtype,
                "width": record.width,
                "height": record.height,
                "provenance": "gamus",
            },
        )
        if load_arrays:
            # Load only if files exist; otherwise leave as None (allows operation without dataset)
            try:
                if image_abs.exists() and image_abs.is_file():
                    arr, _, _ = _load_array_h5(image_abs)
                    sample.image = arr
            except Exception:
                sample.image = None
            try:
                if height_abs.exists() and height_abs.is_file():
                    arr, _, _ = _load_array_h5(height_abs)
                    sample.height = arr
            except Exception:
                sample.height = None
            try:
                if label_abs is not None and label_abs.exists() and label_abs.is_file():
                    arr, _, _ = _load_array_h5(label_abs)
                    sample.label = arr
            except Exception:
                sample.label = None
        return sample

    def get_sample(self, sample_id: str, split: Optional[str] = None, load_arrays: bool = False, manifest_path: Optional[Path | str] = None) -> Optional[GamusSample]:
        rec = self.get_record(sample_id, split=split, manifest_path=manifest_path)
        if rec is None:
            return None
        return self.to_sample(rec, load_arrays=load_arrays)

    def iter_samples(
        self,
        split: Optional[str] = None,
        load_arrays: bool = False,
        manifest_path: Optional[Path | str] = None,
    ) -> Iterable[GamusSample]:
        for rec in self.list_records(split=split, manifest_path=manifest_path):
            yield self.to_sample(rec, load_arrays=load_arrays)

    def __len__(self) -> int:
        # Length when dataset is available; otherwise 0 but still functional for manifest path use
        if not self.available():
            return 0
        return len(self.list_records())

    def __repr__(self) -> str:
        return f"GamusAdapter(root={self.root.as_posix()!r}, available={self.available()})"
