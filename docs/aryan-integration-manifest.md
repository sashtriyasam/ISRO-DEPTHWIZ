# Aryan Integration Manifest

Generated: 2026-09-04

## Current Aryan Integration Branch

```
feat/aryan-session-correctness
d781621f0ad185047208d72dc26f83de127e1583
```

## Base

```
origin/main: c97a614 (feat/integration): add canonical Aryan backend adapter
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

## Recommended Shivam Integration Order

The Aryan stack can be integrated as **one coherent unit**. There is no need for sequential branch merging.

### Option A: Single Merge (Recommended)

Merge `feat/aryan-session-correctness` into `feat/shivam-aryan-integration-readiness`:

```
git checkout feat/shivam-aryan-integration-readiness
git merge feat/aryan-session-correctness
```

This brings in the complete M01–M28 desktop stack in one operation.

### Option B: Cherry-Pick Individual Milestones

If a staged approach is preferred:

| Unit | Base | Depends On | Touches | Risk | Validation |
|------|------|-----------|---------|------|-----------|
| M20 rendering modes | M19 | rendering controls | src/components/RenderingControls | Low | Visual |
| M21 flythrough | M20 | camera system | src/flythrough/, src/camera/ | Medium | CDP test |
| M22 canonical integration | M21 | backend sync | scripts/, src/backend/ | High | Backend boundary |
| M23 backend hardening | M22 | source descriptors | src/backend/sourceDescriptor | Low | Unit tests |
| M24 flythrough UX | M23 | flythrough | src/components/FlythroughPanel | Low | Visual |
| M25 visual validation | M24 | flythrough | CDP test | Low | Runtime |
| M26 desktop host | M25 | host detection | src/host/ | Low | Unit tests |
| M27 project session | M26 | app state | src/session/, src/app/ | Medium | Unit tests |
| M28 session correctness | M27 | session | src/session/ | Low | Unit tests |

**Option A is strongly preferred** because the Aryan stack is a single linear chain with no parallel work.

## Post-Integration Branch Cleanup

After Shivam accepts the integration:

**NOT deleted by Aryan** (cleanup is Shivam's decision):
- All 27 historical `feat/aryan-*` branches become purely historical
- They remain on origin for audit trail
- `feat/aryan-session-correctness` becomes the definitive integration source

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

No new dependencies added during M20–M28.

## License / Provenance

- No external source code copied
- Sat3DGen: audited, no code transferred
- No checkpoints, datasets, caches, or generated scenes committed
- No secrets, API keys, or credentials
