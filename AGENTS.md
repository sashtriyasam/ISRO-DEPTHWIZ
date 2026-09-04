# AGENTS.md — DepthWizard

- **Track owners**: Shravan (ML/data), Shivam (desktop/infra), Aryan (web/3D)
- **Shravan milestone 3 scope**: Depth Anything V2 Small frozen baseline (`depth/`, `eval/`, `experiments/`), per-image affine research evaluation, bring-up report. No training, no adaptation head, no calibration/DSM, no UI/Three.js.
- **Shared interfaces**: Changes to `src/depthwizard/data/` schema or `configs/` require Shravan + Shivam review (see src/depthwizard/data/schemas.py:1). New `DepthBackend`/`DepthResult` boundary (`src/depthwizard/depth/base.py`) likewise requires Shivam review before integration.
- **Shared interfaces**: Changes to `src/depthwizard/data/` schema or `configs/` require Shravan + Shivam review (see src/depthwizard/data/schemas.py:1).
- **Data**: never commit raw .h5, checkpoints, hf caches, predictions. See data/README.md:1.
- **Config**: dataset root via `GamusConfig` (env `GAMUS_ROOT` or `configs/gamus*.json`), not hardcoded paths.
- **Determinism**: manifests and subsets are sorted + hash-based; no filesystem-order dependence.
- **Tests**: `pytest -q` must pass without real GAMUS dataset (fixture-based).
