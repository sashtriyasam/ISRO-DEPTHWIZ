# DepthWizard — Repository Governance

**North star:** SIH Problem Statement 26175 — Single-View Height Estimation and 3D Flythrough.

This document defines how the DepthWizard repository operates as a professional multi-person engineering/research project. It complements AGENTS.md (operational policy) and MASTER_PLAN.md (technical plan).

## 1. Branch Lifecycle

### Branch Naming

```
feat/<owner>-<topic>
```

**Examples:**

- `feat/shivam-runtime-release`
- `feat/shivam-scientific-acceptance`
- `feat/shravan-final-model`
- `feat/aryan-native-release`

**Prohibited patterns:**

- `next`, `new`, `final2`, `m31`, `misc`, `test2`, `temp`, `fix-final-final`

### Branch States

Every branch is exactly one of:

- **ACTIVE** — work in progress, regular pushes
- **RELEASE** — frozen for release candidate, only fixes allowed
- **INTEGRATED-HISTORICAL** — fully merged to main, preserved for provenance
- **SUPERSEDED** — replaced by another branch, documented
- **UNMERGED-REQUIRED** — unique work needed for current release
- **UNMERGED-OPTIONAL** — unique work, nice-to-have
- **UNKNOWN** — needs triage

### Branch Creation

1. Create GitHub Issue first (see §3)
2. Branch from `main`: `git checkout -b feat/<owner>-<topic> main`
3. One coherent concern per branch
4. Push regularly; no long-lived local-only branches

### Branch Cleanup

- **Shivam-owned INTEGRATED-HISTORICAL branches** may be deleted after documentation in this file
- **Teammate branches (Aryan/Shravan)** are NEVER deleted, renamed, rebased, or merged by Shivam
- No force-push, no history rewrite, no `git reset --hard`, no `git clean -fd`

## 2. Issue Lifecycle

### Issue-First Development

Every meaningful task follows:

```
GitHub Issue → Branch → Commits → PR → Review → Merge → Issue Closed → Project Item → Done
```

### Issue Requirements

Every issue must have:

- **Title** — clear, specific
- **Purpose** — why this work
- **Owner** — Shivam / Shravan / Aryan
- **Area** — architecture / ml / desktop / geospatial / pipeline / integration
- **Priority** — P1 / P2 / P3
- **Acceptance criteria** — checkboxes
- **Verification type** — unit / integration / scientific / runtime / visual / end-to-end
- **Dependencies** — other issues/branches
- **Release-gate impact** — which gate(s)

### Issue Types

- `feat` — product feature
- `fix` — bug fix against accepted behavior
- `chore` — maintenance, governance, tooling
- `docs` — documentation
- `spike` — time-boxed exploration
- `research` — ML/data investigation (Shravan track)

## 3. PR Lifecycle

### PR Requirements

Every PR must include:

- **Summary** — what changed
- **SIH requirement/gate** — R1–R15 or gate
- **Owner** — Shivam / Shravan / Aryan
- **Related issue** — link
- **Dependencies** — other PRs/branches
- **Tests** — which ran, results
- **Scientific validation** — if applicable
- **Geospatial validation** — if applicable
- **Runtime verification** — if applicable
- **Visual verification** — if applicable
- **Data/model provenance** — checkpoint hash, upstream revision, license
- **Release-gate impact** — which gate(s)

### PR Template

See `.github/pull_request_template.md` — includes the mandatory question:

> **Does this change make a scientific/metric/geospatial claim? If yes, where is the evidence?**

### Review Policy

- No auto-merge of teammate branches
- Shivam has final merge authority
- Disputed semantics default to stricter (relative-only, no metric claim) interpretation
- Review must verify: ownership boundaries, integration contract compliance, forbidden files, test coverage, evidence for claims

### Merge Requirements

- All required status checks pass
- Conversation resolved
- At least one review (Shivam for cross-cutting)
- No direct feature development on `main`

## 4. GitHub Project Control Plane

### Project

**DepthWizard — SIH 26175** (`github.com/users/sashtriyasam/projects/4`)

### Status Workflow

```
Backlog → Ready → In Progress → In Review → Done
```

### Fields

- **Status** — Backlog / Ready / In Progress / In Review / Done
- **Priority** — P1 / P2 / P3
- **Owner** — Shivam / Shravan / Aryan
- **Area** — architecture / ml / desktop / geospatial / pipeline / integration
- **Type** — feat / fix / chore / docs / spike / research
- **Release Gate** — Yes / No
- **Milestone** — Foundation / Core / ML / Calibration / DSM / 3D / Desktop / Integration / Validation / Packaging / Final
- **Verification** — unit / integration / scientific / runtime / visual / end-to-end

### Views

- **Master Roadmap** — roadmap layout, grouped by Milestone
- **Active Board** — board layout, grouped by Status
- **Master Table** — table layout, all fields
- **Shivam / Shravan / Aryan** — filtered by Owner
- **SIH Traceability** — filtered by SIH Area
- **Release Gates** — filtered by Release Gate = Yes

## 5. Owner Responsibilities

### Shivam (Lead Architect + Core + Integration + Release)

- Architecture authority (`docs/sih-architecture.md`)
- Python core (`src/depthwizard/`)
- Geospatial, calibration, DSM, pipeline, integration
- Release integration, scientific acceptance
- **Final merge authority**
- GATEs 1, 2, 4, 5, 9, 11 ownership

### Shravan (ML / Data / Model / Research)

- ML backends behind `DepthBackend`
- Dataset engineering, experiments, benchmarks
- Scientific evidence, evaluation protocol
- ML output is **relative geometry only** (`metric=false`, `units=None`)
- GATEs 3, 8 ownership

### Aryan (Desktop / 3D / UX / Packaging)

- Desktop app (React/TS/Three.js)
- Rendering, navigation, measurement, UX
- Native host, installer, standalone acceptance
- GATEs 7, 10 ownership

### Shared

- Integration contracts (`docs/project/INTEGRATION_CONTRACT.md`)
- Runtime validation, release readiness
- Cross-cutting documentation

## 6. Merge Authority

- **Shivam has final merge authority** on all PRs
- No auto-merge of teammate branches
- Disputed semantics default to stricter interpretation (relative-only, no metric claim)
- Cross-workstream changes require review from affected owner

## 7. Release Gates

| Gate | Name                             | Owner                  | Status      | Evidence Required                        |
| ---- | -------------------------------- | ---------------------- | ----------- | ---------------------------------------- |
| 1    | Engineering Foundation           | Shivam                 | Done        | pytest/ruff/mypy + typecheck/test/build  |
| 2    | Input & Geospatial Correctness   | Shivam                 | Review      | ingestion/geospatial suites green        |
| 3    | Depth Runtime                    | Shravan + Shivam       | Integration | S16/S16R on main                         |
| 4    | Calibration / Reference Validity | Shivam                 | In Progress | calibration tests, quality checks        |
| 5    | DSM / rDSM Product Correctness   | Shivam                 | In Progress | dsm/rdsm/height/export suites + GIS-open |
| 6    | Mesh + Texture                   | Shivam + Aryan         | In Progress | mesh tests + textured scene              |
| 7    | Interactive 3D                   | Aryan                  | In Progress | flythrough validation + geometry checks  |
| 8    | Scientific Validation            | Shravan + Shivam       | Blocked     | level-3 evidence + broader runs          |
| 9    | End-to-End Integration           | Shivam + Aryan         | Integration | Path A + Path B runs recorded            |
| 10   | Standalone Deployment            | Aryan + Shivam         | Backlog     | fresh-machine launch log                 |
| 11   | Final SIH Acceptance             | All (Shivam authority) | Backlog     | full checklist evidenced                 |

**Gate passes only when ALL prerequisites have recorded evidence.**

## 8. CI Policy

### Baseline Workflows

**Python:**

- `python -m pytest`
- `python -m ruff check src tests`
- `python -m ruff format --check src tests`
- `python -m mypy src tests`

**Frontend:**

- `npm ci`
- `npm run typecheck`
- `npm run test`
- `npm run build`

### CI Constraints

- **MUST NOT** download GAMUS, model checkpoints, huge ML assets
- **MUST NOT** require CUDA or local developer environment
- **MUST NOT** make network-dependent scientific claims
- Heavy-model tests remain opt-in (environment-gated)

## 9. Release Management

### Version Convention

- `v0.x` — development/research candidates
- `v1.0.0` — ONLY when SIH release criteria (GATE 11) are actually satisfied

### Release Process

```
main → all required gates passed → release candidate → tag → GitHub Release
```

### Release Artifacts

- Native Windows installer
- Checkpoint distribution (separate channel, documented provenance)
- Installation docs
- License/provenance bundle

## 10. Research vs Product Boundary

**RESEARCH** (`type:research`, `type:experiment`):

- GAMUS experiments, cross-city, scaleout
- Benchmark comparisons, model adaptation, loss experiments
- Alternative model evaluation (DA-V3, M14 audit)
- Conclude with evidence note — never product status flip

**PRODUCT** (`type:feature`, `type:integration`, `type:test`):

- Model **runtime** integration behind frozen `DepthBackend`
- Calibration, DSM/rDSM, mesh, export
- Desktop integration, 3D, UX, deployment
- Regression tests guarding promoted behavior

**Promotion protocol:**

1. Research issue closes with evidence (numbers + config + provenance)
2. Separate product issue adopts result, names exact integration point
3. Product tests + verification recorded; only then Project item → Done
4. Project `Track`/`SIH Area` reflects where behavior lives, not where discovered

**Current application:**

- S19/S19.1/S20/S21 GAMUS findings: **research signal**, not SIH validation
- DA-V2 Small **runtime**: product-side (GATE 3) — claim is "it runs", not "it is accurate"
- Future accuracy claims (DA-V3, adaptation, tuning) start as research

## 10. Artifact Hygiene

### Never Commit

- Raw datasets (GAMUS, etc.)
- Model checkpoints (`.pt`, `.pth`, `.safetensors`, `.ckpt`)
- Hugging Face caches
- Generated huge rasters/meshes (`.tif`, `.tiff`, `.geotiff`, `.obj`)
- Secrets, `.env`, local environments
- Developer-only paths

### Use Instead

- Manifests + checksums
- Deterministic fixtures
- Preparation scripts
- External download instructions
- Provenance documentation

### Model/Runtime Provenance

Must distinguish:

- Checkpoint hash
- Upstream repository revision
- Model license
- Runtime implementation

## 11. Security / Hygiene

### Audited Paths

Tracked files must not include:

- Large files (>100MB)
- Secrets
- Model weights
- Dataset files
- Generated outputs
- Caches
- Developer paths

### Tools

- `git ls-files` for tracked files
- `.gitignore` covers: `*.tif`, `*.tiff`, `*.geotiff`, `*.obj`, `*.ckpt`, `*.pt`, `*.pth`, `*.safetensors`, `__pycache__`, `.venv`, `.env`, `node_modules/`, `dist/`, `.vite/`, `*.tsbuildinfo`

## 12. Dependency Governance

### Documented In

- `pyproject.toml` — Python runtime + dev + optional (`dav2`)
- `package.json` / `package-lock.json` — Frontend runtime + dev

### Policy

- No opportunistic upgrades
- Upgrade only for concrete governance/security/build reason
- Optional ML deps (`torch`, `torchvision`, `opencv-python`) in `dav2` extra

## 13. Scientific Governance

### ML Candidate Promotion Requires

- Model identity
- Checkpoint hash
- Upstream revision
- Dataset
- Split
- Protocol
- Metrics
- Limitations
- Reproducibility

### Shivam owns final scientific acceptance

- Relative depth ≠ metric DSM
- Metric claims require calibration/reference evidence (method + units + provenance + validity)
- Path A (PNG/JPG): relative only — never invent CRS, coordinates, metres
- Path B (GeoTIFF): preserve CRS/transform; metric only when justified
- No Done without evidence matching issue's verification type

## 14. Emergency Hotfix Policy

For critical production issues only:

1. Create issue with `fix` type, P1 priority
2. Branch from `main`: `feat/shivam-hotfix-<topic>`
3. Minimal fix, full test suite
4. Expedited review (Shivam + affected owner)
5. Merge to `main`, tag hotfix release if needed
6. Backport to release branch if applicable

## 15. Current Branch Inventory (as of 2026-09-06)

### INTEGRATED-HISTORICAL (42 branches — fully merged to main)

**Aryan (27):** advanced-camera, artifact-pipeline, artifact-transport, backend-artifact-adapter, camera-system, canonical-integration, desktop-foundation, desktop-host, elevation-profile, flythrough, flythrough-ux, flythrough-visual-validation, height-exaggeration, input-workflow, integration-ready, layer-system, localservice-client, measurement-tools, point-inspector, processing-workflow, production-backend, production-backend-hardening, project-session, real-backend-integration, real-dsm-mesh-viewer, rendering-modes, scientific-metadata, semantic-hardening, session-correctness

**Shivam (15):** aryan-integration-readiness, calibration, dav2-runtime-verification, dem-reference, depth-backend, dsm-engine, foundation, geospatial, geotiff-export, height-semantics, ingestion, local-service, mesh-engine, pipeline-orchestration, project-governance, reference-controls, relative-desktop-boundary, shravan-dav2-integration

### UNMERGED-REQUIRED (8 branches — unique work needed for release)

| Branch                                | Owner  | Unique Commits | Purpose                   | Target Gate |
| ------------------------------------- | ------ | -------------- | ------------------------- | ----------- |
| feat/shivam-benchmark-expansion       | Shivam | 1              | significance design       | GATE 8      |
| feat/shivam-benchmark-scaleout        | Shivam | 1              | scaled execution          | GATE 8      |
| feat/shivam-cross-city-benchmark      | Shivam | 1              | cross-city robustness     | GATE 8      |
| feat/shivam-field-benchmark           | Shivam | 1              | benchmark harness         | GATE 8      |
| feat/shivam-native-runtime-packaging  | Shivam | 1              | runtime packaging path    | GATE 10     |
| feat/shivam-runtime-provisioning      | Shivam | 1              | provisioning automation   | GATE 10     |
| feat/shivam-sih-architecture-contract | Shivam | 1              | SIH architecture contract | GATE 11     |
| feat/aryan-native-host-installer      | Aryan  | 7              | Electron host + installer | GATE 10     |

### ACTIVE RESEARCH (10 branches — Shravan, no product integration yet)

| Branch                                    | Owner   | Unique Commits | Purpose                   |
| ----------------------------------------- | ------- | -------------- | ------------------------- |
| feat/shravan-dav2-geographic-diversity    | Shravan | 9              | geographic diversity eval |
| feat/shravan-dav2-geographic-rebalancing  | Shravan | 10             | geographic rebalancing    |
| feat/shravan-dav2-target-normalization    | Shravan | 7              | target normalization      |
| feat/shravan-dav2-target-normalization-m9 | Shravan | 11             | target normalization M9   |
| feat/shravan-m10-lowheight-loss           | Shravan | 13             | low-height loss           |
| feat/shravan-m10-seed-repeat              | Shravan | 12             | seed repeatability        |
| feat/shravan-m13-extended-training        | Shravan | 15             | extended training         |
| feat/shravan-m14-external-readiness       | Shravan | 18             | external readiness        |
| feat/shravan-m16-geonrw-adapt             | Shravan | 19             | GeoNRW adaptation         |
| feat/shravan-m17-structural-adapt         | Shravan | 20             | structural adaptation     |

**Note:** All Shravan branches are research (`type:research`/`type:experiment`). None are product integration candidates until promoted per §10 protocol.

## 16. Pending Integrations (UNMERGED-REQUIRED only)

| Branch                                | Owner  | Purpose                   | Target  | Dependencies         | Risk   | PR Recommendation                                             |
| ------------------------------------- | ------ | ------------------------- | ------- | -------------------- | ------ | ------------------------------------------------------------- |
| feat/shivam-benchmark-expansion       | Shivam | significance design       | GATE 8  | field-benchmark      | Low    | `feat(shivam): add significance design to benchmark harness`  |
| feat/shivam-benchmark-scaleout        | Shivam | scaled execution          | GATE 8  | field-benchmark      | Low    | `feat(shivam): scale benchmark execution with significance`   |
| feat/shivam-cross-city-benchmark      | Shivam | cross-city robustness     | GATE 8  | field-benchmark      | Medium | `feat(shivam): add cross-city robustness evaluation`          |
| feat/shivam-field-benchmark           | Shivam | benchmark harness         | GATE 8  | —                    | Low    | `feat(shivam): establish scientific benchmark harness`        |
| feat/shivam-native-runtime-packaging  | Shivam | runtime packaging         | GATE 10 | runtime-provisioning | Medium | `feat(shivam): establish reproducible runtime packaging path` |
| feat/shivam-runtime-provisioning      | Shivam | provisioning automation   | GATE 10 | —                    | Medium | `feat(shivam): establish runtime provisioning automation`     |
| feat/shivam-sih-architecture-contract | Shivam | SIH architecture contract | GATE 11 | all gates            | Low    | `feat(arch): establish SIH end-to-end architecture contract`  |
| feat/aryan-native-host-installer      | Aryan  | Electron host + installer | GATE 10 | runtime-provisioning | High   | `feat(aryan): productionize Electron host and installer`      |

## 17. Next Actions

### Shivam (exactly ONE)

**Merge feat/shivam-field-benchmark → main** (unblocks benchmark-expansion/scaleout/cross-city). Then open PRs for the three benchmark follow-ups.

### Shravan (exactly ONE)

**Consolidate M14–M17 research** into a single evidence note for GATE 8 decision. Close superseded experiment branches via documentation (not deletion).

### Aryan (exactly ONE)

**Open PR for feat/aryan-native-host-installer** targeting main. Dependencies: feat/shivam-runtime-provisioning must land first.

---

_This document is the canonical repository workflow reference. Update it when governance changes._
