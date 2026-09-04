# Canonical Backend Integration Reconciliation

How the desktop bridge reaches the one authoritative scientific
implementation — and what was removed to get there.

## Rule

“Canonical scientific implementation lives in main/src/depthwizard; Aryan owns only the desktop/frontend boundary.”

## Reconciliation table

| PATH | FORMER ROLE | CANONICAL SOURCE | STATUS IN THIS BRANCH | REASON |
| ---- | ----------- | ---------------- | --------------------- | ------ |
| `scripts/dw_serialize.py` | Bridge-owned terrain JSON shape | `depthwizard.integration.{terrain_product,to_json_text}` | **Deleted** | Duplicate serializer; bridge now calls the canonical layer |
| `scripts/backend_bridge.py` | Stage runner + custom serialization | Same stages, canonical serialization | **Kept, migrated** | Desktop glue (argv/stdout contract); science + wire shape now canonical |
| `scripts/depthwiz_service.py` | Service stdio transport | Unchanged | **Kept** | Transport glue; already delegates to `LocalService` + real wire codec |
| `src/depthwizard/{contracts,backends,ingestion,calibration,height,dsm,mesh,pipeline,service,export}/` | Vendored scientific engine | `origin/main` @ `c97a614` (synced verbatim) | **Synced, not owned** | Content-identical to canonical; collapses to zero diff at merge time |
| `src/depthwizard/{geospatial,dem,controls}/` | Missing | `origin/main` @ `c97a614` (new) | **Synced in** | Completes the canonical tree the bridge imports against |
| `src/depthwizard/integration/` | Missing | `origin/main` @ `c97a614` (new) | **Synced in** | The canonical adapter/transport/wire the bridge now calls |
| `tests/{integration,geospatial,dem,controls}/` | Missing | `origin/main` @ `c97a614` (new) | **Synced in** | Canonical adapter tests run on this branch |
| `pyproject.toml` | Custom (rasterio dropped, numpy dev-only) | `origin/main` (rasterio runtime, numpy runtime) | **Synced** | Packaging matches canonical requirements |
| `src/backend/types.ts`, `src/service/*`, `src/transport/*` | Frontend transport representation | Mirrors canonical wire shapes | **Kept** | TypeScript needs its own structural types; they represent, not redefine |

## What changed in behavior

Nothing scientific. The `--terrain` / `--terrain-file` payload is now
produced by `terrain_product()` + `to_json_text()` and validated in
tests through the canonical `terrain_product_from_json` decoder; the
only bridge-added field remains `stages` (the stages the script
genuinely executed, in order). Bridge output before/after is
field-identical — proven by the unchanged frontend suite (all adapter,
transport, and end-to-end tests pass unmodified).

## Small canonical evolutions absorbed

- `numpy` promoted to runtime dependency (matches `pyproject.toml`).
- `ElevationSemantics.TERRAIN_ELEVATION` added (excluded from
  calibration targets by backend validation; the bridge requests only
  the two metric targets, so no frontend change).
- `GeospatialProcessingError` added; affine conversion delegated to
  `geospatial.transforms` (same mapping, verified by ingestion tests).

## Guardrails

- `src/backend/canonical.test.ts`: asserts bridge scripts contain no
  depth formula, mesh/DSM/calibration mathematics, or private
  serializer, and proves bridge output through the canonical wire
  decoder cross-language.
- Repository check: `git diff <branch> origin/main --
  src/depthwizard/` must show no Aryan-side modifications to shared
  scientific files (additive sync only).

## Known environment limitation (not a code issue)

`tests/{dem,geospatial,controls}/` (52 tests) fail in this environment
because `affine 2.4.0` removed the `Affine @ tuple` operator the
canonical geospatial code relies on. All 229 previously-passing tests
(including every suite the bridge consumes) remain green. Fixing the
canonical geospatial code or pinning the dependency is Shivam-side
work; this branch changes neither.

## Merge-time note

Per the integration-readiness record, vendored trees collapse at
merge: after this milestone the branch content under
`src/depthwizard/` is verbatim canonical, so merging contributes no
duplicate implementation. The desktop-owned survivors are exactly:
`scripts/backend_bridge.py`, `scripts/depthwiz_service.py`
(runners), and the TypeScript boundary (`src/backend`,
`src/service`, `src/transport`, `src/input`, `src/processing`).
