# DepthWizard — Terrain Mesh Engine (Shivam S13)

Renderer-independent triangulation of validated DSM grids. No
display, camera, interaction, export or file concepts live here.

## Path

```text
DSMGrid (validated float raster + validity mask)
        ↓  build_terrain_mesh() — deterministic, in-memory
TerrainMesh (vertices / indices / normals / UVs / mapping / metadata)
        ↓  (future adapter — not this milestone)
SceneArtifact.mesh (renderer-owned Float32Array form)
```

## Coordinate convention

`X` = horizontal source-axis 1, `Y` = scientific elevation/height,
`Z` = horizontal source-axis 2. Y carries the exact source raster
value: never exaggerated, normalized, shifted, clipped or
re-centered. No height exaggeration exists anywhere in this layer.

- Georeferenced grids (`CoordinateFrame.GEOREFERENCED_LOCAL`):
  planar positions derive from pixel centers `(c + 0.5, r + 0.5)`
  through the stored GDAL-order affine, expressed relative to the
  explicitly stored local origin (the affine translation terms), so
  `world = origin + vertex` reconstructs exactly. CRS, transform,
  bounds and resolution pass through unchanged; nothing is
  reprojected, resampled, warped or aligned.
- Anything else (`CoordinateFrame.LOCAL`): deterministic pixel-local
  coordinates (`x = column`, `z = row`) with no CRS claims. This also
  covers the explicit fallback where a CRS exists but no transform
  can place pixels — the CRS stays preserved in metadata while the
  frame documents that no metric horizontal distance is claimed.
- Geographic CRS caution: source CRS strings and values pass through
  untouched; degrees are never converted to metres and no projection
  is performed. Only vertical `units = "meters"` is ever claimed.

## Pixel-center and vertex policy

One vertex per valid pixel at its center — never interpolated
corners. Vertices compact valid pixels in row-major order with
`vertex_source_indices` mapping each vertex to its flat row-major
DSM pixel (the picking/measurement/provenance link). Invalid pixels
produce no vertices and participate in no faces.

## Holes and winding

A triangle exists only if all required source pixels are valid —
holes are never bridged, filled or interpolated (a 3×3 with an
invalid center therefore yields no quads at all and fails
explicitly). Per quad: `(i00, i10, i01)` and `(i10, i11, i01)` with a
deterministic handedness flip when the planar mapping determinant is
negative (e.g. north-up rasters), keeping normals upward in both
frames. Degenerate (zero-determinant) planar mappings fail instead
of producing collapsed geometry. Fully valid H×W grids yield exactly
`2·(H−1)·(W−1)` triangles; `coverage` reports the achieved share
(topology share only — never accuracy or confidence).

## Normals and UVs

Face normals accumulate area-weighted onto vertices (vectorized,
fixed order) and normalize; isolated vertices and zero-area
contributions fall back deterministically to vertical `(0, 1, 0)`.
Flat terrain yields exactly upward normals in both frames. All
published positions and normals are finite (validated). UVs are
`u = c/(W−1)`, `v = r/(H−1)` display coordinates in `[0, 1]`
(0.0 on degenerate 1-wide axes, which cannot triangulate anyway) —
never geographic coordinates, never texture sampling.

## Indices and statistics

int64 indices (future-large-grid safe; renderer adapters downcast),
validated non-negative, in-range and `len % 3 == 0`. Statistics
(vertex/triangle counts, valid/invalid pixels, skipped cells,
coverage) describe topology only. Grids below 2×2, with zero valid
pixels, or with no complete quad fail with `MeshGenerationError`
(carrying dimensions and counts); empty meshes are unsupported by
contract, not emitted.

## Ownership and meaning

Factories allocate fresh arrays; sources (`DSMGrid`, products,
calibration, provenance, spatial) are never mutated. Units,
semantics, model identity, calibration scalars, source linkage and
the full provenance record pass through unchanged — meshing is
representation, not calibration or reinterpretation. No vertical
datum is added; no exaggeration, decimation, LOD, contours, slope or
hillshade exists here.

## Dependencies

NumPy only (already a direct runtime dependency): arrays, masks,
cross products, accumulation. No trimesh/Open3D/PyVista/CGAL/GPU
frameworks — regular-grid topology is implemented transparently
(~fixed-order vectorized ops, no parallelism, fully deterministic).
No third-party code copied; the frontend fixture's display-side
triangulator was reviewed for topology conventions only.
