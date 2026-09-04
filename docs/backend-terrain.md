# Backend Terrain Products (DSM + Mesh)

How DepthWizard consumes backend-generated terrain — and what the
frontend must never do itself.

## Rule

“The frontend renders backend-generated terrain products; it does not
generate DSMs or scientific terrain data.”

“Backend scientific semantics are preserved end-to-end; the frontend
must never infer scientific units or product type from numeric values
alone.”

“The synthetic backend is executable test infrastructure, not
production inference.”

## Pipeline (all stages run in Python)

```
synthetic input (PNG)
  → SyntheticDepthBackend.estimate_depth()      (DepthResult, RELATIVE)
  → deterministic dev calibration               (scale_offset, ref synthetic-dev-ref)
  → create_scientific_height_product()          (metric, ABSOLUTE_ELEVATION_DSM)
  → rasterize_height_product()                  (DSMGrid, 1:1, NaN nodata)
  → build_terrain_mesh()                        (TerrainMesh, Y-up)
  → JSON transport (--terrain mode)
  → BackendBridge.executeTerrain()              (TypeScript, process boundary)
  → validateTerrainShape() + adaptTerrainProduct()
  → SceneArtifact                               (real backend mesh)
  → Three.js viewer (createLayerMesh)
```

The dev calibration mirrors the sanctioned backend test helper
`tests/height/support.py::exact_calibration` (2.5x + 10 against
reference `synthetic-dev-ref`); the fit itself is always computed by
the real `ScaleOffsetCalibrator`. No depth formula, rasterization rule,
or triangulation rule exists anywhere in TypeScript for backend
products.

## Product contract (transport)

`BackendTerrainProduct = { kind: "terrain", depth_result, dsm, mesh }`

- `dsm`: width, height, dtype, units (`"meters"`), semantics (metric
  only), row-major `values` (NaN nodata → `null`), `valid_mask`,
  `invalid_count`, georeferencing, spatial context.
- `mesh`: flat `vertices`/`indices`/`normals`/`uvs`,
  `vertex_source_indices` (vertex → DSM pixel), counts, `coverage`,
  `frame`, origin, units, semantics, calibration + provenance metadata.

Validation rejects: bad dimensions, length mismatches, out-of-range
indices, non-metric units/semantics, unknown frames, missing origins
for georeferenced frames, mesh/DSM disagreements.

## Coordinate conventions

| Side    | Convention                              |
| ------- | --------------------------------------- |
| Backend | `TerrainMesh` vertices `[x, y, z]`, **Y = elevation** |
| Frontend| X/Z horizontal, **Y vertical**           |

The conventions are identical, so the mesh adapter copies values
verbatim — there is exactly one place where this is documented
(`src/backend/meshAdapter.ts`), and no axis swap exists anywhere.

- `frame: "local"`: `x = column`, `z = row` (non-georeferenced dev
  fixture). Horizontal metric distance is never claimed.
- `frame: "georeferenced_local"`: raster-transform pixel centers
  relative to the stored origin (`world = origin + vertex`); source
  CRS is preserved unchanged in `spatial`.
- `uvs` are normalized display coordinates in `[0, 1]`, used directly
  by the renderer.

## Scientific vs render data

- `SceneArtifact.elevation` keeps the authoritative DSM raster
  (Float32 grid, `unit: "meters"`, NaN nodata preserved).
- `SceneArtifact.mesh` carries the backend-generated surface for
  rendering (vertices, backend normals, backend UVs).
- `SceneArtifact.metadata.bounds` is computed from backend vertices.
- Height exaggeration applies only via `mesh.scale.y` in the viewer;
  source vertices, semantics, units, and provenance are never mutated
  (covered by `src/display/semantic.test.ts`).

## Layer mapping

Backend semantics drive the labels (`getSemanticLayerLabel`):

- `absolute_elevation_dsm` → **DSM**
- `height_agl_ndsm` → **AGL**
- `relative_surface_rdsm` → **rDSM**
- `relative_depth` → **Relative Depth**

Only layers backed by actual backend data are exposed.

## Status UI

The Source panel distinguishes the **Synthetic Backend** (development
fixture: `synthetic-depth`, dev calibration `synthetic-dev-ref`) from
any future production backend. Metric units (`m`) appear only when the
backend declares `depth_scale: "metric"` with `units: "meters"`.

## Future production path

`BackendBridge` spawns the bridge script today; the same
`executeTerrain()` boundary maps cleanly onto Tauri IPC later. A real
model adapter only needs to satisfy the existing `DepthBackend`
protocol — the frontend never learns about checkpoints, weights, or
inference runtimes.
