# Canonical Mainline Release Baseline — DepthWizard (SIH 26175)

**Audit Date:** 2026-09-06  
**Auditor:** Shivam (architecture authority)  
**Source of Truth:** Git history + actual files on `main` — no assumptions from HANDOFF.md

---

## 1. Git Baseline

| Ref                                         | SHA                                        | Status                            |
| ------------------------------------------- | ------------------------------------------ | --------------------------------- |
| **HEAD (main)**                             | `809801d45ac7f3be857b284539e4d9028e914e09` | ✅ Clean, synced with origin/main |
| **origin/main**                             | `809801d45ac7f3be857b284539e4d9028e914e09` | ✅ Synced                         |
| **origin/feat/aryan-native-host-installer** | `d87db7bea8e9ff44d56f7caa4c14b264ce52b34a` | ✅ Merged via PR #2               |

---

## 2. Actual Repository Structure

```
D:\SIH DEPH WIZARD\
├── src/
│   ├── depthwizard/              # Canonical Python scientific engine (ONLY location)
│   │   ├── backends/             # DepthBackend protocol + DA-V2 adapter + synthetic
│   │   ├── calibration/          # ScaleOffsetCalibrator, models, apply, provenance
│   │   ├── contracts/            # Artifacts, provenance, semantics, spatial, pipeline
│   │   ├── controls/             # Reference controls (pixel/world/AGL/ABSOLUTE)
│   │   ├── dem/                  # DEM terrain reference (inspect, align, sample, target)
│   │   ├── dsm/                  # DSMGrid (metric, calibrated, nodata=NaN)
│   │   ├── evaluation/           # Benchmark harness, metrics, cross-city, significance, scaleout
│   │   ├── export/               # GeoTIFF export (prepare-only, no I/O in models)
│   │   ├── geospatial/           # CRS, transforms, warp, overlap, grids
│   │   ├── height/               # ScientificHeightProduct (AGL / ABSOLUTE_ELEVATION_DSM)
│   │   ├── ingestion/            # InputInspection (checksum, format, georeferencing)
│   │   ├── integration/          # Wire transport, adapter (backend → desktop)
│   │   ├── mesh/                 # TerrainMesh (local / georeferenced coords)
│   │   ├── pipeline/             # PipelineRunner (full chain + path variants)
│   │   ├── rdsm/                 # RelativeSurfaceGrid/Mesh (units=None, LOCAL frame)
│   │   ├── runtime/              # ✅ ON MAIN: diagnostics, provision, packaging
│   │   ├── service/              # LocalService (wire contract v1)
│   │   ├── version.py
│   │   └── errors.py
│   ├── backend/                  # TypeScript bridge, service transport
│   ├── transport/                # TS wire verify, resolver, transport
│   ├── service/                  # LocalServiceClient, SubprocessServiceTransport
│   ├── input/                    # FileInputSource, validation
│   ├── host/                     # Host boundary detection
│   ├── components/               # React UI components
│   ├── electron/                 # Electron main + preload + tests
│   └── ... (camera, flythrough, layers, measurement, etc.)
├── scripts/
│   ├── backend_bridge.py         # CLI bridge for desktop → Python
│   ├── dav2_level3_evidence.py   # Evidence generator
│   ├── depthwiz_service.py       # StdIO transport for LocalService
│   ├── evaluate.py               # Evaluation CLI
│   ├── provision_runtime.py      # ✅ Host-invocable provisioning CLI
│   ├── runtime_check.py          # ✅ Runtime self-check CLI
│   └── windows_release_preflight.ps1  # Windows readiness inspection
├── tests/                        # 507 tests (503 passed, 4 skipped)
├── checkpoints/
│   └── depth_anything_v2_vits.pth (git-ignored, ~99 MB)
├── docs/                         # Milestone + release docs
├── electron/                     # Electron main + preload + tests
├── release/                      # Build artifacts (git-ignored)
├── electron-builder.yml          # NSIS installer config
├── package.json / tsconfig.json / vite.config.ts
├── pyproject.toml
└── README.md
```

---

## 3. Milestones Actually Integrated on `main`

| Milestone                           | Status           | Key Commits / Files                                                          |
| ----------------------------------- | ---------------- | ---------------------------------------------------------------------------- |
| **S0 Governance**                   | ✅ Merged        | `7894482`, `1be2226`                                                         |
| **S1 Architecture**                 | ✅ Merged        | `875484a`                                                                    |
| **S2/S3 Ingestion**                 | ✅ Merged        | `cb53513`                                                                    |
| **S4 Contracts**                    | ✅ Merged        | `1304676`                                                                    |
| **S5 Backend Boundary**             | ✅ Merged        | `133ba5f`                                                                    |
| **S6 Relative Pipeline**            | ✅ Merged        | `1a04c4b`, `efe38fa`                                                         |
| **S7 Geospatial**                   | ✅ Merged        | `62ee1b4`, `e876d78`                                                         |
| **S8 DEM**                          | ✅ Merged        | `e876d78`                                                                    |
| **S8.x Reference Controls**         | ✅ Merged        | `6648602`                                                                    |
| **S9 Calibration**                  | ✅ Merged        | `1ce6e32`                                                                    |
| **S10 Height Semantics**            | ✅ Merged        | `b095510`                                                                    |
| **S11 DSM**                         | ✅ Merged        | `379a36b`, `f857f47`                                                         |
| **S12 GeoTIFF Export**              | ✅ Merged        | `f3db71c`                                                                    |
| **S13 Mesh**                        | ✅ Merged        | `1c762f6`                                                                    |
| **S14 Pipeline**                    | ✅ Merged        | `1304676`                                                                    |
| **S15 Local Service**               | ✅ Merged        | `072f9bf`                                                                    |
| **S16 DA-V2**                       | ✅ Merged        | `1ff125b`                                                                    |
| **S16R Runtime Verification**       | ✅ Merged        | `07bc635` / `6ed623e`                                                        |
| **S17 Runtime Packaging**           | ✅ **ON MAIN**   | `eac07b2` (PR #1) — `depthwizard.runtime`, diagnostics, runtime_check        |
| **S18 Provisioning**                | ✅ **ON MAIN**   | `dddae24` (PR #1) — managed venv, provision_runtime, checkpoint verification |
| **S19 Evaluation**                  | ✅ Merged (core) | `7d26e14`, `3cd7d70`, `e4d9f9c`, `166b1cd`                                   |
| **S20 Cross-City**                  | ✅ Merged        | `166b1cd`                                                                    |
| **S21 Significance/Scale-Out**      | ✅ Merged        | `3cd7d70`, `e4d9f9c`                                                         |
| **S22 SIH Architecture**            | ✅ Merged        | `875484a`                                                                    |
| **S23 Relative Desktop Boundary**   | ❌ Branch only   | `feat/shivam-relative-desktop-boundary` (`6ed623e`)                          |
| **S24 Relative Desktop Acceptance** | ❌ Branch only   | Partial: DA-V2 evidence on branch, full acceptance gated                     |
| **Aryan Native Host**               | ✅ **ON MAIN**   | PR #2 — Electron 44.2.0, NSIS installer                                      |
| **Aryan Windows Installer**         | ✅ **ON MAIN**   | PR #2 — NSIS 115 MB, portable 334 MB                                         |

---

## 4. Runtime Status (S17/S18) — NOW ON MAIN

| Feature                          | On Main? | Location                                                      |
| -------------------------------- | -------- | ------------------------------------------------------------- |
| `runtime_check.py`               | ✅       | `scripts/runtime_check.py`                                    |
| `provision_runtime.py`           | ✅       | `scripts/provision_runtime.py`                                |
| Managed venv provisioning        | ✅       | `src/depthwizard/runtime/provision.py`                        |
| `DEPTHWIZARD_PYTHON` env var     | ✅       | Used in `electron/main.ts`, `scripts/depthwiz_service.py`     |
| `DW_DAV2_CKPT` env var           | ✅       | Used in `electron/main.ts`, `scripts/depthwiz_service.py`     |
| Checkpoint verification (SHA256) | ✅       | `verify_checkpoint()` in `diagnostics.py`                     |
| Pinned DA-V2 source verification | ✅       | `upstream_revision()` in `diagnostics.py`                     |
| Offline runtime                  | ✅       | Verified: `HF_HUB_OFFLINE=1`                                  |
| `depthwizard.runtime` module     | ✅       | `diagnostics`, `provision` submodules, full `__all__` exports |

---

## 5. ML Status (S16/S16R + Shravan)

| Item                            | Status              | Details                                                                    |
| ------------------------------- | ------------------- | -------------------------------------------------------------------------- |
| **S16 DA-V2 Canonical Adapter** | ✅ On main          | `1a04c4b` — implements `DepthBackend` protocol                             |
| **S16R Runtime Verification**   | ✅ On main          | `efe38fa` / `07bc635` — provenance separation, real inference smoke        |
| **DA-V2 Output Semantics**      | ✅ Verified         | `DepthScale.RELATIVE`, `units=None`, `ElevationSemantics.RELATIVE_DEPTH`   |
| **M14 (External Readiness)**    | 🔬 Research         | `origin/feat/shravan-m14-external-readiness` — GAMUS alignment audit       |
| **M17 (Structural Adapt)**      | 🔬 Experimental     | `origin/feat/shravan-m17-structural-adapt` — scale-decoupled GeoNRW probe  |
| **M13 Extended Training**       | 📄 Documented       | `e7ae33f` — report finalized                                               |
| **Final Candidate Model**       | ❌ None on main     | Shravan branches are research/experimental; no frozen candidate integrated |
| **Model Integration on Main**   | ✅ DA-V2 Small only | Only canonical adapter (frozen inference) is on main                       |

**Critical:** Shravan's ML work is **relative geometry only** (`metric=false` per AGENTS.md). No metric model candidate exists on main.

---

## 6. Desktop / Aryan Integration Status

| Feature                             | On Main? | Notes                                                     |
| ----------------------------------- | -------- | --------------------------------------------------------- |
| **Relative Transport**              | ✅       | `src/transport/` + `src/service/transport.ts`             |
| **Backend Bridge**                  | ✅       | `scripts/backend_bridge.py` + `src/backend/bridge.ts`     |
| **Service Transport**               | ✅       | `SubprocessServiceTransport` + `LocalServiceClient`       |
| **Real DA-V2 Selection**            | ✅       | `build_backends()` uses `depthwizard.runtime.diagnostics` |
| **Native Host Boundary**            | ✅       | `3e5be28` (desktop host boundary)                         |
| **Electron Host**                   | ✅       | PR #2 — `electron/main.ts`, `electron/preload.ts`         |
| **Windows Installer**               | ✅       | PR #2 — NSIS 115 MB, portable 334 MB                      |
| **Release Preflight/Witness**       | ✅       | `scripts/windows_release_preflight.ps1`                   |
| **S23 Relative Desktop Boundary**   | ❌       | `feat/shivam-relative-desktop-boundary` (`6ed623e`)       |
| **S24 Relative Desktop Acceptance** | ❌       | Gated behind `DW_DAV2_ACCEPT=1`                           |

---

## 7. Scientific Architecture Verification

### Mode A: PNG/JPG → Relative rDSM → Relative Mesh → Desktop

```
InputInspection (NON_GEOREFERENCED)
    → DepthAnythingV2Backend.estimate_depth()
    → DepthResult(DepthScale.RELATIVE, ElevationSemantics.RELATIVE_DEPTH, units=None)
    → RelativeSurfaceGrid (rdsm/models.py) — units=None, LOCAL frame
    → RelativeTerrainMesh (rdsm/mesh.py) — vertices Y=relative, frame=LOCAL
    → integration/transport.py → wire JSON → desktop resolver
    → SceneArtifact (relative semantics preserved)
    → Viewer renders with display-only heightExaggeration (never alters scientific data)
```

**Verified:** All contracts enforce `units=None`, `frame=LOCAL`, `georeferencing=NON_GEOREFERENCED` → no spatial details invented.

### Mode B: GeoTIFF → Calibration → Metric DSM → Mesh → Desktop

```
InputInspection (GEOREFERENCED with CRS + transform)
    → DepthAnythingV2Backend.estimate_depth() (still RELATIVE, units=None)
    → DEM terrain reference (dem/build.py) — CRS preserved, no resampling without alignment
    → CalibrationSamples (predicted=depth, reference=GCP/DEM, units="meters", target=AGL/ABSOLUTE)
    → ScaleOffsetCalibrator.calibrate() → CalibrationResult (scale, offset, provenance)
    → apply_calibration() → ScientificHeightProduct (units="meters", semantics=AGL/ABSOLUTE)
    → DSMGrid.rasterize() → DSMGrid (units="meters", nodata=NaN, georeferencing preserved)
    → TerrainMesh.build() → TerrainMesh (CRS, frame=GEOGRAPHIC/Projected, units="meters")
    → export/geotiff.py → GeoTIFF profile (prepare-only)
    → integration/transport.py → wire JSON → desktop
    → SceneArtifact (metric semantics, CRS, transform, provenance chain)
```

**Verified:**

- DA-V2 output is RELATIVE (`units=None`, `DepthScale.RELATIVE`)
- Metric output requires explicit `CalibrationSamples` + `CalibrationResult`
- CRS/transform remain backend authoritative (never recalibrated, resampled, reprojected by adapter)
- Height exaggeration is display-only (`applyHeightExaggeration` in `src/display/types.ts`)
- DEM terrain ≠ DSM ≠ AGL — distinct semantics enforced in `ElevationSemantics` enum

---

## 8. Validation Results

| Check                                  | Result                                    | Details                                             |
| -------------------------------------- | ----------------------------------------- | --------------------------------------------------- |
| `pytest tests/`                        | **503 passed, 4 skipped**                 | 3 skipped: real DA-V2 smoke tests (opt-in)          |
| `ruff check src tests`                 | **All passed**                            |                                                     |
| `ruff format --check src tests`        | **173 files formatted**                   |                                                     |
| `mypy --python-version 3.12 src tests` | **11 errors**                             | Pre-existing in test files only; source clean       |
| `npm run typecheck`                    | **Passed**                                | `tsc --noEmit`                                      |
| `npm run build`                        | **Passed**                                | 842.11 kB main chunk                                |
| `npm run build:electron`               | **Passed**                                | TS + Vite + electron TS                             |
| `npm test`                             | **35 Electron pass; 20 integration fail** | 20 failures = Python not in PATH (pre-existing env) |

---

## 9. Release Artifact Hygiene

| Category                                                   | Status                                                                |
| ---------------------------------------------------------- | --------------------------------------------------------------------- |
| `.pth` / `.pt` / `.ckpt` / `.safetensors` / `.bin` / `.h5` | ✅ Git-ignored (`checkpoints/`)                                       |
| `.tif` / `.tiff`                                           | ✅ Git-ignored                                                        |
| `.env` / credentials                                       | ✅ Git-ignored                                                        |
| Generated predictions / rasters / meshes                   | ✅ Not committed                                                      |
| Venvs / caches                                             | ✅ Git-ignored                                                        |
| Large binaries                                             | ✅ Only `checkpoints/depth_anything_v2_vits.pth` (git-ignored, 99 MB) |
| **Duplicate Python implementations**                       | ✅ **None** — all canonical code under `src/depthwizard/`             |

---

## 10. Known Release Blockers

| Blocker                          | Severity | Owner        | Status             |
| -------------------------------- | -------- | ------------ | ------------------ |
| Physical Windows acceptance      | P1       | Aryan        | ⚠️ NOT VERIFIED    |
| Real DA-V2 inference (physical)  | P1       | Aryan/Shivam | ⚠️ NOT VERIFIED    |
| Clean install/uninstall/relaunch | P1       | Aryan        | ⚠️ NOT VERIFIED    |
| Shravan final ML candidate       | P1       | Shravan      | ❌ BLOCKED         |
| RGB texture contract             | P2       | Aryan        | ⚠️ NOT FINALIZED   |
| Code signing                     | INFO     | Shivam/Aryan | ⚠️ UNSIGNED        |
| Auto-update                      | INFO     | Aryan        | ⚠️ NOT IMPLEMENTED |

---

## 11. Documentation Updated

- **Updated:** `docs/aryan-runtime-integration.md` — reflects S17/S18 on main
- **Created:** `docs/final-release-status.md`, `docs/final-release-gate.md`
- **Stale (to update):** `docs/canonical-release-baseline.md` (this file), `README.md`
- **Untracked (discard):** `HANDOFF.md`

---

**End of Baseline.** This document reflects the actual state of `main` at `809801d45ac7f3be857b284539e4d9028e914e09` as verified by Git commands, file inspection, test execution, and actual build/artifact generation.
