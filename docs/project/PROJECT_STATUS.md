# DepthWizard — Project Status (evidence-based, 2026-09-06)

Source: `main` @ `8aafc41`, working branch `feat/shivam-bugfixes-progress-relay`,
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
| Desktop app & IPC     | Done        | Electron IPC stage relay, Python 3.13 discovery, process safety, ISRO space radar telemetry loader overlay    |
| 3D / flythrough       | In Progress | Waypoint flythrough + visual validation (`448ea52`, `af6d416`) on branches, not all on main                    |
| Integration           | Integration | Canonical adapter + transport exist; Path A desktop path accepted on main (`31d9173`); Path B metric E2E open  |
| Scientific validation | Blocked     | GAMUS 32-tile: MAE 4.40 m / RMSE 5.86 m / R² 0.23 — real but poor; SIH-wide accuracy unproven                  |
| Packaging             | Backlog     | Provisioning automation started; native host + installer pending                                               |
| Final SIH readiness   | Backlog     | Blocked on GATES 6–10                                                                                          |

## Head state

- `main` = `8aafc41`
- Open PR #8 (`feat/shivam-bugfixes-progress-relay`):
  - Fixes Windows Python 3.13 discovery & 0-byte Store alias fallback
  - IPC handler order fix & payload size / `stagedDirs` cleanup safety checks
  - IPC `service-stage-update` real-time progress relay
  - Accessible ISRO telemetry space loader with stage progress bar and screen reader isolation
  - Vitest: 627 passed | Pytest: 549 passed
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
