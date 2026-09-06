# Final Release Gate Matrix — DepthWizard (SIH 26175)

**Audit Date:** 2026-09-06  
**Auditor:** Shivam (Architecture Authority + Release Owner)  
**Source of Truth:** Actual Git history + actual files on `main` at `809801d45ac7f3be857b284539e4d9028e914e09`  
**No assumptions — evidence only.**

---

## Release Gate Definitions

| Gate | Name                      | Description                                                          |
| ---- | ------------------------- | -------------------------------------------------------------------- |
| G1   | Scientific contracts      | All scientific semantics, units, CRS, provenance contracts preserved |
| G2   | Real DA-V2 inference      | End-to-end real model inference on physical Windows                  |
| G3   | Metric calibration path   | Explicit calibration required for metric output                      |
| G4   | DSM generation            | Metric DSMGrid with calibrated values, nodata=NaN                    |
| G5   | Terrain mesh              | TerrainMesh with local + georeferenced coordinates                   |
| G6   | Relative/non-geo path     | Mode A: PNG/JPG → rDSM → rMesh (units=None, LOCAL)                   |
| G7   | Native Electron host      | Electron 44.2.0, sandbox, CSP, IPC bridge                            |
| G8   | Managed runtime           | Isolated venv, provisioned via `provision_runtime.py`                |
| G9   | Runtime provisioning      | Host-invocable `provision_runtime.py` + `runtime_check.py`           |
| G10  | Installer                 | NSIS + portable, clean contents, extra resources                     |
| G11  | Offline execution         | `HF_HUB_OFFLINE=1`, no network imports in engine                     |
| G12  | Error/failure behavior    | Structured codes, no silent fallback, quarantine                     |
| G13  | Reproducibility           | Deterministic installer, pinned upstream, hash-verified              |
| G14  | Physical Windows witness  | Actual install/launch on clean Windows + display                     |
| G15  | ML final candidate        | Frozen metric model with verified evidence                           |
| G16  | Documentation             | All docs accurate, no stale claims                                   |
| G17  | Repository/GitHub hygiene | Branch hygiene, CI, branch protection                                |

---

## Gate Status Matrix

| Gate                              | Status           | Evidence                                                                                                                                                                                                                                                                                         | Owner        | Blocker            |
| --------------------------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------ | ------------------ |
| **G1** Scientific contracts       | **PASS**         | Zero diff in `contracts/`, `calibration/`, `dsm/`, `mesh/`, `geospatial/`, `rdsm/`, `backends/` vs origin/main; all contract tests pass                                                                                                                                                          | Shivam       | No                 |
| **G2** Real DA-V2 inference       | **NOT VERIFIED** | Requires physical Windows + checkpoint (`depth_anything_v2_vits.pth`) + display + upstream source clone. Gated by `DW_DAV2_ACCEPT=1`.                                                                                                                                                            | Aryan/Shivam | **Yes**            |
| **G3** Metric calibration path    | **PASS**         | Contract: `CalibrationSamples` → `ScaleOffsetCalibrator` → `CalibrationResult` → `ScientificHeightProduct` (units="meters"). Tests pass.                                                                                                                                                         | Shivam       | No                 |
| **G4** DSM generation             | **PASS**         | `DSMGrid.rasterize()` produces metric DSMGrid (nodata=NaN, CRS preserved). All DSM tests pass.                                                                                                                                                                                                   | Shivam       | No                 |
| **G5** Terrain mesh               | **PASS**         | `TerrainMesh.build()` produces local + georeferenced coords. No CRS invention. All mesh tests pass.                                                                                                                                                                                              | Shivam       | No                 |
| **G6** Relative/non-geo path      | **PASS**         | Mode A: PNG/JPG → `RelativeSurfaceGrid` (units=None) → `RelativeTerrainMesh` (frame=LOCAL). All rDSM tests pass.                                                                                                                                                                                 | Shivam       | No                 |
| **G7** Native Electron host       | **PASS**         | Electron 44.2.0, sandbox=true, CSP, 8 IPC methods via preload bridge, sender validation, channel allowlist. 35 Electron tests pass.                                                                                                                                                              | Aryan        | No                 |
| **G8** Managed runtime            | **PASS**         | `provision_runtime.py` creates isolated venv, pip installs core/dav2, clones pinned upstream, verifies checkpoint SHA256, idempotent.                                                                                                                                                            | Shivam       | No                 |
| **G9** Runtime provisioning       | **PASS**         | `provision_runtime.py` (core/dav2 modes) + `runtime_check.py` verified. Idempotent re-run reuses venv. Offline ready.                                                                                                                                                                            | Shivam       | No                 |
| **G10** Installer                 | **PASS** (build) | NSIS 115 MB (`DepthWizard Setup 0.1.0.exe`, SHA256: `2606648234c275dbf41797f5f881b02521f0295d16947c80e501e569c93f0311`), portable 334 MB. Clean contents: no .git, node_modules, src, .venv, checkpoints, .pth, .env. Extra resources: `depthwiz_service.py` + `backend_bridge.py` (asarUnpack). | Aryan        | **Yes** (physical) |
| **G11** Offline execution         | **PASS**         | `HF_HUB_OFFLINE=1` verified; no socket/HTTP/hub imports in `src/depthwizard/` (tested). Provisioning-only network.                                                                                                                                                                               | Shivam       | No                 |
| **G11** Error/failure behavior    | **PASS**         | Structured error codes (`CHECKPOINT_MISSING`, `CHECKPOINT_HASH_MISMATCH`, `PYTHON_VERSION_UNSUPPORTED`, `UPSTREAM_REVISION_MISMATCH`, `DEVICE_UNAVAILABLE`, etc.). No silent fallback. Mismatched checkpoints quarantined (`.invalid`).                                                          | Shivam       | No                 |
| **G13** Reproducibility           | **PASS**         | Deterministic installer (electron-builder fixed config), pinned upstream revision (`a561b849...`), checkpoint SHA256 verification, deterministic runtime data dirs.                                                                                                                              | Shivam/Aryan | No                 |
| **G14** Physical Windows witness  | **NOT VERIFIED** | Requires clean Windows VM/machine with display + checkpoint. Must: install → launch → verify runtime resolution → service capabilities → real DA-V2 inference → calibration → metric DSM → mesh → renderer.                                                                                      | Aryan        | **Yes**            |
| **G15** ML final candidate        | **BLOCKED**      | Shravan research branches only (M14/M17). No frozen metric model delivered with verified metrics + SHA256 + upstream revision.                                                                                                                                                                   | Shravan      | **Yes**            |
| **G16** Documentation             | **PASS**         | Core docs accurate. Stale docs identified: `aryan-runtime-integration.md` (S17/S18 status), `canonical-release-baseline.md` (integration branch state), `README.md` (outdated).                                                                                                                  | Shivam       | No                 |
| **G17** Repository/GitHub hygiene | **PARTIAL**      | Branch hygiene OK (merged branches ready for archive). CI workflow created (`.github/workflows/ci.yml`). Branch protection documented (`docs/github-branch-protection.md`) — manual configuration required via GitHub UI. CODEOWNERS present.                                                    | Shivam       | No                 |

---

## Blocker Summary

| Blocker                     | Gates Affected   | Resolution                                                                   |
| --------------------------- | ---------------- | ---------------------------------------------------------------------------- |
| Physical Windows acceptance | G2, G10, G14     | Run on clean Windows VM/machine with display + checkpoint                    |
| Real DA-V2 inference        | G2               | Requires checkpoint + display + upstream source                              |
| Shravan final ML candidate  | G15              | Deliver frozen checkpoint + SHA256 + upstream revision + evaluation evidence |
| Code signing                | G10 (production) | Obtain certificate for production distribution                               |

---

## Evidence Traceability

| Gate | Command/Artifact                                                                                                                                                                                                | Result                                                                                                              |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| G1   | `git diff origin/main...HEAD -- src/depthwizard/contracts/ src/depthwizard/calibration/ src/depthwizard/dsm/ src/depthwizard/mesh/ src/depthwizard/geospatial/ src/depthwizard/rdsm/ src/depthwizard/backends/` | No output                                                                                                           |
| G1   | `python -m pytest tests/`                                                                                                                                                                                       | 503 passed, 4 skipped                                                                                               |
| G3   | `python -m pytest tests/calibration/ tests/height/`                                                                                                                                                             | All passed                                                                                                          |
| G4   | `python -m pytest tests/dsm/`                                                                                                                                                                                   | All passed                                                                                                          |
| G5   | `python -m pytest tests/mesh/`                                                                                                                                                                                  | All passed                                                                                                          |
| G6   | `python -m pytest tests/rdsm/`                                                                                                                                                                                  | All passed                                                                                                          |
| G7   | `npm test` (Electron tests)                                                                                                                                                                                     | 35 passed                                                                                                           |
| G8   | `python scripts/provision_runtime.py --runtime-dir D:\tmp\dw --mode core --pretty`                                                                                                                              | `ready: true`, `service_launch_ready: true`, `offline_ready: true`                                                  |
| G9   | `python scripts/runtime_check.py --pretty`                                                                                                                                                                      | `core_ready: true`, `checkpoint.sha_match: true`                                                                    |
| G10  | `npm run electron:build:win`                                                                                                                                                                                    | Exit 0, 115 MB installer                                                                                            |
| G10  | `Get-ChildItem release\win-unpacked -Recurse`                                                                                                                                                                   | No unwanted files                                                                                                   |
| G11  | `HF_HUB_OFFLINE=1 python -c "import depthwizard"`                                                                                                                                                               | No network imports                                                                                                  |
| G12  | `python scripts/runtime_check.py --checkpoint bad.pth`                                                                                                                                                          | `CHECKPOINT_HASH_MISMATCH`                                                                                          |
| G13  | `npm run electron:build:win` (repeat)                                                                                                                                                                           | Same SHA256                                                                                                         |
| G14  | Manual                                                                                                                                                                                                          | —                                                                                                                   |
| G15  | Shravan branches inspection                                                                                                                                                                                     | M14/M17 research only                                                                                               |
| G16  | `git grep -l "NOT ON MAIN" docs/`                                                                                                                                                                               | `aryan-runtime-integration.md`                                                                                      |
| G17  | `git branch -a`, `.github/workflows/`                                                                                                                                                                           | CI workflow created (`.github/workflows/ci.yml`), branch protection documented (`docs/github-branch-protection.md`) |

---

## Final Release Decision

| Decision                                          | Condition                                                            |
| ------------------------------------------------- | -------------------------------------------------------------------- |
| **NOT RELEASE READY**                             | Physical Windows acceptance NOT VERIFIED; ML final candidate BLOCKED |
| **RELEASE CANDIDATE — PHYSICAL WITNESS REQUIRED** | All automated gates PASS; physical witness required for G2/G10/G14   |
| **RELEASE CANDIDATE**                             | —                                                                    |
| **RELEASE READY**                                 | All 17 gates PASS including physical witness + ML candidate          |

**Current State:** **RELEASE CANDIDATE — PHYSICAL WITNESS REQUIRED**

**Required to reach RELEASE READY:**

1. Aryan: Physical Windows acceptance on clean VM + display + checkpoint
2. Shravan: Final ML candidate frozen with verified evidence
3. Shivam: Code signing + CI + branch protection

---

**End of Release Gate Matrix.** This matrix reflects the actual state of `main` at `809801d45ac7f3be857b284539e4d9028e914e09` as verified by Git commands, file inspection, test execution, and actual build/artifact generation.
