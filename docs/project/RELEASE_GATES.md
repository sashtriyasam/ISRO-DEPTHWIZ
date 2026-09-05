# DepthWizard — Release Gates

A gate passes only when its prerequisites are met **with recorded
evidence**. Gate issues carry `Release Gate = Yes` in the Project.

## GATE 1 — Engineering Foundation (Shivam)

- Prerequisites: repo layout, `pyproject` (pytest/ruff/mypy), TS
  tooling (`typecheck`/`test`/`build`), `.gitignore` data rules.
- Verification: unit. Evidence: clean `pytest`, `ruff`, `tsc --noEmit`.
- Status: **Done** (foundation merged on main).

## GATE 2 — Input & Geospatial Correctness (Shivam)

- Prerequisites: ingestion + semantic validation, Path A/B routing,
  CRS/transform validators, overlap/alignment/reprojection, reference
  raster handling.
- Verification: unit + integration. Evidence: ingestion/geospatial
  test suites green; invalid-input rejection demonstrated.
- Status: **Review/Integration** — verify calibration-adjacent
  branches are merged and green before marking Done.

## GATE 3 — Depth Runtime (Shravan + Shivam boundary)

- Prerequisites: `DepthBackend` interface, DA-V2 Small integration,
  deterministic inference, provenance (checkpoint hash + upstream
  revision + license separated from runtime record).
- Verification: runtime + integration. Evidence: S16/S16R runtime
  verification on main; real DA-V2 desktop path test green.
- Status: **Integration** — runtime proven; product promotion of
  further model work still open (see RESEARCH_VS_PRODUCT.md).

## GATE 4 — Calibration / Reference Validity (Shivam)

- Prerequisites: relative→metric mapping, DEM/GCP ingestion,
  reference controls, calibration quality checks, metric validity
  rules (no calibration ⇒ no metric claim).
- Verification: scientific + integration. Evidence: calibration tests;
  quality-check rejection of uncalibrated metric requests.
- Status: **In Progress/Review** — confirm merge state of
  `feat/shivam-calibration`, `feat/shivam-dem-reference`,
  `feat/shivam-reference-controls`.

## GATE 5 — DSM / rDSM Product Correctness (Shivam)

- Prerequisites: DSM/rDSM construction, height semantics, nodata
  handling, standard GeoTIFF export with CRS/transform/provenance.
- Verification: unit + integration + scientific. Evidence: dsm/rdsm/
  height/export test suites; exported product opens in standard GIS.
- Status: **In Progress/Review** — confirm merge state of
  `feat/shivam-dsm-engine`, `feat/shivam-height-semantics`,
  `feat/shivam-geotiff-export`.

## GATE 6 — Mesh + Texture (Shivam + Aryan)

- Prerequisites: renderer-independent terrain mesh with preserved
  coordinates; UVs + source identity; viewer-side RGB projection.
- Verification: integration + visual. Evidence: mesh tests; textured
  scene screenshot/run.
- Status: **In Progress** — mesh engine exists; viewer texturing is
  Aryan track (mostly unmerged branches).

## GATE 7 — Interactive 3D (Aryan)

- Prerequisites: orbit / first-person / aerial navigation, waypoint
  flythrough, height/slope/measurement/profile tools, session
  lifecycle, layers.
- Verification: visual + runtime. Evidence: flythrough validation
  (`af6d416` trajectory workflow); measurement vs known geometry.
- Status: **In Progress** — ~25 Aryan branches exist, most unmerged;
  merge + integration is the work.

## GATE 8 — Scientific Validation (Shravan + Shivam)

- Prerequisites: benchmark framework, real-data evaluation,
  RMSE/MAE/correlation/stability recorded, significance where claimed.
- Verification: scientific. Evidence: `docs/dav2-level3-evidence.md`
  - significance docs; broader-scene evidence.
- Status: **Blocked (open research)** — current 32-tile GAMUS evidence
  is honestly poor in absolute terms; SIH-wide accuracy unproven.

## GATE 9 — End-to-End Integration (Shivam + Aryan)

- Prerequisites: canonical adapter + transport + local service +
  desktop consumption running the full pipeline both paths.
- Verification: end-to-end + runtime. Evidence: `test(integration):
accept real DA-V2 desktop path` green on main; full Path A and Path B
  runs recorded.
- Status: **Integration** — partial (Path A desktop path accepted;
  Path B metric end-to-end still to demonstrate).

## GATE 10 — Standalone Deployment (Aryan + Shivam)

- Prerequisites: reproducible runtime provisioning, native host,
  installer, fresh-machine startup with no dev-path dependency.
- Verification: end-to-end + runtime. Evidence: fresh-machine launch
  log; install docs.
- Status: **Backlog/In Progress** — provisioning automation started;
  native host + installer pending.

## GATE 11 — Final SIH Acceptance (all; Shivam merge authority)

- Prerequisites: GATES 1–10 passed.
- Verification: all types. Evidence: the full checklist in the
  `SIH 26175 — Final Acceptance Gate` issue.
- Status: **Backlog** — not claimable until evidence exists.
