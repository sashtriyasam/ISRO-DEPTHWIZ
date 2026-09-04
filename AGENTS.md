# AGENTS.md — DepthWizard

- **Track owners**: Shravan (ML/data), Shivam (desktop/infra), Aryan (web/3D)
- **Shravan milestone 5 scope**: single-factor extended training of the M4 head (epochs 15 -> 30, all else frozen), M5 reference report. No architecture/loss/normalization/augmentation/fine-tuning changes, no DA3, no calibration/DSM, no UI/Three.js.
- **Shared interfaces**: Changes to `src/depthwizard/data/` schema or `configs/` require Shravan + Shivam review (see src/depthwizard/data/schemas.py:1). New `DepthBackend`/`DepthResult` boundary (`src/depthwizard/depth/base.py`) likewise requires Shivam review before integration.
- **Shared interfaces**: Changes to `src/depthwizard/data/` schema or `configs/` require Shravan + Shivam review (see src/depthwizard/data/schemas.py:1).
- **Data**: never commit raw .h5, checkpoints, hf caches, predictions. See data/README.md:1.
- **Config**: dataset root via `GamusConfig` (env `GAMUS_ROOT` or `configs/gamus*.json`), not hardcoded paths.
- **Determinism**: manifests and subsets are sorted + hash-based; no filesystem-order dependence.
- **Tests**: `pytest -q` must pass without real GAMUS dataset (fixture-based).
