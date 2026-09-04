"""
Deterministic development subset selection for GAMUS.

Requirements:
    deterministic, documented, configurable, reproducible, independent of filesystem ordering,
    does not require downloading complete dataset.

Design:
    - Stable sample IDs (GamusRecord.sample_id)
    - Cryptographic hashing (SHA256 of "{seed}:{sample_id}")
    - Explicit sorted ordering then hash ranking
    - Same (records, size, seed, split_source) -> same selected sample_ids

Not claimed to be statistically representative; it is a development subset, not a benchmark.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable, List, Optional

from depthwizard.data.schemas import GamusRecord, canonical_split

DEFAULT_DEV_SEED = "depthwizard-m1"


def _hash_rank(sample_id: str, seed: str) -> str:
    """Cryptographic hash rank key for a sample."""
    return hashlib.sha256(f"{seed}:{sample_id}".encode("utf-8")).hexdigest()


def select_development_subset(
    records: Iterable[GamusRecord],
    size: int,
    seed: str = DEFAULT_DEV_SEED,
    split_source: Optional[str] = None,
) -> List[GamusRecord]:
    """Deterministically select `size` records from `records`.

    Args:
        records: Iterable of GamusRecord (any order — sorted internally).
        size: Desired subset size (0 <= size <= len(filtered)).
        seed: Seed string hashed with sample_id for ranking (change to get different deterministic subset).
        split_source: If provided, filter to records with matching split before selection.

    Returns:
        List of selected records sorted by hash rank (deterministic), then by sample_id for stability.
        If size >= len(candidates), returns all candidates sorted by hash rank.
        If size == 0, returns [].

    Reproducibility: depends only on (sample_ids, seed, size, split_source). No random module.
    """
    if size < 0:
        raise ValueError("size must be >= 0")
    recs = list(records)
    if split_source is not None:
        split_source = canonical_split(split_source)
        recs = [r for r in recs if r.split == split_source]
    # Deterministic pre-sort by sample_id to eliminate input-order dependence before hashing
    recs.sort(key=lambda r: r.sample_id)
    if size == 0 or not recs:
        return [] if size == 0 or not recs else []

    # Compute hash rank for each
    ranked = sorted(recs, key=lambda r: (_hash_rank(r.sample_id, seed), r.sample_id))
    if size >= len(ranked):
        return ranked
    return ranked[:size]


def load_records_from_manifest(manifest_path: Path | str) -> List[GamusRecord]:
    """Load records from a manifest JSON file (reusing manifest.load_manifest for deterministic order)."""
    from depthwizard.data.manifest import load_manifest

    data = load_manifest(manifest_path)
    return [GamusRecord.from_dict(d) for d in data.get("records", [])]


def build_dev_manifest(
    records: Iterable[GamusRecord],
    size: int,
    seed: str = DEFAULT_DEV_SEED,
    split_source: Optional[str] = None,
    output_path: Optional[Path | str] = None,
) -> dict:
    """Build a dev-subset manifest dict from full records.

    Optionally writes to `output_path` deterministically.
    """
    selected = select_development_subset(records, size=size, seed=seed, split_source=split_source)
    manifest = {
        "version": "1.0-dev",
        "source": "gamus-dev-subset",
        "seed": seed,
        "size": size,
        "split_source": split_source,
        "records": [r.to_dict() for r in selected],
    }
    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Build deterministic GAMUS dev-subset manifest")
    ap.add_argument("--manifest", type=str, required=True, help="Input full manifest JSON")
    ap.add_argument("--output", type=str, required=True, help="Output dev manifest JSON")
    ap.add_argument("--size", type=int, default=20, help="Dev subset size (default 20)")
    ap.add_argument("--seed", type=str, default=DEFAULT_DEV_SEED, help="Hash seed")
    ap.add_argument("--split-source", type=str, default=None, help="Filter source split before selection (e.g. train)")
    args = ap.parse_args()
    recs = load_records_from_manifest(args.manifest)
    build_dev_manifest(recs, size=args.size, seed=args.seed, split_source=args.split_source, output_path=args.output)
    print(f"Wrote dev subset ({args.size}, seed={args.seed}) to {args.output}")


if __name__ == "__main__":
    main()
