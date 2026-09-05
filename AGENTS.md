# AGENTS.md — DepthWizard (SIH 26175)

North star: SIH Problem Statement 26175 — single-view height estimation
and 3D flythrough. Full plan: `docs/project/MASTER_PLAN.md`. Ownership:
`docs/project/TEAM_OWNERSHIP.md`. Shared control plane: GitHub Project
**DepthWizard — SIH 26175**.

## Team ownership (locked)

- **Shivam:** architecture, Python core, geospatial, calibration, DSM,
  pipeline, integration, release, scientific acceptance, final merge
  authority.
- **Shravan:** ML, datasets, depth models, experiments, benchmarks.
  ML output is relative geometry only (`metric=false`).
- **Aryan:** desktop app (React/TS/Three.js), rendering, navigation,
  measurement, UX, packaging.
- Never assign ownership by convenience. No auto-merging teammates'
  branches.

## Scientific truthfulness

- Relative depth ≠ metric DSM. Metric claims require calibration /
  reference evidence (method + units + provenance + validity).
- Path A (PNG/JPG): relative only — never invent CRS, coordinates,
  metres. Path B (GeoTIFF): preserve CRS/transform; metric only when
  justified.
- Never invent results, completion, or verification. No Done without
  evidence matching the issue's verification type.
- Research results are not product claims until promoted through the
  product path (`docs/project/RESEARCH_VS_PRODUCT.md`).

## Geospatial correctness

- Preserve CRS, affine transform, spatial metadata, provenance.
- Standard exports (GeoTIFF) with nodata/validity semantics.
- Integration adapter is transparent: no recalibration, resampling,
  reprojection, remeshing, or unit changes without an accepted
  architectural amendment.

## Git workflow (no exceptions)

- Never: `git reset --hard`, `git clean -fd`, `git checkout -- .`,
  force push, history rewrites, deleting teammate branches, merging
  teammates' branches automatically.
- Branch from `main`: `feat/<owner>-<topic>`. One concern per branch.
- Conventional commits. Push normally. Open a PR; do not merge
  without review (Shivam has final merge authority).

## Testing expectations

- Python: `python -m pytest`, `python -m ruff check src tests`,
  `python -m ruff format --check src tests`, `python -m mypy src tests`.
- Frontend: `npm run typecheck`, `npm run test`, `npm run build`.
- Heavy-model tests are opt-in; CI never downloads GAMUS or huge
  models for ordinary checks.
- Never commit raw datasets, checkpoints, HF caches, huge generated
  rasters/meshes, secrets, or local envs (see `.gitignore` +
  `docs/project/THIRD_PARTY_REGISTER.md`).

## Planning hierarchy

1. SIH Problem Statement 26175
2. `docs/project/MASTER_PLAN.md`
3. GitHub Project: DepthWizard — SIH 26175
4. Current repository state (evidence wins)
5. Team ownership
6. Active implementation tasks

Team commands live in `.opencode/commands/team/`; skills in
`.opencode/skills/`; agents in `.opencode/agents/`.
