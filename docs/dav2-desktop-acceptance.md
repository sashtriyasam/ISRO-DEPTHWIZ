# Real DA-V2 Desktop Integration Acceptance

## Boundary defect found and fixed

The desktop could not select the real backend. Three hardcoded
`synthetic-depth` selections blocked the path (canonical `main`):

| #   | Location                                                                              | Fix (backward compatible)                                                                                                                                         |
| --- | ------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `scripts/backend_bridge.py` hardcoded `SyntheticDepthBackend`                         | `--backend` / `--device` flags, default `synthetic-depth`; unknown or asset-less backends fail loudly, never substitute                                           |
| 2   | `LocalServiceClient.buildRequest` hardcoded `backend`                                 | optional `backend` arg, default `synthetic-depth`                                                                                                                 |
| 3   | `ServiceRequest.backend: Literal["synthetic-depth"]` rejected real backends at decode | widened to `str`; `LocalService` already rejects unknown backends loudly                                                                                          |
| 4   | `depthwiz_service.py` registered synthetic only                                       | registers `depth-anything-v2-small` when upstream source + torch are discoverable and an external checkpoint exists (no heavy imports); capabilities stay factual |

Plumbed through (all optional, defaults preserve existing behavior):
`FileInputSourceOptions.backend` → `TerrainFetchRequest.backend` →
`ServiceArtifactTransport` (control plane + payload plane) →
`BackendBridgeOptions.backend` / per-call override → `--backend` CLI flag.

No model, contract, calibration, DSM, mesh, or adapter semantics changed.
The bridge dev calibration is now fitted to the backend's actual depth
values with the same deterministic rule (`reference = 2.5x + 10`,
`synthetic-dev-ref`); for synthetic output the numbers are identical to
the previous fixed fit (scale 2.5, offset 10).

## Acceptance runs (real DA-V2 Small, CPU)

`src/backend/realDav2Acceptance.test.ts` (gated: `DW_DAV2_ACCEPT=1`):

| Test                                                                         | Result                                                                                                                                    |
| ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Real terrain artifact via `FileInputSource` (32×32)                          | pass (~17 s): id `backend-depth-anything-v2-small-terrain`, metric elevation 32×32, 1024 finite-Y vertices, calibration reference present |
| Camera framing + metric-safe measurement + exaggeration immutability (16×16) | pass (~12 s): finite bounding sphere, finite frame position, source vertices bit-identical after ×10 exaggeration                         |
| CRS/transform preservation, RGB GeoTIFF 4×4 EPSG:32643                       | pass (~13 s): CRS, origin (100, 200), pixel width 0.5 preserved into artifact metadata                                                    |
| Unknown backend fails loudly, no synthetic substitution                      | pass (~0.5 s): `success: false`, errors present, no artifact                                                                              |

Bridge CLI (`--backend depth-anything-v2-small --terrain-file`, 64×64):
relative depth (units null) → metric DSM 64×64 → mesh 4096 v / 7938 t,
stages `preprocessing → inference_running → calibrating →
 dsm_generation → mesh_generation`. Missing checkpoint and unknown backend
both exit non-zero with JSON errors.

## Semantics confirmed

Raw DA-V2 stays `relative` / units null / `relative_depth`; metric appears
only after explicit calibration (adapters reject metric-without-meters and
relative-claiming-meters on both planes). CRS/transform/bounds pass through
verbatim. Height exaggeration is display-only (source arrays untouched;
measurement/profile independent of exaggeration).

## Not verified

In-browser WebGL rendering (no browser automation in this environment);
GPU performance; field accuracy. Vitest baseline unchanged by this task
(498 passed / 87 failed before and after; failures are pre-existing DOM
queries plus Windows `python`-on-PATH spawn failures, unrelated).
