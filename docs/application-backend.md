# Unified Application Backend Path

How the app turns user intent into backend terrain through one
source abstraction.

## Rule

“The UI selects processing intent; the scientific backend determines
and reports the actual result semantics.”

## One source for React

`ApplicationBackendSource` (`src/input/applicationSource.ts`) is the
only backend source the UI constructs:

- **file** — a validated staged input run through the LocalService
  control plane plus the checksum-verified artifact transport;
- **synthetic** — the explicit development path (generated input,
  legacy terrain bridge), labeled `Synthetic Development Backend`.

`FixtureSource` remains for the local deterministic fixture (no
backend involved). React never sees transports, bridges, or
calibration providers.

## Production reality (audited, not inferred)

Every `DepthBackend` implementation in the repository was enumerated:
the sole implementation is `SyntheticDepthBackend`. No model
adapters, checkpoints, or inference runners exist, and no Shravan
branches are present. Consequently:

- there is no backend-selection dropdown (one genuine choice);
- the workspace shows the registered backend identity from live
  capabilities instead;
- nothing is ever labeled production, model, or AI;
- a production adapter behind `DepthBackend` would flow through
  unchanged — no frontend code names any model.

## Capabilities drive the UI

Target semantics, input suffixes, and backend identity all come from
`LocalService.capabilities()` at runtime. The output-target radio
(DSM vs AGL) renders only the targets the backend reports, defaults
to absolute elevation, and the selection propagates unchanged from
radio → `ServiceRequest` → calibration → DSM/mesh → adapter → layer
labels and metadata. No frontend list duplicates these.

## Request, execution, resolution

`LocalServiceClient.buildRequest` sends only contract-supported
fields (input path, metric target, `synthetic-depth`, `identity`,
mesh flag, null export). Failures keep backend domain codes and
stages; cancellation stays transport-level. Artifact resolution,
checksum linkage, retention, and retry behavior are unchanged from
the transport milestone. Retry reuses the same validated staged input
— deterministic reloads verified by test — never asking the user to
reselect after transient failures.

Validated input metadata persists in the workspace; raw byte buffers
are released after staging so large files are not held in React
state. The Panels show backend name and target from the *result*
artifact metadata (authoritative), never from request intent.

## Height exaggeration and camera

Unchanged: 1x/2x/5x/10x remain viewer-only transforms; Orbit,
First-Person, and Aerial modes are untouched by this milestone.

## Future Tauri mapping

Unchanged from prior docs: `ServiceTransport` is the seam; only the
transport implementation changes under a Tauri command bridge.
