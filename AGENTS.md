# AGENTS.md — DepthWizard

- **Track owners**: Shravan (ML/data), Shivam (desktop/infra), Aryan (web/3D)
- **Shravan milestone 4 scope**: frozen DA-V2-Small + lightweight height head (`adapt/`, `experiments/adapt_dav2.py`), masked-L1 training on train split, val-selected checkpoint, research report. No backbone fine-tuning, no DA3, no calibration/DSM, no UI/Three.js.
- **Shared interfaces**: Changes to `src/depthwizard/data/` schema or `configs/` require Shravan + Shivam review (see src/depthwizard/data/schemas.py:1). New `DepthBackend`/`DepthResult` boundary (`src/depthwizard/depth/base.py`) likewise requires Shivam review before integration.
- **Shared interfaces**: Changes to `src/depthwizard/data/` schema or `configs/` require Shravan + Shivam review (see src/depthwizard/data/schemas.py:1).
- **Data**: never commit raw .h5, checkpoints, hf caches, predictions. See data/README.md:1.
- **Config**: dataset root via `GamusConfig` (env `GAMUS_ROOT` or `configs/gamus*.json`), not hardcoded paths.
- **Determinism**: manifests and subsets are sorted + hash-based; no filesystem-order dependence.
- **Tests**: `pytest -q` must pass without real GAMUS dataset (fixture-based).
