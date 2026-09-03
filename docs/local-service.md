# DepthWizard — Local Service Contract (Shivam S15)

Thin, typed, transport-neutral application boundary over
`PipelineRunner`. No science, no sockets, no auth, no database.

## Shape

```text
Client
  ↓  ServiceRequest (JSON-safe)
LocalService
  ↓  PipelineRunner.run()
PipelineResult
  ↓  wire mapping
ServiceResponse (JSON-safe)
  ↓
Client
```

`LocalService.execute(request, calibration_provider,
cancellation=None)` validates the request, translates it to a
`PipelineRequest`, runs exactly one fresh `PipelineRunner`, and maps
the result. It never calls inference, rasterization, mesh, or export
functions directly — the pipeline owns stage ordering. Synchronous
by design; a future transport may wrap it asynchronously outside.

## Wire contract (version "1")

`SERVICE_CONTRACT_VERSION = "1"` versions the wire shapes only —
distinct from engine, package, and model versions. Shapes use enum
strings, lists (never tuples), explicit optionals, and no NumPy,
callables, or pickle. Canonical text encoding is UTF-8 JSON
(`wire.py`: `encode/decode_request/response`).

`ServiceRequest`: input path, metric target semantics, backend id
(`"synthetic-depth"`, the only supported value today), preprocessor
id (`"identity"`), mesh flag, optional GeoTIFF path, lossless export
options. Structural validation only (blank paths, non-metric
targets); domain semantics stay in the pipeline layers.

`ServiceResponse`: success flag, final state string, state history,
optional structured failure, six artifact descriptors
(depth/calibration/height/dsm/mesh/geotiff — absent stages stay
explicitly absent), and a scalar run summary. Arrays are never
serialized: responses stay metadata-first (a full mesh/export run is
a few kilobytes of JSON).

## Artifacts and lifetime

Descriptors report kind, availability, persisted flag, path (GeoTIFF
exports only), semantics, units, dimensions, and georeferenced
status. Depth/calibration/height/DSM/mesh are in-memory
(`persisted: false`, no path); only an actually written GeoTIFF is
`persisted: true` with its path. Relative depth stays identifiable
as relative (`units: null`, `relative_depth`) — calibrated metric
artifacts carry metres plus their declared meaning.

## Errors

Domain categories survive verbatim as the error code
(`InvalidInputError`, `ModelInferenceError`, `CalibrationError`,
`MeshGenerationError`, `ExportError`, …) with stage and message —
never flattened to `SERVICE_ERROR`. No retryable flag: retryability
cannot be defined honestly for scientific failures. Failure messages
carry display basenames only (no tracebacks, no internal paths).

## Selection without callables

Backends resolve through a small id→object registry
(`{"synthetic-depth": …}`, overridable for embedding/tests without
API changes); unknown ids raise `PipelineExecutionError`. The
calibration provider is an in-process collaborator parameter —
request/response stay serializable while provider injection stays
honest, because no serializable real-world provider selection exists
yet and this service fakes no calibration source. Cancellation is an
optional in-process token observed at pipeline boundaries only
(never serialized, never cross-process).

## Capabilities and security

`capabilities()` reports factual support (input suffix allow-list
from the ingestion contract, metric targets, registered backends,
mesh/GeoTIFF support) with no heavy loading. Paths are validated
(non-blank; ingestion/export enforce the rest); the service invokes
only the known pipeline — no shell, no subprocesses, no module
loading, no filesystem operations beyond the exporter's own, no
sandbox claims.

## Provenance and honesty

Summaries echo pipeline reproducibility metadata (checksums, backend
identity, calibration method/reference, target, engine version); no
timestamps or random IDs. Metric claims appear only for validated
metric artifacts.

## Aryan migration path

The current Node bridge (spawn Python → `DepthResult` JSON →
validate → adapt to `SceneArtifact`) keeps working against the
unchanged backend boundary. Future integration migrates to this
contract instead of direct backend inference:

```text
Desktop/Tauri
      ↓  future transport (subprocess JSON / stdio / IPC / localhost HTTP)
LocalService
      ↓
PipelineRunner
      ↓  DepthResult / Height / DSM / Mesh / Export
```

That migration is future work — this milestone changes no frontend
code and duplicates no TypeScript models beyond the necessary
wire-compatible schema.
