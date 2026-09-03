# DepthWizard — Depth Backend Boundary (Shivam S5)

Executable backend abstraction with a deterministic synthetic
implementation. No neural models, checkpoints, GPU or network.

## The executable path

```text
validated input
      ↓ inspect_input()
InputInspection
      ↓ DepthBackend.estimate_depth(inspection)
DepthResult
```

`DepthBackend` (in `contracts/artifacts.py`) is the single backend
protocol: `model_name` / `model_version` / `checkpoint_id` plus
`estimate_depth(inspection)`. It takes the validated `InputInspection`
value object — not an opaque string id — so backends are stateless:
no registry, cache, database or lookup is needed to execute. (The
protocol originally took `input_id: str`; S5 changed the parameter
type for exactly this reason. No second protocol was created and no
public type was renamed.)

## SyntheticDepthBackend (fixture only)

`backends/synthetic.py` implements the protocol with a closed-form
pattern — a normalized separable sinusoid over the input grid,
stdlib `math` only:

```text
v(col, row) = 0.5 * (1 + sin(2π·col/W) · cos(2π·row/H))  ∈ [0, 1]
```

Rules it obeys (enforced by tests):

- Always `RELATIVE` scale, `RELATIVE_DEPTH` semantics, `units=None` —
  never metres, never absolute elevation.
- Output grid equals the input grid (no resampling stage exists yet).
- Input georeferencing/spatial metadata is preserved as-is: PNG/JPEG
  stay `NON_GEOREFERENCED` with no CRS; a CRS-bearing GeoTIFF stays
  `GEOREFERENCED_NO_ELEVATION_REFERENCE` with identical spatial
  details. Nothing is upgraded or invented.
- Provenance records input display name + SHA-256, backend name/
  version, software version and an explicit synthetic marker.
  `checkpoint_id` is None (no checkpoint exists), `generated_at` is
  None (timestamps would break bit-determinism), calibration fields
  are None (nothing was calibrated).
- Non-`InputInspection` input raises `TypeError` (precondition, not
  inference). `ModelInferenceError` is reserved for genuine execution
  failures in real backends; the synthetic path has no fallible
  external calls by construction, so no fake failure logic was added.
- Read-only: inputs unmodified, no files written, no network/GPU/
  weights.

`SyntheticDepthBackend` is development/test infrastructure. It is not
scientifically valid inference and must never be treated as a
production model — its name, version and provenance say so.

## Shravan progression (not implemented here)

```text
SyntheticDepthBackend
        ↓  (same DepthBackend boundary)
Shravan model adapter  →  real DepthResult (RELATIVE or calibrated METRIC)
        ↓
calibration / height semantics (later Shivam milestone)
```

A future adapter implements `estimate_depth(inspection)` and returns
`DepthResult`; orchestration code never branches on backend identity.
Model-specific dependencies (torch, transformers, checkpoints) must
live with the adapter, never in the core engine (`pydantic`, `Pillow`,
`rasterio` only — unchanged in this milestone).

## Renderer independence

The backend imports no React/TypeScript/Three.js and adds no
frontend mesh/layer fields to `DepthResult`. Future DSM/AGL/mesh
products will map into Aryan's artifact pipeline (`SceneArtifact`,
`LayerPayloads`) at integration time, not in this model.
