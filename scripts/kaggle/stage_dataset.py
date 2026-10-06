#!/usr/bin/env python3
"""Stage the nDSM training inputs as a private Kaggle dataset folder.

Produces <out>/ with:
  ndsm.zip            Swiss LiDAR crops (data/ndsm)
  ndsm_gamus.zip      GAMUS crops (data/ndsm_gamus)
  depth_anything_v2_vits.pth   pinned DA-V2 Small base checkpoint
  dav2_src.zip        upstream Depth-Anything-V2 ``depth_anything_v2`` package
  train_ndsm.py       the trainer (also pushed with each kernel)
  dataset-metadata.json

Kaggle extracts uploaded zips, so the kernel sees plain folders. .npz crops
are already compressed, so zips are written STORED (fast, no gain lost).

Usage:
  python scripts/kaggle/stage_dataset.py --out D:/kaggle_stage/depthwizard-ndsm-data \
      --user shivamshelatkar
"""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _zip_dir(src: Path, dest: Path, arc_root: str, pattern: str = "*") -> int:
    count = 0
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_STORED) as archive:
        for path in sorted(src.rglob(pattern)):
            if path.is_file() and "__pycache__" not in path.parts:
                archive.write(path, f"{arc_root}/{path.relative_to(src).as_posix()}")
                count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--slug", default="depthwizard-ndsm-data")
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    counts = {
        "ndsm": _zip_dir(ROOT / "data" / "ndsm", out / "ndsm.zip", "ndsm", "*.npz"),
        "ndsm_gamus": _zip_dir(
            ROOT / "data" / "ndsm_gamus", out / "ndsm_gamus.zip", "ndsm_gamus", "*.npz"
        ),
        "dav2_src": _zip_dir(
            ROOT / "third_party" / "Depth-Anything-V2" / "depth_anything_v2",
            out / "dav2_src.zip",
            "dav2_src/depth_anything_v2",
            "*.py",
        ),
    }
    shutil.copy2(ROOT / "checkpoints" / "depth_anything_v2_vits.pth", out)
    shutil.copy2(ROOT / "scripts" / "train_ndsm.py", out)
    (out / "dataset-metadata.json").write_text(
        json.dumps(
            {
                "title": "DepthWizard nDSM training crops",
                "id": f"{args.user}/{args.slug}",
                "licenses": [{"name": "other"}],
                "subtitle": "RGB to height-above-ground crops (swisstopo LiDAR, GAMUS)",
            },
            indent=2,
        )
    )
    print(json.dumps({"out": str(out), **counts}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
