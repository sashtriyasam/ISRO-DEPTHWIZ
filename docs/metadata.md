# Scientific Metadata Workspace

How DepthWizard presents authoritative backend facts — without
computing any.

## Rule

“The metadata workspace displays authoritative backend facts; it does
not compute or infer scientific metadata.”

## Source of truth

Every displayed value is either backend-provided (transport →
adapter → `SceneArtifact.metadata`) or a pure formatting of one
(number → string, checksum truncation, enum → label). The derivation
layer (`src/metadata/metadata.ts`) is a pure function of
`(artifact, activeLayerId)`:

- it never reads the elevation grid or mesh arrays (a 1M-cell grid
  produces under 3KB of metadata — asserted in tests);
- it never sees the height-exaggeration level, so display transforms
  cannot alter metadata (asserted);
- it replaces the artifact atomically with the terrain, so stale
  metadata can never linger.

## What is preserved (and was previously dropped)

The adapters now carry through, via a shared mapper
(`src/backend/spatialMeta.ts` used by both adapters):

- spatial details: GSD, nodata (explicit `0` stays distinct from
  absent), raster dimensions, spatial units, source tag, the raw
  6-parameter backend affine (GDAL order), and 2D spatial bounds;
- provenance: input id, input checksum, software version, semantic
  meaning;
- calibration scale and offset alongside method and reference.

Known gap (documented, not worked around): the input file *format* is
not part of any backend product contract, so the artifact cannot
report it — the input workspace shows it from the inspection step
instead. Proposed additive field for Shivam if wanted: `input_format`
on product provenance.

## Panels

- **Metadata** (`MetadataPanel`): Product / Spatial / Calibration /
  Provenance / Input sections in native keyboard-accessible
  `<details>` collapsibles, derived per render from the current
  artifact and active layer (rDSM/AGL payloads switch the product
  rows; missing payloads show nothing rather than stale data).
- **SceneInfo**: artifact status, label, backend product line, geometry
  counts, unit-aware grid description.
- **Inspector**: scientific value with semantic label and metric-only
  unit suffix, backend CRS row when present, and display coordinates
  explicitly labeled as scene units — never Easting/Northing.
- **ProfileChart**: axis titles and accessible description follow the
  profile's own `units`/`elevationSemantics` (`Elevation (m)` vs
  `Relative depth (relative)`); distance follows product units.

## Missing data

One fallback everywhere: `Not available`. Never `0`, `N/A`,
`unknown`, or empty strings — and `0`/`NaN` values are never
conflated with absence (`NaN` renders as `NaN (nodata marker)`).

## Spatial vs display coordinates

- **Spatial**: CRS, georeferencing level, affine, spatial bounds, GSD —
  backend facts, descriptive only (no transformation in React).
- **Display**: Three.js X/Y/Z bounds and inspector positions —
  labeled as scene/display values with no unit claims.

## Source coherence

One status rule (`sourceStatusLabel`): fixture → “Development
fixture”; `synthetic-depth` backend → “Synthetic Development
Backend”; any other model → neutral “Backend model (name)” — never
“Production” or “AI Prediction” unless actually true.

## Reference data readiness

Backend DEM/reference modules exist but no reference fields flow into
the consumed product contracts (calibration *reference id* is the only
reference carrier, and it is displayed). The workspace will render
reference source/CRS/alignment if a future contract carries them —
no fake fields were added.
