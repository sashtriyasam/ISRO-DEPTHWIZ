# DepthWizard — ISRO-DEPTHWIZ (SIH 26175)

**Single-View Height Estimation and 3D Flythrough**

Shravan ML/data track — Milestone 8: geographic training diversity experiment on frozen M5 raw-meter model (M5 current reference).

M1/M2 established and verified the dataset contract; M3 froze the relative-depth baseline. M4 adds masked-L1 training of a ~23k-param head on frozen features with val-selected checkpoints. M5 extends training to 30 epochs. M6 evaluates geographic generalization. M7 tests z-score target normalization. M8 tests geographic training diversity (8/8/8 city train composition). No backbone fine-tuning, calibration/DSM, or Three.js visualization is included.

## Quick start (no dataset or weights required)

```bash
pip install -e ".[dev]"
pytest -q
python -m depthwizard.data.manifest --help
```

Real inference additionally needs `pip install -e ".[dav2]"`, the pinned upstream package (see `docs/research/depth-anything-v2.md`), and the Small checkpoint under `checkpoints/` (git-ignored; `DW_DAV2_CKPT` override supported).

## Reproducibility

See:

- `docs/research/gamus-audit.md` — full upstream GAMUS audit (re-verified 2026-09-04, commit `6ed44ba87b59911144430ebc0ca02c1f7a1c62b4`)
- `docs/research/gamus-empirical-probe.md` — M2 empirical probe report (real H5 measurements, tool-generated)
- `docs/research/depth-anything-v2.md` — M3 upstream audit, license, preprocessing, baseline protocol + bring-up results
- `docs/research/remote-sensing-adaptation.md` — M4 adaptation report (Stage A results, ablations deferred)
- `docs/research/m5-extended-training.md` — M5 single-factor report (epochs 15 -> 30; current reference)
- `docs/research/m6-geographic-validation.md` — M6 geographic validation report (frozen M5 eval)
- `docs/research/m7-target-normalization.md` — M7 target normalization report (z-score vs raw)
- `docs/research/dataset-foundation-repro.md` — how to reproduce manifest / dev subset / validation
- `docs/data-provenance.md` — license & provenance
- `configs/gamus.example.json` — example configuration
- `manifests/README.md` — manifest format

## Layout

```
src/depthwizard/data/
  schemas.py      — manifest record & sample contract (frozen, M1+M2 verified)
  config.py       — GamusConfig (root, manifest, subset)
  manifest.py     — deterministic manifest generation (--probe verified on real data)
  subset.py       — deterministic dev-subset selection
  validation.py   — pairing / shape / dtype / class validation
  adapter.py      — GAMUS adapter (lazy H5 loading, contract)
  acquire.py      — deterministic tiny real-data acquisition (M2)
  probe.py        — empirical H5 probe → JSON + Markdown (M2)
  experiment.py   — manifest-driven tensor interface, torch-optional (M2, no training)
src/depthwizard/depth/
  base.py         — DepthBackend / DepthResult (relative-first; metric raises; Shivam review)
  depth_anything_v2.py — frozen DA-V2-Small adapter (official package, not vendored)
src/depthwizard/eval/
  alignment.py    — mask + per-image affine research eval + metrics (NOT calibration)
src/depthwizard/experiments/
  depth_anything_v2.py — frozen baseline runner → experiments/depth-anything-v2/<id>/
  adapt_dav2.py   — M4 adaptation runner → experiments/dav2-gamus-head-m4-<id>/
  m6_geographic.py — M6 geographic validation runner → experiments/m6-geographic-<id>/
src/depthwizard/adapt/  — M4/M5: features tap + HeightHead + masked-L1 + train/eval (research only)
tests/            — fixture-based + opt-in real-data/real-model tests (no download required)
configs/          — example configs (gamus.*, dav2_baseline.*)
experiments/      — compact config.json + results.json + README.md per run (no rasters)
manifests/        — manifests + compact probe reports only (no raw .h5)
data/             — local dataset root (ignored, see data/README.md)
```

## Data policy

Raw `.h5` tiles, checkpoints, Hugging Face caches, predictions, and CUDA artifacts are **never committed**. Only manifests, schemas, metadata, and config are tracked.

Local dataset root is supplied via config or `GAMUS_ROOT` env var (see `src/depthwizard/data/config.py:12`).

## Tests

All tests use synthetic fixtures under `tests/` and run without the real GAMUS dataset. See `tests/README.md` if present.

## Branch

`feat/shravan-dav2-geographic-diversity` (M7: `feat/shravan-dav2-target-normalization`, M6: `feat/shravan-m5-geographic-validation`)
