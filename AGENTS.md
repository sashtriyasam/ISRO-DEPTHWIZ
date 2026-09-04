# AGENTS.md — DepthWizard

- **Track owners**: Shravan (ML/data), Shivam (desktop/infra), Aryan (web/3D)
- **Shravan milestone 7 scope**: target normalization experiment on frozen M5 model (`loss.py` zscore, `train.py` normalized targets, `model.py` inverse normalization, `adapt_dav2_m7.py` runner), M5 config frozen, per-city/per-class/height-bin analysis vs M5. No training protocol change, no architecture change, no DA3, no calibration/DSM, no UI/Three.js.
- **Shared interfaces**: Changes to `src/depthwizard/data/` schema or `configs/` require Shravan + Shivam review (see src/depthwizard/data/schemas.py:1). New `DepthBackend`/`DepthResult` boundary (`src/depthwizard/depth/base.py`) likewise requires Shivam review before integration.
- **Shared interfaces**: Changes to `src/depthwizard/data/` schema or `configs/` require Shravan + Shivam review (see src/depthwizard/data/schemas.py:1).
- **Data**: never commit raw .h5, checkpoints, hf caches, predictions. See data/README.md:1.
- **Config**: dataset root via `GamusConfig` (env `GAMUS_ROOT` or `configs/gamus*.json`), not hardcoded paths.
- **Determinism**: manifests and subsets are sorted + hash-based; no filesystem-order dependence.
- **Tests**: `pytest -q` must pass without real GAMUS dataset (fixture-based).
