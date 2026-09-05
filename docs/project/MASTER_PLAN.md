# DepthWizard — SIH 26175 Master Plan

**North star:** SIH Problem Statement 26175 —
"DepthWizard: Single-View Height Estimation and 3D Flythrough".

Single-view optical RGB remote-sensing imagery → depth/geometric
representation → calibration/reference → rDSM/DSM → terrain mesh →
RGB projection → interactive 3D flythrough → height/slope/measurement/
validation → standalone software.

Canonical architecture: `docs/sih-architecture.md`.
Team ownership: `docs/project/TEAM_OWNERSHIP.md`.
SIH traceability: `docs/project/SIH_REQUIREMENT_TRACEABILITY.md`.
Integration contract: `docs/project/INTEGRATION_CONTRACT.md`.
Release gates: `docs/project/RELEASE_GATES.md`.
Live status: `docs/project/PROJECT_STATUS.md`.
Research vs product: `docs/project/RESEARCH_VS_PRODUCT.md`.
Third-party register: `docs/project/THIRD_PARTY_REGISTER.md`.

Shared team control plane: GitHub Project **DepthWizard — SIH 26175**
(`github.com/users/sashtriyasam/projects/4`, renamed from project #4).

## Pipeline (canonical dependency order)

```text
INPUT
↓
GEOSPATIAL / IMAGE VALIDATION
↓
DEPTH / GEOMETRIC REPRESENTATION (relative only)
↓
CALIBRATION / REFERENCE (explicit; metric claims live here or nowhere)
↓
rDSM / DSM
↓
MESH
↓
TEXTURE PROJECTION
↓
3D SCENE
↓
FLYTHROUGH / ANALYSIS
↓
VALIDATION
↓
PACKAGING
↓
SIH FINAL ACCEPTANCE
```

Branch:

- **Path A (PNG/JPG, non-georeferenced):** input → relative depth →
  rDSM → mesh → texture → 3D. Never CRS, never metres.
- **Path B (GeoTIFF, georeferenced):** input → relative depth →
  reference/calibration → metric DSM → mesh → texture → 3D.
  CRS/transform preserved end to end.

## Phase map (matches Project Milestone field)

| #   | Phase                               | Owner                                     | Gate    |
| --- | ----------------------------------- | ----------------------------------------- | ------- |
| 1   | Repository & engineering foundation | Shivam                                    | GATE 1  |
| 2   | Input & geospatial understanding    | Shivam                                    | GATE 2  |
| 3   | Monocular geometry / depth runtime  | Shravan (+ Shivam boundary)               | GATE 3  |
| 4   | Metric calibration                  | Shivam                                    | GATE 4  |
| 5   | rDSM / DSM products                 | Shivam                                    | GATE 5  |
| 6   | Terrain mesh & texture              | Shivam (mesh) / Aryan (texture in viewer) | GATE 6  |
| 7   | Interactive 3D / desktop            | Aryan                                     | GATE 7  |
| 8   | Validation & scientific evidence    | Shravan (+ Shivam methodology)            | GATE 8  |
| 9   | End-to-end integration              | Shivam + Aryan                            | GATE 9  |
| 10  | Packaging & standalone deployment   | Aryan (+ Shivam runtime)                  | GATE 10 |
| 11  | SIH final acceptance                | All (Shivam merge authority)              | GATE 11 |

## Non-negotiable semantics

1. **Relative depth ≠ metric DSM.** Depth Anything V2 Small (or any
   backend behind `DepthBackend`) yields relative geometry only.
   Metric output exists only after explicit calibration against
   validated DEM/GCP/reference controls, with units + provenance +
   validity evidence recorded.
2. **No fabricated CRS/coordinates/metres** on Path A.
3. **The integration adapter is transparent.** It must not recalibrate,
   rerasterize, resample, reproject, remesh, reinterpret semantics, or
   change units unless an explicitly accepted architectural change
   says so.
4. **No Done without evidence.** Status transitions require the
   verification type recorded on the issue (unit / integration /
   scientific / runtime / visual / end-to-end).
5. **Research results are not product claims** until they pass through
   the product integration path with acceptance evidence.

## Planning hierarchy (precedence order)

1. SIH Problem Statement 26175
2. `docs/project/MASTER_PLAN.md` (this file)
3. GitHub Project: DepthWizard — SIH 26175
4. Current repository state (evidence wins over plans)
5. Team ownership
6. Active implementation tasks
