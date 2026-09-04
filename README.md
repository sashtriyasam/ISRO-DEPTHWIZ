# DepthWizard — ISRO-DEPTHWIZ (SIH 26175)

**Single-View Height Estimation and 3D Flythrough**

Shravan ML/data track — Milestone 2: Empirical GAMUS Validation + Experiment-Ready Interface (builds on M1 foundation).

This repository establishes the deterministic dataset contract, manifest, and development-subset machinery for future depth-model experiments, now empirically verified against real GAMUS tiles. No model training, DSM generation, or Three.js visualization is included in this milestone.

## Quick start (no dataset required)

```bash
pip install -e ".[dev]"
pytest -q
python -m depthwizard.data.manifest --help
```

## Reproducibility

See:

- `docs/research/gamus-audit.md` — full upstream GAMUS audit (re-verified 2026-09-04, commit `6ed44ba87b59911144430ebc0ca02c1f7a1c62b4`)
- `docs/research/gamus-empirical-probe.md` — M2 empirical probe report (real H5 measurements, tool-generated)
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
tests/            — fixture-based + opt-in real-data tests (no download required)
configs/          — example config
manifests/        — manifests + compact probe reports only (no raw .h5)
data/             — local dataset root (ignored, see data/README.md)
```

## Data policy

Raw `.h5` tiles, checkpoints, Hugging Face caches, predictions, and CUDA artifacts are **never committed**. Only manifests, schemas, metadata, and config are tracked.

Local dataset root is supplied via config or `GAMUS_ROOT` env var (see `src/depthwizard/data/config.py:12`).

## Tests

All tests use synthetic fixtures under `tests/` and run without the real GAMUS dataset. See `tests/README.md` if present.

## Branch

`feat/shravan-gamus-audit`
