# Final Release Gate Matrix — DepthWizard (SIH 26175)

**Audit Date:** 2026-09-06
**Auditor:** Shivam (Architecture Authority + Release Owner)
**Source of Truth:** Actual Git history + actual files on `main` at `809801d45ac7f3be857b284539e4d9028e914e09`
**No assumptions — evidence only.**

---

## Release Gate Definitions

| Gate | Name                             | Description                                                          |
| ---- | -------------------------------- | -------------------------------------------------------------------- |
| G1   | Scientific contracts             | All scientific semantics, units, CRS, provenance contracts preserved |
| G2   | Final ML candidate               | Frozen model with verified checkpoint, metrics, provenance           |
| G3   | Real DA-V2 runtime               | End-to-end real model inference (assets-gated)                       |
| G4   | Calibration                      | Explicit calibration required for metric output                      |
| G5   | DSM                              | Metric DSMGrid with calibrated values, nodata=NaN                    |
| G6   | rDSM                             | Relative surface grid (units=None, LOCAL frame)                      |
| G7   | Mesh                             | TerrainMesh with local + georeferenced coordinates                   |
| G8   | Native host                      | Electron 44.2.0, sandbox, CSP, IPC bridge                            |
| G9   | Managed runtime                  | Isolated venv, provisioned via `provision_runtime.py`                |
| G10  | Provisioning                     | Host-invocable `provision_runtime.py` + `runtime_check.py`           |
| G11  | Installer                        | NSIS + portable, clean contents, extra resources                     |
| G12  | Offline                          | `HF_HUB_OFFLINE=1`, no network imports in engine                     |
| G13  | Failure handling                 | Structured codes, no silent fallback, quarantine                     |
| G14  | Physical Windows witness         | Actual install/launch on clean Windows + display                     |
| G15  | SIH problem-statement compliance | Requirements audit vs SIH PS 26175                                   |
| G16  | Scientific evidence              | GAMUS/GeoNRW evidence recorded with honest caveats                   |
| G17  | Reproducibility                  | Deterministic installer, pinned upstream, hash-verified              |
| G18  | Documentation                    | All docs accurate, no stale claims                                   |
| G19  | GitHub/repository governance     | Branch hygiene, CI, branch protection, CODEOWNERS                    |

---

## Gate Status Matrix

| Gate                                     | Status           | Evidence                                                                                                                                                                                                                                                                                                                                               | Owner          | Blocker            |
| ---------------------------------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------- | ------------------ |
| **G1** Scientific contracts              | **PASS**         | Zero diff in `contracts/`, `calibration/`, `dsm/`, `mesh/`, `geospatial/`, `rdsm/`, `backends/`; 503 pytest passed                                                                                                                                                                                                                                     | Shivam         | No                 |
| **G2** Final ML candidate                | **PARTIAL**      | M17 locked in research; decision doc ON MAIN via PR #3 (`docs/final-ml-candidate.md`); release branch `origin/feat/shravan-final-ml-release` @ `b920772` (ancestry repaired); checkpoint SHA256 `D7C0BE91…EDAC`, Pearson 0.37 probe; NOT promoted to product (main still canonical DA-V2 Small); promotion analysis in `docs/m17-product-promotion.md` | Shravan        | **Yes**            |
| **G3** Real DA-V2 runtime                | **NOT VERIFIED** | Requires checkpoint + upstream source + display; gated by `DW_DAV2_ACCEPT=1`; real-inference smoke tests skipped (4 skipped in suite)                                                                                                                                                                                                                  | Aryan/Shivam   | **Yes**            |
| **G4** Calibration                       | **PASS**         | `CalibrationSamples` → `ScaleOffsetCalibrator` → `CalibrationResult` → `ScientificHeightProduct` (metres); `tests/calibration/`, `tests/height/` pass                                                                                                                                                                                                  | Shivam         | No                 |
| **G5** DSM                               | **PASS**         | `DSMGrid.rasterize()` (nodata=NaN, CRS preserved); `tests/dsm/`, `tests/export/` pass                                                                                                                                                                                                                                                                  | Shivam         | No                 |
| **G6** rDSM                              | **PASS**         | `RelativeSurfaceGrid` (units=None, LOCAL); `tests/rdsm/` pass                                                                                                                                                                                                                                                                                          | Shivam         | No                 |
| **G7** Mesh                              | **PASS**         | `TerrainMesh.build()` (local + georeferenced, no CRS invention); `tests/mesh/` pass                                                                                                                                                                                                                                                                    | Shivam         | No                 |
| **G8** Native host                       | **PASS**         | Electron 44.2.0, sandbox, CSP, 8 IPC methods, sender validation; 35 Electron tests pass                                                                                                                                                                                                                                                                | Aryan          | No                 |
| **G9** Managed runtime                   | **PASS**         | `provision_runtime.py` (venv, pip, git, checkpoint, idempotent); verified `ready:true`, `reused:true` on rerun                                                                                                                                                                                                                                         | Shivam         | No                 |
| **G10** Provisioning                     | **PASS**         | `provision_runtime.py` (core/dav2) + `runtime_check.py` verified; `service_launch_ready:true`, `offline_ready:true`                                                                                                                                                                                                                                    | Shivam         | No                 |
| **G11** Installer                        | **PASS** (build) | NSIS 115,174,663 bytes (SHA256 `1DD0959C…C4A04`, build 2026-09-06), portable present; clean contents; `depthwiz_service.py` + `backend_bridge.py` via asarUnpack                                                                                                                                                                                       | Aryan          | **Yes** (physical) |
| **G12** Offline                          | **PASS**         | No socket/HTTP/hub imports in engine (`test_no_network_imports_in_runtime`); provisioning-only network                                                                                                                                                                                                                                                 | Shivam         | No                 |
| **G13** Failure handling                 | **PASS**         | `CHECKPOINT_MISSING` / `CHECKPOINT_HASH_MISMATCH` / `PYTHON_VERSION_UNSUPPORTED` / `UPSTREAM_*_MISMATCH` / `DEVICE_UNAVAILABLE`; quarantine `.invalid`; never synthetic substitution                                                                                                                                                                   | Shivam         | No                 |
| **G14** Physical Windows witness         | **NOT VERIFIED** | Requires clean Windows VM + display + checkpoint: install → launch → runtime → service → DA-V2 → calibration → DSM → mesh → renderer (see `docs/windows-release-acceptance.md`)                                                                                                                                                                        | Aryan          | **Yes**            |
| **G15** SIH problem-statement compliance | **PARTIAL**      | 5/9 PASS, 2/9 PARTIAL, 2/9 MISSING per `docs/sih-compliance-matrix.md`: solar shadow geometry/trigonometry MISSING; 3D neural rendering PARTIAL (rasterization, not NeRF/GS)                                                                                                                                                                           | Shivam         | **Yes**            |
| **G15A** Solar-shadow sub-gate           | **MISSING**      | Zero implementation in `src/` (verified search); gap filed in `docs/ps-solar-shadow-gap.md`; decision **C — MAJOR GAP, new R&D subsystem**                                                                                                                                                                                                             | Shivam         | **Yes**            |
| **G15B** 3D neural rendering sub-gate    | **MISSING**      | Zero implementation in `src/` (verified search); Three.js rasterization only; gap filed in `docs/ps-neural-rendering-gap.md`; decision **C — MAJOR GAP, new R&D subsystem**                                                                                                                                                                            | Aryan/Shivam   | **Yes**            |
| **G16** Scientific evidence              | **PARTIAL**      | GAMUS 32-tile pooled MAE 4.40 m / RMSE 5.86 m / R² 0.23 recorded honestly (research signal, not SIH validation); GeoNRW M17 probe Pearson 0.37 (research branch); SIH-wide accuracy unproven                                                                                                                                                           | Shravan/Shivam | **Yes**            |
| **G17** Reproducibility                  | **PASS**         | Pinned upstream `a561b849…`, checkpoint SHA256 verification, deterministic data dirs, deterministic installer config                                                                                                                                                                                                                                   | Shivam/Aryan   | No                 |
| **G18** Documentation                    | **PARTIAL**      | Core docs accurate; closure docs added (`m17-product-promotion`, `sih-authoritative-requirement-audit`, `ps-*-closure`, `sih-compliance-matrix`); `final-release-status.md` synced to G1–G19                                                                                                                                                           | Shivam         | No                 |
| **G19** GitHub/repository governance     | **PARTIAL**      | CI workflow present (`.github/workflows/ci.yml`, contract job enforced); `.github/CODEOWNERS` present; branch protection documented-manual; PR #3 merged; control PR pending; no tags; API unverifiable (401)                                                                                                                                          | Shivam         | No                 |

---

## Blocker Summary

| Blocker                                       | Gates Affected   | Resolution                                                                                                                                    |
| --------------------------------------------- | ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Physical Windows acceptance                   | G3, G11, G14     | Run `docs/windows-release-acceptance.md` on clean Windows VM + display + checkpoint                                                           |
| Real DA-V2 runtime                            | G3               | Checkpoint + display + upstream source (`DW_DAV2_ACCEPT=1`)                                                                                   |
| Final ML candidate promotion                  | G2               | Shravan: freeze M17 evidence; Shivam: promote via product path (no silent swap)                                                               |
| SIH compliance gaps (solar, neural rendering) | G15/G15A/G15B    | Gaps filed (`docs/ps-solar-shadow-gap.md`, `docs/ps-neural-rendering-gap.md`); decision C — implementation is a new program, not this closure |
| Code signing                                  | G11 (production) | Obtain EV certificate for production distribution                                                                                             |

---

## Evidence Traceability

| Gate | Command/Artifact                                                                                                                                                                                                                 | Result                                                                                 |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| G1   | `git diff main...HEAD -- src/depthwizard/contracts/ src/depthwizard/calibration/ src/depthwizard/dsm/ src/depthwizard/height/ src/depthwizard/mesh/ src/depthwizard/geospatial/ src/depthwizard/rdsm/ src/depthwizard/backends/` | No output                                                                              |
| G1   | `python -m pytest tests/ -q`                                                                                                                                                                                                     | 503 passed, 4 skipped                                                                  |
| G4   | `python -m pytest tests/calibration/ tests/height/ -q`                                                                                                                                                                           | All passed (in full suite)                                                             |
| G5   | `python -m pytest tests/dsm/ tests/export/ -q`                                                                                                                                                                                   | All passed (in full suite)                                                             |
| G6   | `python -m pytest tests/rdsm/ -q`                                                                                                                                                                                                | All passed (in full suite)                                                             |
| G7   | `python -m pytest tests/mesh/ -q`                                                                                                                                                                                                | All passed (in full suite)                                                             |
| G8   | `npm test` (Electron tests)                                                                                                                                                                                                      | 35 passed (per acceptance record; current run: 557 passed / 70 env-failed / 4 skipped) |
| G9   | `python scripts/provision_runtime.py --runtime-dir <dir> --mode core --pretty`                                                                                                                                                   | `ready:true`, `reused:true` on rerun                                                   |
| G10  | `python scripts/runtime_check.py --pretty`                                                                                                                                                                                       | `healthy:true`, `checkpoint.sha_match:true`                                            |
| G11  | `npm run electron:build:win`                                                                                                                                                                                                     | Exit 0, 115,174,663 bytes                                                              |
| G11  | `Get-ChildItem release\win-unpacked -Recurse`                                                                                                                                                                                    | No `.git`/`node_modules`/`src`/checkpoints/`.pth`/`.env`                               |
| G12  | `tests/runtime/test_packaging.py::test_no_network_imports_in_runtime`                                                                                                                                                            | PASS                                                                                   |
| G13  | `python scripts/runtime_check.py --checkpoint bad.pth --pretty`                                                                                                                                                                  | `CHECKPOINT_HASH_MISMATCH`, `healthy:false`                                            |
| G17  | `npm run electron:build:win` (repeat)                                                                                                                                                                                            | Same byte size; hash recorded per build                                                |
| G14  | Manual                                                                                                                                                                                                                           | — (procedure in `docs/windows-release-acceptance.md`)                                  |
| G2   | `git show origin/feat/shravan-final-ml-freeze:docs/research/final-ml-candidate.md`                                                                                                                                               | M17 locked in research, not on main                                                    |
| G15  | `docs/sih-compliance-matrix.md`                                                                                                                                                                                                  | 5 PASS / 2 PARTIAL / 2 MISSING                                                         |
| G18  | `git grep -l "NOT ON MAIN" docs/`                                                                                                                                                                                                | Only historical references remain                                                      |
| G19  | `git branch -a`, `.github/workflows/ci.yml`, `.github/CODEOWNERS`                                                                                                                                                                | CI + CODEOWNERS present; branch protection manual                                      |

---

## Final Release Decision

| Decision                                              | Condition                                                                         |
| ----------------------------------------------------- | --------------------------------------------------------------------------------- |
| **NOT RELEASE READY**                                 | Physical Windows acceptance NOT VERIFIED; ML candidate not promoted; PS gaps open |
| **RELEASE CANDIDATE — PHYSICAL WITNESS REQUIRED**     | All automated gates PASS; physical witness required                               |
| **RELEASE CANDIDATE — SCIENTIFIC CANDIDATE REQUIRED** | ML freeze/M17 promotion + SIH compliance program required                         |
| **RELEASE CANDIDATE**                                 | —                                                                                 |
| **READY FOR SHIVAM RELEASE AUTHORIZATION**            | All required gates have real evidence (not current state)                         |

**Current State:** **RELEASE CANDIDATE — PHYSICAL WITNESS REQUIRED** (with additional scientific-candidate requirement noted).

**Required to reach READY FOR SHIVAM RELEASE AUTHORIZATION:**

1. Aryan: Physical Windows acceptance on clean VM + display + checkpoint
2. Shravan: Final ML candidate evidence freeze + product-path promotion proposal
3. Shivam: Code signing decision + CI/branch-protection activation + PS-gap program scoping

---

**End of Release Gate Matrix.** State verified against `main` at `809801d45ac7f3be857b284539e4d9028e914e09` plus this control branch's additive changes.
