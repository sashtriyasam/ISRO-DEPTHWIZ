# Final System Acceptance — DepthWizard (SIH 26175)

**Audit Date:** 2026-09-06
**Auditor:** Shivam (Architecture + Release Authority)
**Main:** `809801d45ac7f3be857b284539e4d9028e914e09`
**Source of truth:** actual code, actual tests, actual commands. No fabricated evidence.

---

## 1. PATH A — PNG/JPG → relative depth → rDSM → 3D terrain/flythrough

| Step                                                 | Implementation                                                                                     | Evidence                                                                                                              | Status                              |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| PNG/JPG input + validation                           | `depthwizard.ingestion` (`InputInspection`, checksum, format)                                      | `tests/ingestion/test_supported.py`, `test_invalid.py`, `test_integrity.py` — PASS (503-test suite)                   | PASS                                |
| Relative depth (DA-V2 Small, frozen)                 | `DepthAnythingV2Backend.estimate_depth()` → `DepthResult` (`is_metric` never True, `units=None`)   | `src/depthwizard/backends/depth_anything_v2.py:20`, `tests/backends/test_depth_anything_v2.py` — PASS                 | PASS                                |
| rDSM product                                         | `RelativeSurfaceGrid` (LOCAL frame, units absent)                                                  | `tests/rdsm/` — PASS                                                                                                  | PASS                                |
| Relative terrain mesh                                | `RelativeTerrainMesh` (pixel-local, never exaggerated/shifted in source)                           | `src/depthwizard/mesh/models.py:52`, `tests/mesh/` — PASS                                                             | PASS                                |
| Desktop transport (no resampling/remesh/unit change) | `depthwizard.integration.adapt` (transparent adapter)                                              | `src/depthwizard/integration/adapt.py:5`, `tests/integration/` — PASS                                                 | PASS                                |
| Renderer + flythrough (display-only exaggeration)    | Three.js scene, waypoint flythrough, `applyHeightExaggeration` returns new array, source immutable | `src/display/immutability.test.ts`, `src/transport/endToEnd.test.ts` (unit parts), `src/camera/*`, `src/flythrough/*` | PASS (unit) / NOT VERIFIED (visual) |

**PATH A verdict:** PASS (contract + unit). Visual renderer confirmation requires physical display (NOT VERIFIED).

## 2. PATH B — GeoTIFF → relative depth → explicit calibration → metric DSM → 3D terrain/flythrough

| Step                                    | Implementation                                                              | Evidence                                          | Status |
| --------------------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------- | ------ |
| GeoTIFF input (CRS/transform preserved) | `InputInspection` + `depthwizard.geospatial` validators                     | `tests/ingestion/`, `tests/geospatial/` — PASS    | PASS   |
| Relative depth (still relative)         | Same `DepthAnythingV2Backend` (no metric shortcut)                          | `tests/backends/test_depth_anything_v2.py` — PASS | PASS   |
| DEM/GCP reference + controls            | `depthwizard.dem`, `depthwizard.controls`                                   | `tests/dem/`, `tests/controls/` — PASS            | PASS   |
| Explicit calibration                    | `ScaleOffsetCalibrator` → `CalibrationResult` (method + units + provenance) | `tests/calibration/` — PASS                       | PASS   |
| Metric height product                   | `ScientificHeightProduct` (AGL / absolute, metres)                          | `tests/height/` — PASS                            | PASS   |
| Metric DSM                              | `DSMGrid` (metres, nodata=NaN, CRS preserved)                               | `tests/dsm/`, `tests/export/` — PASS              | PASS   |
| Terrain mesh (metric)                   | `TerrainMesh` (preserved coordinates)                                       | `tests/mesh/` — PASS                              | PASS   |
| End-to-end pipeline                     | `PipelineRunner` full + path variants                                       | `tests/pipeline/`, `tests/service/` — PASS        | PASS   |

**PATH B verdict:** PASS (contract + unit). Real calibrated-metric end-to-end (GCP/DEM + real DA-V2 + physical witness) NOT VERIFIED.

## 3. Metadata / provenance

| Check                     | Evidence                                                                   | Status                                                                 |
| ------------------------- | -------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| Input checksum linkage    | `InputInspection` SHA-256, repeat-inspection equivalence                   | PASS (`tests/ingestion/test_integrity.py`)                             |
| Model identity separation | checkpoint SHA-256 vs upstream revision vs license kept as separate fields | PASS (`tests/backends/test_depth_anything_v2.py`, runtime diagnostics) |
| Calibration provenance    | `CalibrationResult` records method + reference + validity                  | PASS (`tests/calibration/test_provenance.py`)                          |
| Product provenance        | height/DSM/mesh carry source + calibration linkage                         | PASS (`tests/height/test_provenance.py`)                               |

## 4. Runtime / packaging

| Check                           | Evidence                                                                                        | Status                                                      |
| ------------------------------- | ----------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Managed runtime                 | `scripts/provision_runtime.py` (venv, pinned DA-V2 source, SHA-verified checkpoint, idempotent) | PASS (verified `ready:true`, `reused:true` on rerun)        |
| Runtime diagnostics             | `scripts/runtime_check.py` (JSON, exit 0/1/2, no downloads)                                     | PASS (verified `healthy:true`, checkpoint `sha_match:true`) |
| Service launch                  | `scripts/depthwiz_service.py` stdio wire contract                                               | PASS (capabilities verified)                                |
| Native host                     | Electron 44.2.0 main/preload, 8 IPC methods, sender validation                                  | PASS (config + 35 Electron tests per acceptance record)     |
| Installer build                 | `npm run electron:build:win` → NSIS 115,174,663 bytes                                           | PASS (build)                                                |
| Packaged contents               | `resources/scripts/{depthwiz_service,backend_bridge}.py` via asarUnpack + extraResources        | PASS (verified in `release/win-unpacked`)                   |
| Install/launch on clean machine | Requires physical Windows witness                                                               | NOT VERIFIED                                                |

## 5. Error handling

| Check                           | Evidence                                            | Status                                                                         |
| ------------------------------- | --------------------------------------------------- | ------------------------------------------------------------------------------ |
| Unknown backend rejected loudly | `LocalService` rejects; synthetic never substituted | PASS (`tests/service/test_safety.py`, `tests/integration/test_dav2_bridge.py`) |
| Missing checkpoint              | `CHECKPOINT_MISSING`, DA-V2 unregistered            | PASS (runtime tests + service tests)                                           |
| Invalid checkpoint              | `CHECKPOINT_HASH_MISMATCH`, quarantine `.invalid`   | PASS (verified bad-checkpoint rejection)                                       |
| Unsupported format              | `UnsupportedFormat` vs `InvalidInput` distinction   | PASS (`tests/ingestion/test_unsupported.py`)                                   |
| CLI misuse                      | exit 2 (argparse)                                   | PASS                                                                           |

## 6. Offline operation

| Check                             | Evidence                                                                                        | Status                      |
| --------------------------------- | ----------------------------------------------------------------------------------------------- | --------------------------- |
| No network imports in engine      | `tests/runtime/test_packaging.py::test_no_network_imports_in_runtime`                           | PASS                        |
| `HF_HUB_OFFLINE=1` inference path | Real-inference smoke is opt-in (`tests/backends/test_depth_anything_v2.py::TestRealModelSmoke`) | NOT VERIFIED (assets-gated) |
| Provisioned runtime offline       | venv + local checkpoint; no downloads at import/test                                            | PASS (design + tests)       |

## 7. Renderer behavior

| Check                                 | Evidence                                                                         | Status                                                                       |
| ------------------------------------- | -------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Height exaggeration display-only      | `applyHeightExaggeration` returns new array; source mesh/grid/metadata unchanged | PASS (`src/display/immutability.test.ts`, `src/backend/meshAdapter.test.ts`) |
| Measurement uses scientific elevation | vertical/horizontal differences independent of exaggeration                      | PASS (`src/measurement/calculator.test.ts`)                                  |
| Visual confirmation (real display)    | Requires physical display + real artifact                                        | NOT VERIFIED                                                                 |

---

## Verdict

**FINAL SYSTEM ACCEPTANCE: PASS (contract + unit + build) / NOT VERIFIED (physical visual + real-asset end-to-end).**

Engineering validation is complete. Scientific accuracy claims remain bounded by the GAMUS evidence caveat (MAE 4.40 m / RMSE 5.86 m / R² 0.23 — pipeline-valid, honestly poor in absolute terms; a research signal, not SIH validation).
