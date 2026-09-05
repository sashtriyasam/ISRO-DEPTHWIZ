# DepthWizard — Release Synchronization Record

## Synchronization Summary

| Field | Value |
|-------|-------|
| Pre-sync Aryan SHA | `25c5ad07c0fae4e4ae9b19f2bee71f553df191a2` |
| Canonical announced SHA | `583f982045330f524867962ac612e9896cff8d15` |
| Verified canonical main SHA | `583f982045330f524867962ac612e9896cff8d15` |
| Canonical main = origin/main HEAD | YES |
| Commits after announced SHA | 0 |
| Merge-base (Aryan ↔ Canonical) | `6ed623e63c133a2b5780f83deb106189c71ded8a` |
| New Aryan HEAD | `6872c01714a6776545c323c965cb5702a5d1b886` |
| Synchronization method | Controlled rebase (Aryan-owned branch only) |
| Rebase conflicts | 0 (clean) |
| Aryan commits rebased | 6 |
| Aryan commits rewritten SHAs | All 6 (normal rebase behavior) |
| Timestamp | 2026-09-05 23:15 IST |

## Rewritten Aryan Commit SHAs

| Old SHA | New SHA | Message |
|---------|---------|---------|
| `1bac431` | `f524848` | feat(native-host): Electron foundation + runtime contract + installer strategy |
| `ef4e5f5` | `41dc33e` | feat(desktop): productionize Electron host and installer |
| `04bb5d9` | `5740f60` | fix(desktop): align runtime resolution, harden security, build Windows package |
| `ae21294` | `ec511a7` | fix(desktop): clarify Python-prerequisite policy and harden error messaging |
| `cbe3144` | `6bb0dd0` | docs(release): finalize Phase 5 acceptance evidence |
| `25c5ad0` | `6872c01` | test(release): add windows acceptance witness harness |

## Canonical Changes Consumed (from `feat/shivam-project-governance`)

### 115 files, ~7856 insertions

#### Classification

| Category | Files | Key Changes |
|----------|-------|-------------|
| GOVERNANCE | 68 | AGENTS.md, project control plane, team ownership, release gates, issue templates, opencode agents/skills/commands |
| RUNTIME | 5 | `output_mode: "metric" \| "relative"` on wire; `run_relative_path()` in rDSM pipeline; relative mode in `backend_bridge.py` |
| SERVICE | 3 | `_execute_relative()` in service.py; `output_mode` field in ServiceRequest model; `relative_surface`/`relative_mesh` artifact kinds |
| TRANSPORT | 5 | `RelativeBundle`, `fetchRelative()`, `resolveRelativeArtifact()`, `verifyRelativeBundle()` |
| ARTIFACT | 4 | `BackendRelativeProduct`, `BackendRelativeSurfaceTransport`, `BackendRelativeMeshTransport`; `adaptRelativeProduct()` |
| TYPESCRIPT | 5 | `mode` on `BackendBridge`, `output_mode` on `ServiceRequestWire`, `outputMode` on `ServiceExecutionArgs` |
| PYTHON | 5 | `rdsm/` package (models, mesh, rasterize, pipeline); `TransportRelativeProduct`; `relative_product_from_json()` |
| EVALUATION | 9 | `depthwizard/evaluation/` package; GAMUS manifests; `evaluate.py` script |
| GEOSPATIAL | 2 | `src/input/source.ts` updated; `src/service/processing.ts` adds `relativeMeshDescriptorOf()` |
| DOCUMENTATION | 12 | Architecture, evaluation protocol, evaluation significance, datasets, SIH traceability |
| TESTS | 13 | Evaluation tests, rdsm tests, service test updates |

#### Aryan files NOT touched by canonical changes

All 20 Aryan files are untouched by the canonical merge:
- `electron/main.ts`, `electron/preload.ts`, `electron/electron.test.ts`
- `electron-builder.yml`, `tsconfig.electron.json`
- `src/host/host.ts`, `src/host/electron.d.ts`, `src/host/host.test.ts`
- `scripts/windows_release_preflight.ps1`
- All docs (release-witness.md, native-release-acceptance.md, release-blockers.md, phase5-acceptance.md, aryan-runtime-integration.md, installer-strategy.md, native-host.md)
- `package.json`, `package-lock.json`, `.gitignore`, `vite.config.ts`

## Alignment Fixes Applied

| File | Change | Reason |
|------|--------|--------|
| `tsconfig.electron.json` | `module: "commonjs"` → `"node16"`, `moduleResolution: "node"` → `"node16"` | TypeScript 5.8.3 removed `moduleResolution: "node"` (node10) |
| `src/backend/sourceDescriptor.test.ts` | Added `"output_mode"` to expected request keys | Canonical contract added `output_mode` field to `ServiceRequestWire` |

## Runtime Contract (Canonical Main)

| Component | Contract |
|-----------|----------|
| Python | External prerequisite; `DEPTHWIZARD_PYTHON` env → `python` on PATH |
| Provisioning | NOT present on canonical main |
| Runtime self-check | NOT present on canonical main |
| Checkpoint | `DW_DAV2_CKPT` env → `%APPDATA%/DepthWizard/checkpoints/` → `<resourcesPath>/checkpoints/` |
| Checkpoint file | `depth_anything_v2_vits.pth` |
| Checkpoint SHA | `715fade13be8f229f8a70cc02066f656f2423a59effd0579197bbf57860e1378` |
| Backend (metric) | `backend_bridge.py --mode metric --terrain-file <path>` |
| Backend (relative) | `backend_bridge.py --mode relative --terrain-file <path>` |
| Service | `depthwiz_service.py` (stdio JSON envelope) |
| Wire contract version | `"1"` |
| Output modes | `"metric"` (calibrated), `"relative"` (calibration-free rDSM) |
| Relative semantics | `units: null`, `frame: "local"`, no calibration fields |
| Metric semantics | `units: "meters"`, calibration fields required |

## Verification

| Check | Result |
|-------|--------|
| SHA verified on origin/main | PASS |
| No destructive history operation | PASS (controlled rebase only) |
| Aryan stack survived | PASS (all 16 files present) |
| TypeScript main | PASS (exit 0) |
| TypeScript electron | PASS (exit 0) |
| Frontend tests | 627 passed, 4 skipped, 0 failed |
| Electron tests | 35 passed, 0 failed |
| New canonical tests (rdsm/evaluation/service/backends/integration) | 160 passed, 3 skipped, 0 failed |
| Frontend build | PASS |
| Electron build | PASS |
| Security audit | 13/13 PASS |
| Scientific boundary audit | 4/4 PASS |
