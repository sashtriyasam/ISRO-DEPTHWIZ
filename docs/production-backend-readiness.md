# Production Backend Readiness (M23 truth record)

No marketing language below. Every claim was verified against the
repository; anything unverifiable is marked as such.

## 1. What backend implementations actually exist today?

Exactly one `DepthBackend`: `SyntheticDepthBackend`
(`src/depthwizard/backends/synthetic.py`) — a deterministic analytic
sinusoid in `[0, 1]`, no weights, no network, no GPU. Verified by
enumerating `estimate_depth` implementations across the backend
branches and `origin/main`. No model adapters exist anywhere.

## 2. Which one is synthetic/development?

`synthetic-depth` (model version `0.1.0`, no checkpoint). The UI
labels it `Synthetic Development Backend` from a single constant
(`APPLICATION_BACKEND_LABEL`); no other backend identity exists in
the frontend.

## 3. Is a production model executable today?

No. There is nothing to execute: no checkpoint files, no inference
runner, no registry, no Shravan branches in the repository. The
application never claims otherwise — there is no production option,
dropdown, model name, or "AI" label anywhere in the UI.

## 4. Which branch/source provides each implementation?

`src/depthwizard/` on this branch is content-identical to
`origin/main` (verified: `git diff origin/main -- src/depthwizard/
tests/ pyproject.toml` is empty). The engine is Shivam-owned;
Aryan-owned code is the desktop boundary only (`scripts/*`,
`src/{backend,service,transport,input,processing}/`, UI).

## 5. What is the canonical runtime path?

Staged input file → `LocalServiceClient.buildRequest` (contract v1,
`synthetic-depth`, `identity`, metric target, mesh on) →
`depthwiz_service.py` stdio transport → `LocalService.execute` →
`PipelineRunner` → validated `ServiceResponse` → descriptor gate →
deterministic payload run → checksum/descriptor verification →
`adaptTerrainProduct` → `SceneArtifact` → viewer. No step is skipped,
no step is faked, and a production request can never silently become
synthetic output because no production request path exists.

## 6. What conditions make a backend unavailable?

- Service process cannot start (`SERVICE_UNAVAILABLE`, retryable).
- `available_backends` does not list `synthetic-depth`
  (deterministic `UNAVAILABLE` state, Generate disabled, no
  substitution — proven by test).
- Input rejected (`InvalidInputError` / `UnsupportedFormatError`
  with stage, previous terrain retained).
- Payload/descriptor disagreement (`DESCRIPTOR_MISMATCH`,
  `CHECKSUM_MISMATCH`, `MESH_UNAVAILABLE`, `PAYLOAD_FAILED`).
- Cancellation (`OPERATION_CANCELLED`, never reported as failure).

## 7. Does the app ever silently fall back?

No. Verified by repository search and test: every failure path
throws a structured error; the fixture button is an explicit,
labeled development choice, not a fallback; unknown backends resolve
to kind `unknown`, never to synthetic.

## 8. What remains blocked on Shravan?

A production model adapter: an implementation of the existing
`DepthBackend` protocol (`model_name`, `model_version`,
`checkpoint_id`, `estimate_depth(inspection) -> DepthResult`),
registered in `LocalService`'s backend map. No new frontend work is
needed to consume it beyond the identity display already driven by
capabilities.

## 9. What remains blocked on Shivam?

- Long-lived artifact transfer (today: deterministic re-execution +
  checksum verification, documented in `docs/artifact-transport.md`).
- Reference DEM/GCP acquisition (calibration references are
  developer-supplied today).
- The `affine 2.4.0` incompatibility failing 52 geospatial/DEM/
  controls tests (environmental, outside consumed paths).

## 10. What can Aryan complete independently?

Desktop packaging groundwork (Tauri policy/tooling still absent),
trajectory UX refinements, and any presentation work that consumes
already-exposed contracts. Nothing requiring model weights,
reference data, or wire-contract changes.

## 11. What exact interface must a future production model adapter satisfy?

The existing backend seam — no new abstraction was or will be
invented on the frontend for this:

INPUT: a validated `InputInspection` (dimensions, checksum, spatial
semantics — never raw paths or opaque ids, never pixel blobs in the
contract).

OUTPUT: a `DepthResult` with honest `DepthScale`/`ElevationSemantics`
(metric claims require metre units and a calibration reference),
plus `model_name`, `model_version`, optional `checkpoint_id`, and
deterministic errors from the existing taxonomy
(`ModelInferenceError` et al.).

The adapter MUST NOT own UI logic, Three.js rendering, CRS
invention, frontend calibration, or viewer state. Registration is
Shivam-side (`LocalService` backend map); discovery is automatic via
`capabilities().available_backends`, which the UI already renders
without a hardcoded list.
