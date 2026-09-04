# Depth Anything V2 Small — Upstream Audit, License & Frozen Baseline Protocol (M3)

**Date:** 2026-09-04
**Author:** Shravan (ML/data)
**Branch:** `feat/shravan-depth-anything-v2-baseline`

Upstream and checkpoint facts below were inspected live on 2026-09-04 (API + raw file fetch).
Baseline numbers are tool-generated (`experiments/depth-anything-v2/bringup-cpu-3tile/results.json`).

---

## 1. Upstream audit

| Item | Value |
|---|---|
| Repository | `https://github.com/DepthAnything/Depth-Anything-V2` (official; NeurIPS 2024, arXiv:2406.09414) |
| Inspected revision | `a561b849ebae10a6f5ef49e26c83cbbcd36c71bf` (HEAD of `main`, 2026-03-24, verified via GitHub API) |
| Inspection method | Web fetch only (README, `requirements.txt`, `depth_anything_v2/dpt.py`, `dinov2.py`) + one read-only clone **outside** the tracked tree (pinned at the same commit, never modified, `.git` not vendored) |
| Architecture (Small) | DINOv2 ViT-S encoder (`vits`, intermediate layers [2,5,8,11], patch 14) + DPT head; `features=64`, `out_channels=[48,96,192,384]` |
| Params (Small) | 24,785,089 measured at construction (spec: 24.8M) |
| Inference API | `DepthAnythingV2(**config).infer_image(raw_bgr, input_size=518)` → H×W numpy float (source size restored) |
| Code license | Repo carries a LICENSE file; model-scale terms below govern weights |

## 2. License & checkpoint provenance

| Item | Value |
|---|---|
| Selected checkpoint | HF `depth-anything/Depth-Anything-V2-Small` file `depth_anything_v2_vits.pth` |
| Checkpoint sha | `03876f8651c73a60fe4c2c48294e09fcb6838fcf` (snapshot 2024-07-08, ungated, 99,218,434 B locally) |
| Checkpoint license | **Apache-2.0** (HF `cardData.license`, tags `license:apache-2.0`) — the only DA-V2 scale under a permissive license |
| Why Small | M1 names Small the default final-integration candidate; Base/Large/Giant are **CC-BY-NC-4.0** (non-commercial) per upstream README and are NOT integrated |
| Code reuse | None vendored; backend imports the official `depth_anything_v2` package (pinned clone on PYTHONPATH or equivalent install) |
| Weights policy | Resolved via explicit path → `DW_DAV2_CKPT` → `checkpoints/depth_anything_v2_vits.pth`; git-ignored, never committed |

## 3. Preprocessing contract (from audited `dpt.py`)

- Entry: `infer_image(raw_image: BGR uint8 HWC, input_size=518)` — callers pass RGB, backend converts RGB→BGR with cv2 (documented in `PREPROCESSING`)
- `BGR2RGB`, `/255.0` → Resize (keep aspect ratio, lower-bound, multiple of 14, `INTER_CUBIC`) → ImageNet normalize (mean [0.485,0.456,0.406], std [0.229,0.224,0.225]) → `PrepareForNet` (HWC→CHW)
- Forward: DINOv2 intermediates → DPT head → ReLU (non-negative output)
- Output restore: bilinear interpolate to source (H,W), `align_corners=True`
- Default `input_size=518`; device auto cuda/mps/cpu upstream — backend requires explicit `device` (no silent fallback)
- Dataset loading (M2 `GamusExperimentDataset`/adapter) stays separate from this model preprocessing

## 4. Output semantics

- Monocular **relative** depth, scale-ambiguous, ReLU'd ≥ 0. `DepthResult`: `scale_semantics="relative"`, `is_metric=False`, `confidence=None` (model provides none)
- Rules A/B enforced in code: no meter conversion exists; `metric_height()` raises toward Shivam's calibration subsystem
- Bring-up observation: prediction range ≈ [0.4, 2.5] vs GAMUS meters [0, 44.5] — direct comparison would be meaningless (Rule F)

## 5. Frozen baseline protocol (stable for future DA-3 comparison)

1. Records: deterministic manifest (`manifests/gamus.manifest.json`), explicit `--split`, optional `--samples`/`--subset`/`--max-samples`; sorted by (split, sample_id); never re-split
2. Mask: finite prediction AND finite target; negative heights kept (M2 sentinel-candidate rule); no clipping
3. Per-image affine eval only: `aligned = a·pred + b` via closed-form least squares on that image's masked pixels; degenerate (constant/<2 px) flagged, never NaN
4. Metrics: aligned MAE/RMSE + Pearson + Spearman + valid coverage + per-image runtime; raw distribution stats only (no raw-vs-meter error)
5. Reproducibility log: experiment/model/checkpoint revisions, preprocessing, resolution, device, software versions, seed, timing; `memory: not measured` when unavailable

## 6. Bring-up results (3 train tiles, CPU — smoke, NOT the final benchmark)

Command:

```bash
PYTHONPATH=src:<pinned-clone> python -m depthwizard.experiments.depth_anything_v2 \
  --manifest manifests/gamus.manifest.json --split train \
  --device cpu --output experiments/depth-anything-v2/bringup-cpu-3tile --visuals
```

Environment: Python 3.14.3, torch 2.14.0+cpu, torchvision 0.29.0+cpu, numpy 2.5.0, h5py 3.16.0, cv2 5.0.0, Windows 11, cpu. Model load 2.52 s; mean inference 0.78 s/image (0.74/0.84/0.77 s).

| Sample | Affine a | Affine b | Aligned MAE (m) | Aligned RMSE (m) | Pearson | Spearman |
|---|---|---|---|---|---|---|
| DC_01_25 | −9.934 | 20.64 | 10.292 | 11.845 | −0.158 | 0.003 |
| DC_02_24 | −5.493 | 19.82 | 11.580 | 12.972 | −0.137 | −0.054 |
| DC_02_25 | 3.094 | 3.18 | 6.032 | 7.946 | 0.093 | 0.281 |
| **mean** | — | — | **9.302** | **10.921** | **−0.067** | **0.077** |

Valid coverage 100% (3/3); prediction finite coverage 100%.

Reading (n=3, cautious): frozen DA-V2-Small detects building-like structures (see `outputs/bringup-cpu-3tile/*.png`, git-ignored) but pixel-wise correlation with nDSM is near-zero/negative on 2/3 tiles, with negative affine slopes — the relative-depth sign/scale does not transfer to aerial nDSM without adaptation. This confirms the need for the M4 adaptation milestone; no generalization claim is made beyond these tiles.

## 7. Reproducibility

```bash
pip install -e ".[dev]"            # tests (no weights needed)
pip install -e ".[dav2]"           # torch + torchvision + opencv-python for real inference
export GAMUS_ROOT=data/gamus       # or configs/gamus.json
python -m depthwizard.data.acquire --root "$GAMUS_ROOT"   # tiny sample (or place tiles manually)
python -m depthwizard.experiments.depth_anything_v2 --manifest manifests/gamus.manifest.json \
  --split train --device cpu --output experiments/depth-anything-v2/<id>
python -m pytest -q                # 85 passed, 2 skipped (opt-in real-model tests need weights+package)
```

Upstream clone (inspection only): outside tracked tree, pinned at `a561b84`; provenance preserved, never modified.

## 8. Limitations

- n=3 bring-up on train tiles only; not a benchmark (Rule H)
- Per-image affine uses the target image (declared evaluation protocol, not calibration)
- CPU-only timing; GPU behavior untested (no CUDA here)
- `depth_anything_v2` package resolution via PYTHONPATH documented, not auto-installed
- Memory: not measured
