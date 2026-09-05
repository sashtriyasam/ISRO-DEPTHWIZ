# DepthWizard — Project Status (evidence-based, 2026-09-05)

Source: `main` @ `6ed623e`, branch inventory (~50 branches),
`docs/sih-architecture.md`, `docs/dav2-level3-evidence.md`.
Uncertainty is marked; nothing below is a planning guess presented
as completion.

| Area                  | Status      | Evidence / note                                                                                                |
| --------------------- | ----------- | -------------------------------------------------------------------------------------------------------------- |
| Repository foundation | Done        | `pyproject` (pytest/ruff/mypy strict), TS tooling, `.gitignore` covers `*.tif/*.obj/*.ckpt/*.pt/*.safetensors` |
| Core geospatial       | Review      | `depthwizard.geospatial/dem/export/ingestion` + tests exist; GATE 2 pending merge-state confirmation           |
| Depth / model backend | Integration | Real DA-V2 Small runtime verified (S16/S16R on main); output is **relative-only**                              |
| Calibration           | In Progress | Engine + DEM reference + controls branches exist; merge/verification state to confirm                          |
| DSM / rDSM            | In Progress | DSM engine, height semantics, GeoTIFF export branches exist; GIS-open check pending                            |
| Mesh                  | In Progress | Renderer-independent mesh engine exists; viewer texturing pending (Aryan)                                      |
| Desktop               | In Progress | Session, camera, flythrough, measurement, layers branches exist; ~25 Aryan branches mostly unmerged            |
| 3D / flythrough       | In Progress | Waypoint flythrough + visual validation (`448ea52`, `af6d416`) on branches, not all on main                    |
| Integration           | Integration | Canonical adapter + transport exist; Path A desktop path accepted on main (`31d9173`); Path B metric E2E open  |
| Scientific validation | Blocked     | GAMUS 32-tile: MAE 4.40 m / RMSE 5.86 m / R² 0.23 — real but poor; SIH-wide accuracy unproven                  |
| Packaging             | Backlog     | Provisioning automation started; native host + installer pending                                               |
| Final SIH readiness   | Backlog     | Blocked on GATES 6–10                                                                                          |

## Head state

- `main` = `6ed623e` "fix(runtime): validate real DA-V2 desktop execution".
- Working branch for this governance change:
  `feat/shivam-project-governance` (cut from `main`).
- Open PRs: 0. Repo issues before this change: 0.
- Teammate branches are **preserved untouched**; no merges, no
  deletions, no history rewrites performed by this change.

## Immediate next recommended work

1. Confirm merge state of calibration/DSM/mesh branches → close or
   queue GATE 4/5/6 items with evidence.
2. Merge Aryan desktop stack incrementally behind the transport
   contract → GATE 7/9.
3. Shravan: M14 target-semantics audit + broader benchmark evidence →
   unblock GATE 8.
4. Fresh-machine + installer acceptance → GATE 10.
