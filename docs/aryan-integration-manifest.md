# Aryan Integration Manifest

Generated: 2026-09-04 (updated M30)

## Current Aryan Integration Branch

```
feat/aryan-integration-ready
198bc1d (M29 consolidation commit)
parent: d781621 (M28 session correctness)
```

## Base

```
origin/main: c97a614 (feat/integration): add canonical Aryan backend adapter
merge-base: 27ec398 (camera-system fork point)
```

## Aryan Milestone Commits (M20–M28)

| Milestone | SHA | Description | Files Changed |
|-----------|-----|-------------|---------------|
| M20 | 6b96e78 | Professional terrain rendering modes | 9 |
| M21 | 448ea52 | Waypoint-based 3D flythrough | 16 |
| M22 | 1bf18e1 | Canonical integration reconciliation | 52 |
| M23 | c28af61 | Production backend source hardening | 8 |
| M24 | 1dac740 | Flythrough UX refinement | 14 |
| M25 | af6d416 | Flythrough visual QA (CDP validation) | 3 |
| M26 | 3e5be28 | Desktop host boundary | 11 |
| M27 | dd1eb0b | Project session lifecycle | 7 |
| M28 | d781621 | Session lifecycle correctness | 7 |

## Desktop-Owned Paths

```
src/app/                          Application root, state orchestration
src/artifact/                     Artifact loading, fixture source
src/backend/                      Backend bridge, adapter, types, descriptors
src/camera/                       CameraManager, orbit/FP/aerial/trajectory controllers
src/components/                   React UI components (all panels, controls)
src/display/                      Height exaggeration types
src/flythrough/                   Trajectory model, evaluation, preview
src/host/                         Host detection, capability boundary
src/input/                        Input validation, application source
src/inspection/                   Point inspection types, resolver
src/layers/                       Layer registry, renderer, types
src/measurement/                  Measurement calculator, types
src/metadata/                     Scientific metadata derivation
src/processing/                   Processing state machine, operation
src/profile/                      Elevation profile sampler, types
src/service/                      LocalService client, transport, wire types
src/session/                      Session lifecycle, phase derivation
src/transport/                    Artifact transport, verification
src/viewer/                       Three.js viewer, terrain mesh, graphics
```

## Canonical Backend Path

```
src/depthwizard/                  Python scientific engine (synced from origin/main)
scripts/backend_bridge.py         Frontend→backend bridge (uses depthwizard.integration)
scripts/depthwiz_service.py       Stdio service transport
```

## Shivam-Dependent Interfaces

| Interface | Aryan Path | Backend Path |
|-----------|-----------|--------------|
| ServiceCapabilitiesWire | src/service/wireTypes.ts | src/depthwizard/service/wire.py |
| ServiceRequestWire | src/service/wireTypes.ts | src/depthwizard/service/wire.py |
| ServiceResponseWire | src/service/wireTypes.ts | src/depthwizard/service/wire.py |
| TerrainBundle | src/backend/types.ts | src/depthwizard/contracts/artifacts.py |
| SceneArtifact | src/types/scene.ts | (derived from bundle) |
| MetricTargetSemantics | src/service/wireTypes.ts | src/depthwizard/contracts/semantics.py |

## Shravan-Dependent Interface

```
src/backend/sourceDescriptor.ts   Production backend registration seam
                                  (currently only synthetic backend registered)
```

## Known Conflicts

**None.** Aryan and Shivam work on opposite sides of the service boundary. Aryan owns the TypeScript frontend; Shivam owns the Python backend. The interface is the stdio service protocol.

## Known Legacy Paths

```
scripts/dw_serialize.py           DELETED in M22 — replaced by depthwizard.integration
                                  (no longer exists in current line)
```

## Known Environment Failures

```
52 backend tests fail due to affine 2.4.0 incompatibility:
  - tests/geospatial/ (TypeError: unsupported operand)
  - tests/dem/test_sample.py (depthwizard.error)
  - tests/controls/ (similar affine issues)
  - tests/height/ (similar affine issues)
  - tests/dsm/ (similar affine issues)

These are pre-existing environment issues, NOT code defects.
307 backend tests pass.
```

## M30 Integration Rehearsal

**Date:** 2026-09-04
**Aryan branch:** `feat/aryan-integration-ready` at `198bc1d`
**Shivam target:** `origin/main` at `c97a614` (same as `feat/shivam-aryan-integration-readiness`)
**Merge base:** `27ec398` (camera-system fork point)

### Simulated Merge Result

**NO CONFLICT.** `git merge-tree` produced zero conflict markers.

The only "changed in both" file is `.gitignore`, which auto-merges cleanly.

Aryan adds 27 new/modified files on top of the merge base. Main has 15 commits ahead of the merge base. These are additive changes with no overlapping modifications.

### Conflicting Files

**None.** Zero file-level conflicts detected.

### Semantic Conflict Findings

**None.** Aryan and Shivam work on opposite sides of the service boundary:
- Aryan owns: TypeScript frontend, React UI, Three.js viewer, camera, flythrough, session
- Shivam owns: Python scientific backend, calibration, DSM, geospatial transforms

The interface is the stdio service protocol (`src/service/wireTypes.ts` ↔ `src/depthwizard/service/wire.py`).

### Transport Compatibility

All transport contract files are **NEW in Aryan** (do not exist in origin/main):
- `src/service/wireTypes.ts` — service wire types
- `src/backend/types.ts` — backend artifact types
- `scripts/backend_bridge.py` — frontend→backend bridge
- `scripts/depthwiz_service.py` — stdio service

These are additive. No existing Shivam files are modified by Aryan.

### Host Compatibility

Aryan's host boundary (`src/host/`) is self-contained:
- Detects browser vs Node.js runtime
- Provides capability flags
- No assumptions about backend executables
- No hardcoded paths

Compatible with any backend deployment.

### Session/Viewer Compatibility

Session lifecycle (`src/session/`) derives state from:
- `hasArtifact` (boolean)
- `processing` (ProcessingState)

No scientific values in session state. No backend assumptions. Pure derivation logic.

### Production Backend Status

**Still only SyntheticDepthBackend.** No production model adapter exists in any branch.

The `src/backend/sourceDescriptor.ts` seam remains ready for future registration.

---

## Recommended Shivam Integration Order

**ONE-SHOT MERGE: SAFE**

```bash
git checkout feat/shivam-aryan-integration-readiness
git merge feat/aryan-integration-ready
```

This brings in the complete M01–M29 desktop stack in one operation. No sequential merging needed.

### Rollback Considerations

If the merge causes issues:
```bash
git merge --abort  # if still in progress
git reset --hard origin/main  # after merge, to revert
```

The Aryan branch remains unchanged on origin for retry.

### Post-Merge Validation Commands

```bash
# Frontend
npm install
npx tsc --noEmit
npx vitest run
npm run build

# Backend
python -m pytest tests/
python -m ruff check

# Runtime
npm run dev  # then open browser, test fixture, verify viewer
```

## Post-Integration Branch Cleanup

After Shivam accepts the integration:

**NOT deleted by Aryan** (cleanup is Shivam's decision):
- All 28 historical `feat/aryan-*` branches become purely historical
- They remain on origin for audit trail
- `feat/aryan-integration-ready` is the definitive integration source

## Architecture Satisfaction

| Requirement | Status |
|-------------|--------|
| ONE scientific backend | ✅ src/depthwizard/ (canonical, synced from main) |
| ONE canonical integration layer | ✅ src/depthwizard/integration/ |
| ONE transport representation | ✅ src/transport/ |
| ONE host capability abstraction | ✅ src/host/ |
| ONE application/session lifecycle owner | ✅ src/session/ |
| ONE CameraManager | ✅ src/camera/CameraManager.ts |
| ONE trajectory controller owner | ✅ src/camera/TrajectoryController.ts |
| ONE viewer artifact representation | ✅ src/viewer/Viewer.tsx |
| Frontend never performs science | ✅ boundary tests pass |
| Session never performs science | ✅ invariant test passes |
| Host never performs science | ✅ boundary test passes |
| Flythrough never performs science | ✅ invariant test passes |

## Scientific Invariants

- No terrain/elevation/calibration logic in TypeScript session module
- No CRS/geotransform calculations in frontend
- No DSM generation in frontend
- Backend is sole authority for scientific values
- Frontend owns rendering, camera, interaction, display only

## Dependencies

No new dependencies added during M20–M29.

## License / Provenance

- No external source code copied
- Sat3DGen: audited, no code transferred
- No checkpoints, datasets, caches, or generated scenes committed
- No secrets, API keys, or credentials
