# DepthWizard — ISRO-DEPTHWIZ (SIH 26175)

**Single-View Height Estimation and 3D Flythrough**

Shravan ML/data track — Milestone 3: Depth Anything V2 Small frozen baseline + reproducible GAMUS bring-up (builds on M1/M2).

M1/M2 established the deterministic dataset contract and empirically verified it against real GAMUS tiles. M3 adds frozen monocular baseline inference (relative depth only), per-image affine research evaluation, and compact experiment artifacts. No training, adaptation, calibration/DSM, or Three.js visualization is included.

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

`feat/shravan-depth-anything-v2-baseline` (M1: `feat/shravan-gamus-audit`, M2: `feat/shravan-gamus-empirical-validation`)
