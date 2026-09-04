# Artifact Payload Transport

How backend-generated DSM/mesh products travel from `LocalService`
to the viewer — and the boundary that keeps the wire contract honest.

## Rules

“ServiceResponse remains metadata-first; artifact payloads are
transferred through an explicit artifact transport.”

## Why two planes

`LocalService.execute()` returns `ServiceResponse`: success, final
state, state history, structured failure, artifact descriptors, run
summary. By backend design it never carries depth/DSM/mesh arrays,
and in-memory products die with the service process — so a later
“fetch by handle” request cannot work (there is no artifact store,
and no handle would outlive its process).

The frontend therefore pairs, per run, two real executions of the
same deterministic chain:

1. **Control plane** — `ServiceRequest` → `LocalService` →
   validated `ServiceResponse`. Authoritative for success, states,
   failures, and what exists (descriptors).
2. **Payload plane** — the frozen legacy `--terrain-file` path
   returns the actual arrays for the same input.

Determinism makes this exact rather than approximate, and the
transport *verifies* rather than trusts (below). No backend code was
changed; no wire version was bumped; the `v1` response shape is
untouched.

## Transport (`src/transport/`)

```
ServiceResponse + descriptors
  → ServiceArtifactTransport.fetchTerrain()
  → descriptor gate (no mesh available → ARTIFACT_UNAVAILABLE, no payload run wasted)
  → payload fetch (same input, same deterministic chain)
  → verifyBundle(): checksum linkage + descriptor agreement
  → ArtifactResolver.resolveTerrainArtifact() → SceneArtifact
```

- **Checksum linkage**: `summary.input_checksum` must equal the
  payload's `source_checksum` when both are present. A break means the
  payload is not from the described run → `CHECKSUM_MISMATCH`.
- **Descriptor agreement**: mesh semantics/units/dimensions must match
  the payload → `DESCRIPTOR_MISMATCH`.
- **Resolver**: reuses the existing validated adapter; malformed
  payloads surface adapter codes as `RESOLUTION_FAILED` with detail.
- **Taxonomy** (never flattened): `SERVICE_UNAVAILABLE`,
  backend domain codes verbatim (`InvalidInputError`, …),
  `ARTIFACT_UNAVAILABLE`, `PAYLOAD_FAILED`, `CHECKSUM_MISMATCH`,
  `DESCRIPTOR_MISMATCH`, `RESOLUTION_FAILED`, `OPERATION_CANCELLED`.
- The transport owns no temp files (payloads travel over stdout) and
  creates no caches; staged input files stay owned by the input
  workspace with cleanup on replace/clear/unmount/failure.

## Identity and lifetime

Artifact ids are content-derived (`file-<sha256>`); the backend
records input checksums end to end (input → calibration → mesh
provenance). Ownership chain: backend product → transport payload
(parsed once) → `SceneArtifact` → Three.js `BufferGeometry`
(disposed on scene replacement via the existing viewer lifecycle).
No React state holds raw arrays beyond the artifact itself.

## What the UI shows

Only backend-provided facts: product kind from elevation semantics
(DSM/AGL/relative), units only when the backend declares metres,
model name, calibration reference, CRS/bounds where present. Height
exaggeration remains a renderer-only `scale.y`; scientific values are
never touched by transport or display.

## Proposal for Shivam (no change implemented)

If a future contract should unify the planes, the smallest clean
options are: (a) a content-addressed payload reference on the mesh
descriptor (`payload_ref` + `payload_checksum`, optional and
backward-compatible with v1), or (b) a companion payload endpoint
served by a long-lived local service. Until one lands, this transport
is the sanctioned path — checksums enforced, limitations stated.

## Tauri mapping

`ArtifactTransport` is transport-neutral: stdio today, Tauri command
tomorrow. Only `ServiceArtifactTransport` changes; resolver,
validator, UI, and processing states are untouched.
