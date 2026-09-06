# DepthWizard (SIH 26175) — Session Handoff

**Date:** 2026-09-05  
**Session ID:** (current)  
**Branch:** `main` at `583f982045330f524867962ac612e9896cff8d15`

---

## 1. Current Repository State

### Commit History (Recent)

| Commit    | Author  | Message                                                    | Branch                           |
| --------- | ------- | ---------------------------------------------------------- | -------------------------------- |
| `583f982` | (merge) | Merge branch 'feat/shivam-project-governance'              | `main`                           |
| `1be2226` | Shivam  | feat(rel): close the non-georeferenced SIH path end-to-end | `feat/shivam-project-governance` |
| `7894482` | Shivam  | chore(governance): establish SIH project control plane     | `feat/shivam-project-governance` |

### Active Branches

- **main** (583f982) — Current HEAD, merged governance branch
- **feat/shivam-relative-desktop-boundary** (6ed623e) — Desktop boundary detection work
- **feat/shivam-project-governance** (1be2226) — Merged into main

### Working Tree

Clean — no uncommitted changes.

---

## 2. Project Context (SIH Problem Statement 26175)

**North Star:** Single-view height estimation and 3D flythrough for Bike Intercom App.

### Team Ownership (Locked)

| Owner       | Domain                                                                                                                                |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **Shivam**  | Architecture, Python core, geospatial, calibration, DSM, pipeline, integration, release, scientific acceptance, final merge authority |
| **Shravan** | ML, datasets, depth models, experiments, benchmarks — _ML output is relative geometry only (metric=false)_                            |
| **Aryan**   | Desktop app (React/TS/Three.js), rendering, navigation, measurement, UX, packaging                                                    |

### Critical Rules

- **Relative depth ≠ metric DSM** — Metric claims require calibration + reference evidence (method + units + provenance + validity)
- **Path A (PNG/JPG):** Relative only — never invent CRS, coordinates, metres
- **Path B (GeoTIFF):** Preserve CRS/transform; metric only when justified
- **Never** invent results, completion, or verification
- **Git workflow:** No `reset --hard`, no force push, no history rewrites, no auto-merging teammates' branches
- **Branch naming:** `feat/<owner>-<topic>` from `main`, one concern per branch
- **Final merge authority:** Shivam

---

## 3. What Was Accomplished This Session

### Governance & Planning (Completed & Merged)

1. **Established SIH Project Control Plane** (PR #1, merged)
   - GitHub Project "DepthWizard — SIH 26175" configured
   - Iteration field "Sprint" created (2-week iterations)
   - Status field configured (Backlog → Ready → In Progress → In Review → Done)
   - Priority field (P1/P2/P3)
   - Labels synced: `area:*`, `type:*`, `priority:*`, `owner:*`

2. **Closed Non-Georeferenced SIH Path End-to-End** (PR #2, merged)
   - Relative depth pipeline validated for PNG/JPG inputs
   - Desktop app integration point defined (relative geometry only)
   - No metric claims made without calibration evidence

### Branches Created but Not Merged

- **feat/shivam-relative-desktop-boundary** — Desktop boundary detection work (6ed623e)

---

## 4. Key Files & Architecture

### Repository Structure

```
D:\SIH DEPH WIZARD\
├── apps/
│   ├── mobile/          # React Native (Expo)
│   └── api/             # FastAPI backend
├── packages/
│   └── shared/          # Shared TypeScript types
├── docs/
│   └── project/
│       ├── MASTER_PLAN.md
│       ├── TEAM_OWNERSHIP.md
│       ├── RESEARCH_VS_PRODUCT.md
│       └── THIRD_PARTY_REGISTER.md
├── .opencode/
│   ├── commands/team/   # Team GSD commands
│   ├── skills/          # Custom skills
│   └── agents/          # Custom agents
└── .planning/           # GSD planning directory (if initialized)
```

### Testing Commands

| Layer    | Command                                                                                                                     |
| -------- | --------------------------------------------------------------------------------------------------------------------------- |
| Python   | `python -m pytest`, `python -m ruff check src tests`, `python -m ruff format --check src tests`, `python -m mypy src tests` |
| Frontend | `npm run typecheck`, `npm run test`, `npm run build`                                                                        |

---

## 5. GitHub Project State

**Project:** DepthWizard — SIH 26175 (Owner: Shivam, Org/User context)

### Fields Configured

- **Status** (Single Select): Backlog, Ready, In Progress, In Review, Done
- **Priority** (Single Select): P1, P2, P3
- **Sprint** (Iteration): 2-week iterations, auto-created
- **Owner** (Single Select): Shivam, Shravan, Aryan
- **Area** (Single Select): architecture, ml, desktop, geospatial, pipeline, integration
- **Type** (Single Select): feat, fix, chore, docs, spike, research

### Current Items (from memory — verify with `gh project item-list`)

- Governance setup items → Done
- Non-georeferenced path closure → Done
- Desktop boundary detection → In Progress (on branch)

---

## 6. Immediate Next Steps

### Option A: Continue Desktop Boundary Work (feat/shivam-relative-desktop-boundary)

```bash
git checkout feat/shivam-relative-desktop-boundary
# Resume implementation
```

### Option B: Start New Phase via GSD

```bash
# Check planning state
cat .planning/STATE.md 2>/dev/null || echo "No .planning/ — run /gsd-new-project"

# Or quick task
/gsd-quick "description of small task"
```

### Option C: Verify Current State & Plan Next Milestone

```bash
# Check GitHub Project for open items
gh project item-list --owner Shivam --project-number 1

# Run gsd-review-backlog to promote items
/gsd-review-backlog
```

---

## 7. Open Questions for Next Session

1. **Desktop boundary branch:** Complete `feat/shivam-relative-desktop-boundary` and merge, or abandon?
2. **ML pipeline:** Shravan — any depth model benchmarks ready for integration?
3. **Desktop app:** Aryan — Three.js rendering pipeline status?
4. **Calibration path:** Path B (GeoTIFF) — any ground control points / GCPs available for metric validation?
5. **GSD planning:** Initialize `.planning/` with `/gsd-new-project` or continue ad-hoc?

---

## 8. Quick Commands Reference

```bash
# Check git status
git status

# View GitHub Project items
gh project item-list --owner Shivam --project-number 1 --format json

# List branches
git branch -a

# Run Python tests
cd apps/api && python -m pytest

# Run frontend tests
cd apps/mobile && npm run test

# GSD commands (if .planning/ exists)
/gsd-progress
/gsd-plan-phase <N>
/gsd-execute-phase <N>
/gsd-verify-work
```

---

## 9. Important Reminders

- **Scientific truthfulness:** Never claim metric results without calibration evidence
- **Geospatial correctness:** Preserve CRS, affine transform, provenance
- **No auto-merge:** All PRs require review; Shivam has final merge authority
- **Heavy models:** Opt-in only; CI never downloads GAMUS/huge models
- **Secrets:** Never commit raw datasets, checkpoints, HF caches, huge rasters/meshes, secrets, local envs

---

_Generated at session end. Update this file at start of next session._
