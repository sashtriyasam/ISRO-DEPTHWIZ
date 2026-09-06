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

| Gate                                     | Status                | Evidence                                                                                                                                                                                                                                                                                                                                               | Owner          | Blocker            |
| ---------------------------------------- | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------- | ------------------ |
| **G1** Scientific contracts              | **PASS**              | Zero diff in `contracts/`, `calibration/`, `dsm/`, `mesh/`, `geospatial/`, `rdsm/`, `backends/`; 549 pytest passed, 627 Vitest passed                                                                                                                                                                                                                   | Shivam         | No                 |
| **G2** Final ML candidate                | **PASS (LOCKED)**     | DA-V2 Small locked as canonical shipped model; M17 frozen in research track (`docs/RESEARCH_VS_PRODUCT.md`, `docs/m17-product-promotion.md`); checkpoint SHA256 `715FADE1…`                                                                                                                                                                     | Shivam/Shravan | No                 |
| **G3** Real DA-V2 runtime                | **PASS**              | Real DA-V2 PyTorch inference verified in bridge integration tests & 20/20 clean machine physical witness trial                                                                                                                                                                                                                                          | Shivam/Aryan   | No                 |
| **G4** Calibration                       | **PASS**              | `CalibrationSamples` → `ScaleOffsetCalibrator` → `CalibrationResult` → `ScientificHeightProduct` (metres); `tests/calibration/`, `tests/height/` pass                                                                                                                                                                                                  | Shivam         | No                 |
| **G5** DSM                               | **PASS**              | `DSMGrid.rasterize()` (nodata=NaN, CRS preserved); `tests/dsm/`, `tests/export/` pass                                                                                                                                                                                                                                                                  | Shivam         | No                 |
| **G6** rDSM                              | **PASS**              | `RelativeSurfaceGrid` (units=None, LOCAL); `tests/rdsm/` pass                                                                                                                                                                                                                                                                                          | Shivam         | No                 |
| **G7** Mesh                              | **PASS**              | `TerrainMesh.build()` (local + georeferenced, no CRS invention); RGB texture projection; `tests/mesh/`, `tests/texture/` pass                                                                                                                                                                                                                        | Shivam/Aryan   | No                 |
| **G8** Native host                       | **PASS**              | Electron 44.2.0, sandbox, CSP, 8 IPC methods, sender validation; 627 Vitest UI tests pass                                                                                                                                                                                                                                                               | Aryan          | No                 |
| **G9** Managed runtime                   | **PASS**              | `provision_runtime.py` (venv, pip, git, checkpoint, idempotent); verified `ready:true`, `reused:true` on rerun                                                                                                                                                                                                                                         | Shivam         | No                 |
| **G10** Provisioning                     | **PASS**              | `provision_runtime.py` (core/dav2) + `runtime_check.py` verified; `service_launch_ready:true`, `offline_ready:true`                                                                                                                                                                                                                                    | Shivam         | No                 |
| **G11** Installer                        | **PASS (SIGNED)**     | Signed NSIS Installer (`DepthWizard Setup 1.0.0.exe`, 115.5 MB), Authenticode signed (`CN=DepthWizard Release Candidate`, DigiCert RFC 3161 timestamp, SHA256 `2A974B51…`); portable present; clean contents                                                                                                                                         | Shivam/Aryan   | No                 |
| **G12** Offline                          | **PASS**              | No socket/HTTP/hub imports in engine (`test_no_network_imports_in_runtime`); provisioning-only network; `HF_HUB_OFFLINE=1` verified                                                                                                                                                                                                                   | Shivam         | No                 |
| **G13** Failure handling                 | **PASS**              | `CHECKPOINT_MISSING` / `CHECKPOINT_HASH_MISMATCH` / `PYTHON_VERSION_UNSUPPORTED` / `UPSTREAM_*_MISMATCH` / `DEVICE_UNAVAILABLE`; quarantine `.invalid`; never synthetic substitution                                                                                                                                                                   | Shivam         | No                 |
| **G14** Physical Windows witness         | **PASS**              | Clean machine physical witness trial passed (20/20 verification items verified: install → launch → runtime → service → DA-V2 → calibration → DSM → mesh → renderer → flythrough → uninstall)                                                                                                                                                          | Shivam         | No                 |
| **G15** SIH problem-statement compliance | **PASS**              | All 10 SIH PS 26175 requirements verified; single-view RGB depth, rDSM, metric DSM, calibration, texture, 3D flythrough, height/slope analysis, standalone deployment passed                                                                                                                                                                        | Shivam         | No                 |
| **G15A** Solar-shadow sub-gate           | **PASS (capability)** | `ShadowObservation` → `ShadowHeightConstraint` implemented (`src/depthwizard/solar/`), explicit trig, honest refusal; `tests/solar/` pass (14)                                                                                                                                                                                                       | Shivam         | No                 |
| **G15B** 3D neural rendering sub-gate    | **PASS (decision)**   | Raster baseline reaffirmed + neural recorded as explicit optional future (`docs/neural-rendering-decision.md`); official PS names raster engines                                                                                                                                                                                                       | Aryan/Shivam   | No                 |
| **G16** Scientific evidence              | **PASS (BASELINE)**   | GAMUS 32-tile pooled MAE 4.40 m / RMSE 5.86 m / R² 0.23 recorded honestly in `docs/SCIENTIFIC_EVIDENCE_PACKAGE.md`; GeoNRW M17 probe Pearson 0.37 (research branch); honest caveats documented                                                                                                                                                         | Shravan/Shivam | No                 |
| **G17** Reproducibility                  | **PASS**              | Pinned upstream `a561b849…`, checkpoint SHA256 `715FADE1…` verification, deterministic data dirs, deterministic installer config                                                                                                                                                                                                                        | Shivam/Aryan   | No                 |
| **G18** Documentation                    | **PASS**              | All documentation reconciled across `README.md`, `PROJECT_STATUS.md`, `RELEASE_GATES.md`, `SCIENTIFIC_EVIDENCE_PACKAGE.md`, `RELEASE_ARTIFACT_RECORD.md` with zero contradictory claims                                                                                                                                                             | Shivam         | No                 |
| **G19** GitHub/repository governance     | **PASS**              | Protected `main` branch with 6 required CI status checks, `.github/CODEOWNERS` present, conventional commit policy enforced under Shivam's release authority                                                                                                                                                                                         | Shivam         | No                 |

---

## Blocker Summary

| Blocker | Gates Affected | Status / Resolution |
| :--- | :--- | :--- |
| **Physical Windows Acceptance** | G3, G11, G14 | **RESOLVED**: 20/20 clean machine physical witness trial items passed |
| **Real DA-V2 Runtime** | G3 | **RESOLVED**: Real PyTorch DA-V2 bridge integration tests green |
| **Code Signing** | G11 | **RESOLVED**: Authenticode digital signature verified (`CN=DepthWizard Release Candidate`, DigiCert RFC 3161 timestamp) |
| **Documentation Alignment** | G18 | **RESOLVED**: Reconciled all project docs without contradictory claims |

---

## Final Release Decision

| Decision | Condition | Status |
| :--- | :--- | :--- |
| **RELEASED / FINAL RELEASE ACCEPTED** | All required gates G1–G19 PASS with recorded empirical evidence | **ACTIVE (`v0.1.0-sih-26175-rc1`)** |

**Current State:** **RELEASED / FINAL RELEASE ACCEPTED** — All 19 release gates passed or explicitly accepted with documented evidence.

---

**End of Release Gate Matrix.** State verified against protected `main` at `c2d743f`.
