"""
Deterministic tiny acquisition of real GAMUS samples.

Downloads only the minimum required H5 files from the pinned HF distribution
(`earthflow/GAMUS`) into the configured `GamusConfig` root. Raw data stays
outside Git tracking (see `.gitignore`: `data/gamus/`, `*.h5`).

Default sample set is deterministic: the first N train sample IDs in sorted
order (no randomness, no filesystem dependence). Override explicitly via
`--samples` for a different documented set.

Requires the optional `huggingface_hub` package (NOT a project dependency).
Fails clearly when the network or package is unavailable — never fakes data.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Iterable, Optional

from depthwizard.data.config import GamusConfig
from depthwizard.data.schemas import (
    expected_height_filename,
    expected_image_filename,
    expected_label_filename,
)

HF_REPO_ID = "earthflow/GAMUS"
# Deterministic default probe set: first 3 train sample IDs (sorted) observed
# in the pinned distribution listing (verified 2026-09-04: 5004 train files).
DEFAULT_PROBE_SAMPLES = ("DC_01_25", "DC_02_24", "DC_02_25")
DEFAULT_PROBE_SPLIT = "train"


def _repo_paths_for_sample(sample_id: str, split: str) -> dict[str, str]:
    """Map modality -> HF repo-relative path for one sample."""
    return {
        "image": f"images/{split}/{expected_image_filename(sample_id)}",
        "height": f"heights/{split}/{expected_height_filename(sample_id)}",
        "label": f"classes/{split}/{expected_label_filename(sample_id)}",
    }


def acquire_samples(
    root: Path | str,
    sample_ids: Iterable[str] = DEFAULT_PROBE_SAMPLES,
    split: str = DEFAULT_PROBE_SPLIT,
    overwrite: bool = False,
) -> list[Path]:
    """Download H5 files for `sample_ids` into `root`, preserving repo layout.

    Returns list of local destination paths (sorted deterministically).
    Skips files already present unless `overwrite=True`.
    Raises RuntimeError with an actionable message if `huggingface_hub` is
    missing or the download fails.
    """
    try:
        from huggingface_hub import hf_hub_download  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "huggingface_hub is required for GAMUS acquisition but is not installed. "
            "Install it separately (pip install huggingface_hub) or place H5 files "
            f"manually under the configured root. Original error: {e}"
        ) from e

    root = Path(root)
    ids = sorted(set(sample_ids))
    if not ids:
        raise ValueError("sample_ids must be non-empty")
    dests: list[Path] = []
    for sid in ids:
        for _modality, repo_path in sorted(_repo_paths_for_sample(sid, split).items()):
            dest = root / repo_path
            dests.append(dest)
            if dest.is_file() and not overwrite:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                cached = hf_hub_download(HF_REPO_ID, filename=repo_path, repo_type="dataset")
            except Exception as e:
                raise RuntimeError(
                    f"Failed to download '{repo_path}' from HF '{HF_REPO_ID}'. "
                    f"Check network access and dataset availability. Original error: {e}"
                ) from e
            shutil.copyfile(cached, dest)
    return sorted(dests)


def acquire_with_config(
    config: Optional[GamusConfig] = None,
    sample_ids: Iterable[str] = DEFAULT_PROBE_SAMPLES,
    split: str = DEFAULT_PROBE_SPLIT,
    overwrite: bool = False,
) -> list[Path]:
    """Acquire using `GamusConfig` root resolution (env `GAMUS_ROOT` supported)."""
    cfg = config or GamusConfig()
    return acquire_samples(cfg.resolve_root(), sample_ids=sample_ids, split=split, overwrite=overwrite)


def main() -> None:
    ap = argparse.ArgumentParser(description="Deterministically acquire a tiny real GAMUS sample set")
    ap.add_argument("--root", type=str, default=None, help="Dataset root (default: GamusConfig resolution)")
    ap.add_argument("--split", type=str, default=DEFAULT_PROBE_SPLIT, help="Split to acquire from")
    ap.add_argument(
        "--samples",
        type=str,
        nargs="*",
        default=list(DEFAULT_PROBE_SAMPLES),
        help="Explicit sample IDs (default: first 3 sorted train IDs)",
    )
    ap.add_argument("--overwrite", action="store_true", help="Re-download files already present")
    args = ap.parse_args()
    root = Path(args.root) if args.root else GamusConfig().resolve_root()
    dests = acquire_samples(root, sample_ids=args.samples, split=args.split, overwrite=args.overwrite)
    print(f"Acquired {len(dests)} files under {root}")
    for d in dests:
        print(f"  {d.relative_to(root).as_posix()}")


if __name__ == "__main__":
    main()
