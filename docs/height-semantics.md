# DepthWizard — Scientific Height Semantics (Shivam S10)

The meaning layer between calibrated numbers and scientific products.
No DEM, no rasters, no export, no meshes — meaning and contract only.

## The semantic chain

```text
RELATIVE DEPTH / RELATIVE SURFACE   (model output, unitless)
        ↓  empirical affine calibration against an explicit reference
CALIBRATED METRIC VALUES            (numbers in metres, still meaning-free)
        ↓  caller-declared target semantics, validated against calibration
SCIENTIFIC HEIGHT / ELEVATION       (AGL height or absolute elevation)
```

Each arrow is a separate concern: the depth model knows ordering,
calibration knows the metre mapping, and **this** layer knows what
the metres mean. A value is never "height in metres" merely because
calibration exists — the product states what the numbers mean, in
what units, from what reference, via what calibration.

## Construction (only sanctioned path)

```python
create_scientific_height_product(depth_result, calibration, target_semantics)
```

There is no `create_product(relative_depth)` overload. The factory
requires: a `RELATIVE` `DepthResult` with relative elevation
semantics (already-metric depth is rejected — re-calibrating metric
output would be unsound); a finite `CalibrationResult` whose target
agrees with the requested product semantics; an explicit-metre
reference; consistent source linkage (depth checksum vs calibration
source checksum: contradiction fails, absence is tolerated, never
over-constrained). Values come from the existing
`apply_calibration(...)` — no second calibration path. The source
`DepthResult` and `CalibrationResult` are never mutated.

## The two product meanings

- `HEIGHT_AGL_NDSM`: height above local/reference ground, metres.
  Never claimed as absolute terrain elevation.
- `ABSOLUTE_ELEVATION_DSM`: elevation relative to the stated vertical
  reference, metres. The contract defines **no vertical-datum field**,
  so no datum is ever fabricated; it is unknown/unavailable by design.

Both reject non-metre units at construction; relative meanings are
rejected as product semantics. Cardinality (`len(values) == width ×
height`, row-major, source grid preserved — never reshaped,
resampled or interpolated) and finiteness are enforced.

## Spatial policy

Spatial metadata is preserved as-is from the depth source.
Calibration changes numeric semantics, never spatial referencing: a
non-georeferenced source yields a non-georeferenced product (no CRS,
transform or bounds invented); a georeferenced source keeps its CRS,
transform, bounds, dimensions and resolution.

## Provenance

`product.provenance` derives from `calibration.to_provenance()` plus
depth-backend identity (model name/version/checkpoint): source
input/checksum, method, reference, `(scale, offset)` params, target
meaning, metres, engine version. No vertical datums, checkpoints,
coordinates, accuracy scores, timestamps or benchmark evidence are
fabricated. The chain model-relative → empirical calibration →
metric values → declared semantics stays reconstructible.

## Why not DEM / GeoTIFF / mesh here

DEM loading, alignment, resampling and terrain normalization need a
geospatial engine (later milestone); raster export and meshing need
format writers. This layer deliberately stops at the in-memory
semantic product so each later engine consumes a meaning-explicit
input instead of raw numbers.

## Future mapping

```text
ScientificHeightProduct
        ↓  future DSM engine (rasterization)
future terrain/DSM artifact (file product)
        ↓  future integration mapping
Aryan artifact/layer system (SceneArtifact elevation / LayerPayloads)
```

The backend stays renderer-independent: no React/TypeScript/Three.js,
no frontend fields on the product. Aryan's layers (`dsm`, `rdsm`,
`agl`), measurement tools and elevation profiles currently sample
fixture grids explicitly marked `fixture-coordinate-system`; backend
metric products will reach them only through a future explicit
artifact mapping — never silently.
