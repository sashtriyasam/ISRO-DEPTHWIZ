"""
Schemas for GAMUS dataset foundation.

Defines the internal sample contract and manifest record used by adapter, validation,
manifest generation, and downstream training milestones.

Notes:
- RGB is input image; height/AGL (nDSM) is ground-truth geometry; semantic labels are labels, not depth.
- Height must not be silently treated as metric elevation prediction.
- See docs/research/gamus-audit.md for upstream-verified representation details.
"""

from __future__ import annotations

import dataclasses
import hashlib
from pathlib import Path
from typing import Optional

# Verified GAMUS class encoding (see docs/research/gamus-audit.md: classes)
GAMUS_CLASSES: dict[int, str] = {
    0: "others/background",
    1: "ground",
    2: "low vegetation",
    3: "buildings",
    4: "water",
    5: "road",
    6: "tree",
}

GAMUS_CLASS_NAMES: dict[str, int] = {v: k for k, v in GAMUS_CLASSES.items()}
GAMUS_VALID_LABELS = set(GAMUS_CLASSES.keys())

# Splits — note upstream uses `val` (not `valid`/`validation`); we canonicalise to `val`
GAMUS_SPLITS = ("train", "val", "test")
# Alternate names accepted during validation/normalization
GAMUS_SPLIT_ALIASES = {"valid": "val", "validation": "val", "eval": "val"}

# File conventions — verified against upstream gamus_dataset.py and HF siblings
# images: *RGB.h5 (current) or *IMG.h5 (legacy); classes: *CLS.h5; heights: *AGL.h5
GAMUS_IMAGE_SUFFIXES = ("_RGB.h5", "_IMG.h5", "RGB.h5", "IMG.h5")
GAMUS_HEIGHT_SUFFIX = "AGL.h5"
GAMUS_LABEL_SUFFIX = "CLS.h5"

# Expected geometry (from GAMUS paper Table 1, 1024x1024 tiles).
# Not enforced strictly in validation — mismatch is an error if files are present,
# but paper-reported size is advisory for absent-file cases.
GAMUS_EXPECTED_TILE_SIZE = (1024, 1024)  # (H, W)


def _strip_image_suffix(filename: str) -> Optional[str]:
    """Return sample_id (base without suffix+ext) for an image filename, or None if not an image file.

    Handles both current (`_RGB.h5`) and legacy (`_IMG.h5`, `IMG.h5`, `RGB.h5`) conventions.
    Examples:
        DC_03_26_RGB.h5 -> DC_03_26
        DC_03_26_IMG.h5 -> DC_03_26
        DC_03_26CLS.h5  -> None
    """
    for suf in sorted(GAMUS_IMAGE_SUFFIXES, key=len, reverse=True):
        if filename.endswith(suf):
            # Also handle leading underscore variants robustly
            # filename = <sample_id><suf>  e.g. DC_03_26 + _RGB.h5
            # strip suf exactly
            return filename[: -len(suf)].rstrip("_")
    # Generic fallback: if it ends with .h5 but wasn't image-like, return None to signal mismatch
    if filename.endswith(".h5"):
        # Try heuristic: if contains CLS or AGL, not image
        if "CLS.h5" in filename or "AGL.h5" in filename:
            return None
        # Otherwise treat stem as id
        stem = filename[:-3]
        if stem.endswith(".h5"):
            stem = stem[:-3]
        return stem.rstrip("_")
    return None


def canonical_split(split: str) -> str:
    s = split.strip().lower()
    s = GAMUS_SPLIT_ALIASES.get(s, s)
    if s not in GAMUS_SPLITS:
        raise ValueError(f"Unknown split '{split}': expected one of {GAMUS_SPLITS} (aliases {sorted(GAMUS_SPLIT_ALIASES)})")
    return s


def expected_image_filename(sample_id: str, style: str = "RGB") -> str:
    # style RGB is canonical; legacy IMG is accepted on read but never emitted for new manifests
    if style.upper() == "IMG":
        return f"{sample_id}_IMG.h5"
    return f"{sample_id}_RGB.h5"


def expected_height_filename(sample_id: str) -> str:
    return f"{sample_id}_AGL.h5"


def expected_label_filename(sample_id: str) -> str:
    return f"{sample_id}_CLS.h5"


@dataclasses.dataclass(frozen=True, slots=True)
class GamusRecord:
    """Manifest record identifying a single GAMUS sample without embedding raw data.

    Paths are stored relative to dataset root using POSIX separators (e.g. `images/train/DC_03_26_RGB.h5`).
    Ordering of serialized manifests is deterministic (sorted by sample_id then split).
    """

    sample_id: str
    image_path: str  # relative POSIX
    height_path: str
    label_path: Optional[str]  # may be None if label absent (e.g. test split in some distributions)
    split: str  # train|val|test canonical
    source: str = "gamus"  # provenance marker
    # Optional enrichment — populated only when files are actually inspected (not invented)
    checksum: Optional[str] = None  # sha256 hex of image file content when available
    image_dtype: Optional[str] = None  # e.g. "uint8"
    height_dtype: Optional[str] = None  # e.g. "float32"
    width: Optional[int] = None
    height: Optional[int] = None

    def to_dict(self) -> dict:
        d = dataclasses.asdict(self)
        # canonical ordering for serialization (not required but helps determinism)
        return {k: d[k] for k in sorted(d)}

    @staticmethod
    def from_dict(d: dict) -> "GamusRecord":
        return GamusRecord(
            sample_id=d["sample_id"],
            image_path=d["image_path"],
            height_path=d["height_path"],
            label_path=d.get("label_path"),
            split=canonical_split(d["split"]),
            source=d.get("source", "gamus"),
            checksum=d.get("checksum"),
            image_dtype=d.get("image_dtype"),
            height_dtype=d.get("height_dtype"),
            width=d.get("width"),
            height=d.get("height"),
        )

    def record_hash(self) -> str:
        """Stable hash of the record's identity fields (for determinism checks)."""
        payload = f"{self.sample_id}|{self.split}|{self.image_path}|{self.height_path}|{self.label_path or ''}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclasses.dataclass
class GamusSample:
    """In-memory sample contract exposed by the adapter.

    Conceptual fields (see task §6):
        sample_id
        image   — loaded ndarray when available, else None (lazy)
        height  — nDSM ground-truth ndarray when available, else None
        label   — semantic label ndarray when available, else None
        split, source/provenance metadata

    The adapter makes explicit that RGB is input, height (nDSM/AGL) is geometry ground truth,
    and semantic labels are not depth.
    """

    sample_id: str
    split: str
    source: str
    image_path: Path
    height_path: Path
    label_path: Optional[Path]
    # Loaded arrays (optional; None if not loaded or dataset unavailable)
    image: Optional[object] = None  # numpy ndarray of shape (H,W,3) dtype uint8 when loaded
    height: Optional[object] = None  # ndarray (H,W) or (H,W,1) dtype float32
    label: Optional[object] = None  # ndarray (H,W) dtype uint8/int64 with values 0..6
    metadata: Optional[dict] = None

    def __post_init__(self) -> None:
        self.split = canonical_split(self.split)

    @property
    def has_image(self) -> bool:
        return self.image is not None

    @property
    def has_height(self) -> bool:
        return self.height is not None

    @property
    def has_label(self) -> bool:
        return self.label is not None
