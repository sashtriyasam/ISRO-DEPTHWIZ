# AGENTS.md — DepthWizard

- **Track owners**: Shravan (ML/data), Shivam (desktop/infra), Aryan (web/3D)
- **Shravan milestone 1 scope**: dataset audit, schema, deterministic manifest, deterministic dev subset, adapter, validation, tests, provenance docs. No training, no DepthAnything, no DSM, no UI/Three.js.
- **Shared interfaces**: Changes to `src/depthwizard/data/` schema or `configs/` require Shravan + Shivam review (see src/depthwizard/data/schemas.py:1).
- **Data**: never commit raw .h5, checkpoints, hf caches, predictions. See data/README.md:1.
- **Config**: dataset root via `GamusConfig` (env `GAMUS_ROOT` or `configs/gamus*.json`), not hardcoded paths.
- **Determinism**: manifests and subsets are sorted + hash-based; no filesystem-order dependence.
- **Tests**: `pytest -q` must pass without real GAMUS dataset (fixture-based).
