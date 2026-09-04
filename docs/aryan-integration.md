# DepthWizard — Aryan Integration Readiness (Shivam I1)

Canonical backend-to-desktop boundary plus the reconciliation record
for Aryan's vendored Python snapshots. No science, no transport
servers, no frontend changes live here.

## Canonical architecture

```text
main/src/depthwizard            (sole canonical Python implementation)
        ↓  depthwizard.integration (this layer: translate only)
JSON-safe transport (BackendTerrainProduct + ServiceResponse wire)
        ↓  future transport (subprocess JSON / stdio / IPC / HTTP)
Aryan desktop (adapters already consume these shapes)
```

Rules: the desktop never imports Python; Python never depends on
TypeScript; renderers never leak into the engine; the adapter never
recalibrates, rerasterizes, remeshes, reprojects, resamples, changes
units, exaggerates height, or reinterprets semantics.

## Transport rules (verified against Aryan's validators)

- Depth: full field mapping; relative stays relative (`units: null`,
  `depth_scale: "relative"`); metric claims require metres (both
  sides enforce this independently).
- Calibration: scale/offset/reference/units/target/metrics verbatim.
- DSM: invalid pixels become `null` (JSON has no NaN; the desktop
  validator accepts finite-or-null); valid `0.0` preserved; nodata
  serializes as `null` (validity lives in values+mask, documented).
- Mesh: vertices/normals/UVs flat finite lists (non-finite refused
  with `InvalidInputError`); int indices and source mapping exact;
  frame/origin/coverage/units/semantics/spatial/provenance linkage
  preserved; X/Y(up)/Z convention untouched, no axis swaps.
- No `meters: true` field exists anywhere — inspected and confirmed;
  units/semantics strings are authoritative on both sides.
- Counts/dims cross-checked (`3N`/`3T`/`2N`/`N`); origin both-set or
  both-absent with georeferenced-local requiring origin;
  `world = origin + local` reconstructs (tested).
- int64 indices serialize as JSON numbers (exact below 2^53 —
  realistic meshes are orders of magnitude smaller; documented).
- Datetimes become ISO text; tuples become lists; NumPy scalars are
  converted explicitly (the safety scanner uses exact-type checks
  because NumPy scalars subclass Python numerics).
- Pipeline bundles carry status/history/failure/available-kind list
  plus the requested artifact sections and export path — no giant
  array dumps outside explicit dsm/mesh sections.

## Migration path

```text
CURRENT (works, unchanged):
Node → backend_bridge.py → DepthBackend → DepthResult JSON → validate → SceneArtifact

TARGET (this layer enables):
Desktop → LocalService transport → PipelineRunner → artifacts
→ transport adapter → BackendTerrainProduct JSON → Aryan validators → SceneArtifact
```

The current bridge keeps working; migration happens on Aryan's side
when ready. No TypeScript was generated or modified here.

## Snapshot inventory (read-only audit, 2026-09-04)

Canonical source for every row: `main/src/depthwizard/...`.
Nothing below was modified, merged, or deleted by this task.

| Aryan branch @ SHA             | Vendored Python paths                                                                                                                  | Vintage vs main                                                                                                                                                            | Runtime role                                                  | Action on Aryan merge                         |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- | --------------------------------------------- |
| semantic-hardening @ bf6f8eb   | `depthwizard/{__init__,version,errors,contracts/*,ingestion/*,backends/*}`, `tests/{backends,contracts,ingestion}/*`, `pyproject.toml` | Identical to contemporary canonical (verified file-level); stale vs main (predates numpy-promotion, TERRAIN_ELEVATION, pipeline/geospatial errors, from_affine delegation) | Fallback only (bridge prefers real imports; exits if missing) | Remove snapshots; depend on canonical package |
| real-dsm-mesh-viewer @ f857f47 | Above plus `calibration/*`, `dsm/*`, `height/*`, `mesh/*` (+ their tests)                                                              | Identical to contemporary canonical; stale vs main (missing export/pipeline/service/geospatial/dem/controls)                                                               | Fallback only (same pattern)                                  | Remove snapshots; depend on canonical package |

Verification method: `git diff main <branch> -- src/depthwizard/` shows
only deletions relative to main (missing newer files) plus era
differences (numpy dev-vs-runtime, missing enum members/error
classes, pre-delegation converter) — zero Aryan-side modifications
to the copied logic were found.

## Integration risks

- **High — dual-backend drift**: two copies of the Python core exist
  (canonical `main` + Aryan snapshots). Mitigation: reconciliation
  table above; snapshots must go at Aryan-merge time. No code change
  in this task affects it.
- **Medium — transport shape drift**: if Aryan's validators gain
  fields (e.g. stricter nodata rules), the Python adapter must grow
  matching coverage. Mitigation: adapter tests assert the full
  current shape; docs pin the inspected SHAs.
- **Medium — `--terrain-file` producer gap**: the bridge spawns a
  script for terrain JSON; Aryan's vendored bridge script covers
  depth only. Mitigation: this adapter is the canonical producer —
  a future thin CLI/wrapper can call it (not built here, by design).
- **Low — int64 precision**: documented 2^53 bound, far above
  realistic mesh sizes.
- **Low — NaN nodata as null**: documented and validator-compatible;
  mask remains authoritative.
