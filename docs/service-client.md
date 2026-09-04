# LocalService Client Boundary

How the frontend talks to the backend application boundary — and what
it deliberately does not do.

## Rules

“The LocalService is the backend application boundary; the frontend
does not call scientific pipeline modules directly.”

“ServiceResponse metadata does not imply artifact payload availability.”

## Architecture

```
InputWorkspace / sources
  → LocalServiceClient (src/service/)
  → SubprocessServiceTransport (stdio JSON, structured argv, no shell)
  → scripts/depthwiz_service.py
  → wire.decode_request → LocalService.execute → wire.encode_response
  → validated ServiceResponse
  → existing processing reducer + adapter + viewer
```

The TypeScript side never imports scientific pipeline modules. The
Python script never implements science: it decodes with the real wire
decoder, executes the real `LocalService` (which owns stage ordering
through `PipelineRunner`), and encodes with the real wire encoder.
Calibration inside the service run comes from an in-process dev
provider mirroring the sanctioned backend test collaborator
(`tests/pipeline/support.py`); the reference id marks it as synthetic
dev data.

## Wire contract (v1)

`SERVICE_CONTRACT_VERSION = "1"` — the client rejects anything else.
Requests carry only backend-supported fields (`input_path`, metric
`target_semantics`, `backend: synthetic-depth`, `preprocessor:
identity`, `build_mesh`, null GeoTIFF path). Responses preserve
`success`, `final_state`, state history, structured failure
(`code`, `message`, `stage` with backend domain categories verbatim),
artifact descriptors, and the run summary (checksums, backend
identity, calibration reference, engine version).

## Control plane vs payload plane

`ServiceResponse` is metadata-first by backend design: descriptors say
what exists, never the arrays. Until the backend exposes artifact
transfer, terrain payloads keep flowing over the frozen legacy bridge
(`--terrain-file` → same validation → same adapter), gated by an
explicit consistency check: the mesh descriptor must report available
with matching semantics, otherwise the run fails with
`MESH_UNAVAILABLE` / `DESCRIPTOR_MISMATCH` instead of rendering
anything. Service lifecycle integration is therefore complete while
artifact payload transfer remains a backend transport extension —
tracked here, not hidden.

## Stages, progress, cancellation

The service is synchronous: no live stages, no percentages, no job
IDs. The UI shows indeterminate processing; on completion the
response `states` history maps onto the existing stage vocabulary
(`input_validated` → loading; terminal/export-only states dropped).
Cancellation is transport-level (process termination → existing
`cancelled` state), because backend cancellation tokens are
in-process only and never serialized — `ServiceRequest` carries no
cancellation field, honestly.

## Capabilities

Single source: `LocalService.capabilities()` (suffixes, metric
targets, backends, mesh/GeoTIFF flags). The input workspace renders
supported formats from it; the client defaults the dev target to
`absolute_elevation_dsm`. The legacy `--capabilities` bridge mode
remains for transport diagnostics only.

## Semantics preserved

Relative depth never gains metric claims (descriptors carry
`units: null` / `relative_depth` untouched); metric products render
metres only when descriptors say `meters`; CRS/transform/bounds/GSD
flow through the existing adapter untouched; height exaggeration stays
a renderer-only `scale.y`.

## Future Tauri mapping

`ServiceTransport` is the seam: stdio today, Tauri command tomorrow.
`LocalServiceClient` speaks parsed JSON documents either way, so only
the transport implementation changes. No Tauri tooling is installed in
this environment, so no IPC is implemented here.
