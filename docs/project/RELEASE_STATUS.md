# DepthWizard — Release Status

**North star:** SIH Problem Statement 26175 — Single-View Height Estimation and 3D Flythrough.

**Last updated:** 2026-09-06 | **Main SHA:** `583f982` | **Origin/main SHA:** `583f982`

---

## What Is on Main (Evidence-Based)

| Area                                                       | Status          | Evidence                                                                         |
| ---------------------------------------------------------- | --------------- | -------------------------------------------------------------------------------- |
| Repository foundation                                      | **Done**        | pytest/ruff/mypy strict, TS typecheck/test/build, `.gitignore` data rules        |
| Core geospatial (ingestion, CRS/transform, DEM reference)  | **Review**      | tests exist; GATE 2 pending merge confirmation                                   |
| Depth / model backend (DA-V2 Small)                        | **Integration** | real runtime verified S16/S16R; output is **relative-only**                      |
| Calibration engine + DEM reference + reference controls    | **In Progress** | branches exist; merge/verification state to confirm                              |
| DSM / rDSM (engine, height semantics, GeoTIFF export)      | **In Progress** | branches exist; GIS-open check pending                                           |
| Mesh (renderer-independent)                                | **In Progress** | engine exists; viewer texturing pending (Aryan)                                  |
| Desktop (session, camera, flythrough, measurement, layers) | **In Progress** | ~25 Aryan branches mostly unmerged                                               |
| 3D / flythrough (waypoint + visual validation)             | **In Progress** | `448ea52`, `af6d416` on branches                                                 |
| Integration (canonical adapter + transport)                | **Integration** | Path A desktop path accepted (`31d9173`); Path B metric E2E open                 |
| Scientific validation                                      | **Blocked**     | GAMUS 32-tile: MAE 4.40 / RMSE 5.86 / R² 0.23 — real but poor; SIH-wide unproven |
| Packaging (provisioning, native host, installer)           | **Backlog**     | provisioning automation started; host + installer pending                        |
| Final SIH readiness                                        | **Backlog**     | blocked on GATES 6–10                                                            |

---

## What Is Frozen (On Main, Done)

- Repository foundation (pyproject, package.json, tooling, governance docs)
- DA-V2 Small **runtime** (loads, runs deterministically, provenance recorded) — GATE 3
- DepthBackend interface (frozen shape)
- Integration contract (`docs/project/INTEGRATION_CONTRACT.md`)
- Team ownership, AGENTS.md, branch policy
- SIH architecture contract (`feat/shivam-sih-architecture-contract` merged)

---

## What Is Active (In Progress / Unmerged)

| Branch                                | Owner  | Gate    | Status            |
| ------------------------------------- | ------ | ------- | ----------------- |
| feat/shivam-field-benchmark           | Shivam | GATE 8  | UNMERGED-REQUIRED |
| feat/shivam-benchmark-expansion       | Shivam | GATE 8  | UNMERGED-REQUIRED |
| feat/shivam-benchmark-scaleout        | Shivam | GATE 8  | UNMERGED-REQUIRED |
| feat/shivam-cross-city-benchmark      | Shivam | GATE 8  | UNMERGED-REQUIRED |
| feat/shivam-native-runtime-packaging  | Shivam | GATE 10 | UNMERGED-REQUIRED |
| feat/shivam-runtime-provisioning      | Shivam | GATE 10 | UNMERGED-REQUIRED |
| feat/shivam-sih-architecture-contract | Shivam | GATE 11 | UNMERGED-REQUIRED |
| feat/aryan-native-host-installer      | Aryan  | GATE 10 | UNMERGED-REQUIRED |

---

## What Is Waiting (Blocked / Dependencies)

| Work                         | Blocked By                                                       | Owner            |
| ---------------------------- | ---------------------------------------------------------------- | ---------------- |
| GATE 4 Calibration merge     | confirm calibration/dem-reference/reference-controls merge state | Shivam           |
| GATE 5 DSM merge             | confirm dsm-engine/height-semantics/geotiff-export merge state   | Shivam           |
| GATE 6 Mesh+Texture          | mesh engine (merged) + viewer texturing (Aryan unmerged)         | Shivam + Aryan   |
| GATE 7 Interactive 3D        | ~25 Aryan desktop branches unmerged                              | Aryan            |
| GATE 8 Scientific Validation | GAMUS evidence honestly poor; broader runs needed                | Shravan + Shivam |
| GATE 9 E2E Integration       | Path B metric end-to-end                                         | Shivam + Aryan   |
| GATE 10 Deployment           | native host + installer (Aryan) + provisioning (Shivam)          | Aryan + Shivam   |
| GATE 11 Final Acceptance     | GATES 1–10                                                       | All              |

---

## What Is Blocked (Real Blockers)

1. **GATE 8 Scientific Validation** — current 32-tile GAMUS evidence (MAE 4.40 / RMSE 5.86 / R² 0.23) is a research signal, not SIH validation. Broader-scene evidence, GPU behavior, and GPU behaviour remain open.
2. **GATE 10 Standalone Deployment** — native Electron host + installer pending (Aryan); runtime provisioning automation started but not complete (Shivam).
3. **No GitHub Project control plane** — Project #4 exists but not configured (no views, fields, items, automation). gh token lacks `read:project` scope.
4. **No CI workflows** — GitHub Actions not configured.
5. **No CODEOWNERS** — not configured.
6. **No branch protection** — not configured.

---

## Evidence Index

| Doc                                              | Purpose                        | Verified Against Code |
| ------------------------------------------------ | ------------------------------ | --------------------- |
| `docs/sih-architecture.md`                       | Canonical system architecture  | Yes (commit 875484a)  |
| `docs/project/MASTER_PLAN.md`                    | Phase map, pipeline, semantics | Yes                   |
| `docs/project/TEAM_OWNERSHIP.md`                 | Locked ownership model         | Yes                   |
| `docs/project/RELEASE_GATES.md`                  | Gate definitions + status      | Yes                   |
| `docs/project/SIH_REQUIREMENT_TRACEABILITY.md`   | R1–R15 traceability            | Yes                   |
| `docs/project/RESEARCH_VS_PRODUCT.md`            | Research→product protocol      | Yes                   |
| `docs/project/INTEGRATION_CONTRACT.md`           | Backend↔desktop boundary       | Yes                   |
| `docs/project/THIRD_PARTY_REGISTER.md`           | Model/data provenance          | Yes                   |
| `docs/project/PROJECT_CONTROL_PLANE_RECOVERY.md` | gh CLI recovery for Project    | Yes                   |
| `docs/dav2-level3-evidence.md`                   | S19–S21 benchmark evidence     | Yes                   |
| `docs/dav2-runtime-acceptance.md`                | DA-V2 runtime verification     | Yes                   |

---

## Next Release Gate

**GATE 4 — Calibration / Reference Validity** (Shivam)

**Prerequisites:**

- Calibration engine merged + tests green
- DEM reference pipeline merged
- Reference controls merged
- Quality-check rejection of uncalibrated metric requests demonstrated

**Then:** GATE 5 (DSM/rDSM) → GATE 6 (Mesh+Texture) → GATE 7 (Interactive 3D) → GATE 8 (Scientific) → GATE 9 (E2E) → GATE 10 (Deployment) → GATE 11 (Final)

---

## Current Team State

| Member      | Focus                        | Active Work                                                            |
| ----------- | ---------------------------- | ---------------------------------------------------------------------- |
| **Shivam**  | Core/Geo/Cal/DSM/Int/Release | GATE 4/5 merge confirmation; benchmark branches; architecture contract |
| **Shravan** | ML/Data/Model/Research       | M14–M17 consolidation → GATE 8 evidence                                |
| **Aryan**   | Desktop/3D/UX/Packaging      | Native host/installer PR; desktop stack merge                          |

---

## Verified Blockers (Only Real Ones)

1. **GATE 8 blocked** — no SIH-wide accuracy evidence; GAMUS 32-tile is research signal only
2. **GATE 10 blocked** — native host + installer not started; provisioning incomplete
3. **Project control plane** — gh token lacks `read:project`; Project #4 unconfigured
4. **CI** — no GitHub Actions workflows
5. **Governance gaps** — no CODEOWNERS, no branch protection, no issue-first enforcement

---

_This status reflects repository evidence as of commit `583f982`. Update after each gate closure or significant merge._
