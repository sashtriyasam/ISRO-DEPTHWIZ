"""Kaggle GPU job: train the DepthWizard nDSM height model.

Input: the private dataset staged by scripts/kaggle/stage_dataset.py
(crops, DA-V2 Small base checkpoint, DA-V2 source, trainer). Output in
/kaggle/working: depthwizard_ndsm_vits.pth, its JSON training record and
train.log. The trainer is the repository's scripts/train_ndsm.py, unchanged.
"""

import os
import subprocess
import sys
import zipfile
from pathlib import Path

EPOCHS = int(os.environ.get("DW_EPOCHS", "20"))
BATCH = int(os.environ.get("DW_BATCH", "16"))
INPUT = Path("/kaggle/input")
WORK = Path("/kaggle/working")
TEMP = Path("/kaggle/temp")


def find(name: str) -> Path:
    hits = sorted(INPUT.rglob(name))
    if not hits:
        raise SystemExit(f"{name} not found under {INPUT}")
    return hits[0]


def crop_dirs() -> list[Path]:
    dirs = {p.parent for p in INPUT.rglob("*.npz")}
    if not dirs:  # zips not auto-extracted: extract them ourselves
        for archive in INPUT.rglob("*.zip"):
            with zipfile.ZipFile(archive) as z:
                z.extractall(TEMP)
        dirs = {p.parent for p in TEMP.rglob("*.npz")}
    return sorted(dirs)


def main() -> int:
    data = crop_dirs()
    trainer = find("train_ndsm.py")
    base = find("depth_anything_v2_vits.pth")
    dav2 = find("dpt.py").parent.parent  # folder containing depth_anything_v2/
    if not (dav2 / "depth_anything_v2").is_dir():
        with zipfile.ZipFile(find("dav2_src.zip")) as z:
            z.extractall(TEMP)
        dav2 = TEMP / "dav2_src"

    # The trainer only needs ensure_dav2_source_on_path() from the app package.
    stub = TEMP / "stub" / "depthwizard" / "runtime"
    stub.mkdir(parents=True, exist_ok=True)
    (stub.parent / "__init__.py").write_text("")
    (stub / "__init__.py").write_text("")
    (stub / "diagnostics.py").write_text("def ensure_dav2_source_on_path():\n    return None\n")

    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(TEMP / "stub"), str(dav2)]))
    cmd = [
        sys.executable,
        str(trainer),
        "--data",
        *map(str, data),
        "--base",
        str(base),
        "--out",
        str(WORK / "depthwizard_ndsm_vits.pth"),
        "--epochs",
        str(EPOCHS),
        "--batch",
        str(BATCH),
        "--workers",
        "4",
    ]
    print("crop dirs:", [str(d) for d in data], flush=True)
    print("command:", " ".join(cmd), flush=True)
    with open(WORK / "train.log", "w") as log:
        proc = subprocess.Popen(
            cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            print(line, end="", flush=True)
            log.write(line)
            log.flush()
    return proc.wait()


if __name__ == "__main__":
    raise SystemExit(main())
