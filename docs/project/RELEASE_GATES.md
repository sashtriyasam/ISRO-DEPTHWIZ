# DepthWizard — Release Gates

A gate passes only when its prerequisites are met **with recorded evidence**. Gate issues carry `Release Gate = Yes` in the Project. All release gates carry final authorization under **Shivam**.

## GATE 1 — Engineering Foundation (Shivam)

- Prerequisites: repo layout, `pyproject` (pytest/ruff/mypy), TS tooling (`typecheck`/`test`/`build`), `.gitignore` data rules.
- Verification: unit. Evidence: clean `pytest` (549 passed), `Vitest` (627 passed), `ruff` check/format, `tsc --noEmit` (0 errors).
- Status: **Done** (Foundation merged on main; CI enforcement active).

## GATE 2 — Input & Geospatial Correctness (Shivam)

- Prerequisites: ingestion + semantic validation, Path A/B routing, CRS/transform validators, overlap/alignment/reprojection, reference raster handling.
- Verification: unit + integration. Evidence: ingestion/geospatial test suites green; invalid-input rejection demonstrated.
- Status: **Done** (Merged on main; Path A non-georeferenced & Path B GeoTIFF routing verified).

## GATE 3 — Depth Runtime (Shravan + Shivam boundary)

- Prerequisites: `DepthBackend` interface, DA-V2 Small integration, deterministic inference, provenance (checkpoint hash `715FADE1...` + upstream revision `a561b849` + license separated from runtime record).
- Verification: runtime + integration. Evidence: `test_dav2_bridge.py` 4/4 passed; real DA-V2 desktop path test green.
- Status: **Done** (DA-V2 Small locked as canonical shipped model; M17 frozen in research track).

## GATE 4 — Calibration / Reference Validity (Shivam)

- Prerequisites: relative→metric mapping, DEM/GCP ingestion, reference controls, calibration quality checks, metric validity rules (no calibration ⇒ no metric claim).
- Verification: scientific + integration. Evidence: `test_calibration.py` green; quality-check rejection of uncalibrated metric requests.
- Status: **Done** (ScaleOffsetCalibrator with DEM 30m and GCP controls merged on main).

## GATE 5 — DSM / rDSM Product Correctness (Shivam)

- Prerequisites: DSM/rDSM construction, height semantics, nodata handling, standard GeoTIFF export with CRS/transform/provenance.
- Verification: unit + integration + scientific. Evidence: dsm/rdsm/height/export test suites green; exported product opens in standard GIS.
- Status: **Done** (Path A relative rDSM and Path B metric DSM with GeoTIFF export merged on main).

## GATE 6 — Mesh + Texture (Shivam + Aryan)

- Prerequisites: renderer-independent terrain mesh with preserved coordinates; UVs + source identity; viewer-side RGB projection.
- Verification: integration + visual. Evidence: `TerrainMesh` test suite green; textured Three.js scene verified.
- Status: **Done** (Mesh generation & optical RGB texture projection merged on main).

## GATE 7 — Interactive 3D (Aryan)

- Prerequisites: orbit / first-person / aerial navigation, waypoint flythrough, height/slope/measurement/profile tools, session lifecycle, layers.
- Verification: visual + runtime. Evidence: 627 Vitest UI tests green; Orbit, First-Person aerial camera, Waypoint flythrough player, slope degree grid, and point height inspector verified.
- Status: **Done** (React 19 + Three.js 0.177 3D renderer and camera system merged on main).

## GATE 8 — Scientific Validation (Shravan + Shivam)

- Prerequisites: benchmark framework, real-data evaluation, RMSE/MAE/correlation/stability recorded, significance where claimed.
- Verification: scientific. Evidence: Automated evaluation harness (`src/depthwizard/evaluation/`); scientific limitations and research vs product boundary documented in `RESEARCH_VS_PRODUCT.md`.
- Status: **Done (RC Baseline)** (Shipped model DA-V2 Small locked; scientific caveats and relative vs metric boundaries strictly documented).

## GATE 9 — End-to-End Integration (Shivam + Aryan)

- Prerequisites: canonical adapter + transport + local service + desktop consumption running the full pipeline both paths.
- Verification: end-to-end + runtime. Evidence: `test_dav2_bridge.py` & `realDav2Acceptance.test.ts` green on main; full Path A (relative rDSM) and Path B (metric DSM) runs verified.
- Status: **Done** (End-to-end pipeline IPC relay and local service execution verified).

## GATE 10 — Standalone Deployment (Aryan + Shivam)

- Prerequisites: reproducible runtime provisioning, native host, installer, fresh-machine startup with no dev-path dependency.
- Verification: end-to-end + runtime. Evidence: NSIS installer `DepthWizard Setup 1.0.0.exe` (115.5 MB) built; Authenticode signed with DigiCert RFC 3161 timestamp (`CN=DepthWizard Release Candidate`); SHA-256 `2A974B514694D79C0B7E72D6F17EE33B2B07A532CDD33207F9D34FFB3452D717`; 20/20 Physical Witness Trial items passed.
- Status: **Done** (Standalone signed Windows installer package and runtime provisioning fully verified).

## GATE 11 — Final SIH Acceptance (all; Shivam merge authority)

- Prerequisites: GATES 1–10 passed.
- Verification: all types. Evidence: All 20 physical witness trial items passed, 549 Python tests passed, 627 Vitest tests passed, TypeScript compiler clean, Authenticode signature verified, documentation reconciled.
- Status: **Done / Ready for Tagging** (Release Candidate `v0.1.0-sih-26175-rc1` ready to tag on main).
