# Desktop Host Boundary + Packaging Contract

How DepthWizard separates the JavaScript runtime environment from the
scientific backend — and what a future native wrapper must provide.

## Rule

Host capability answers where the code runs. Backend identity answers
what science is available. The two must never imply each other.

## Architecture

```
Browser
  ↓
HostCapability (browser: no spawning, no staging)
  ↓
Input/Service abstraction
  ↓
LocalService contract
  ↓
canonical backend
  ↓
artifact transport
  ↓
SceneArtifact
  ↓
Three.js

Desktop (future native host):
Native host
  ↓
DesktopHost implementation (same HostCapabilities shape)
  ↓
same TypeScript boundary
```

The two paths converge before scientific artifact adaptation. No
packaged desktop binary exists today; nothing below claims one does.

## Host capabilities (`src/host/`)

A tiny framework-neutral module answering only environment questions:

- `runtime`: `"browser"` or `"node"` (detected from globals, never
  configurable silently — overrides are explicit and injected, which
  is also how tests simulate a browser).
- `processSpawning` / `localFilesystem`: default from the runtime,
  overridable for hosts like Tauri where JS runs in a webview but
  native APIs arrive through a different mechanism.

The module contains no scientific vocabulary by construction
(enforced by test). `BackendBridge` and `SubprocessServiceTransport`
take an optional host override and expose their resolved
capabilities; all six bridge guards and the transport guard now read
from this single source instead of duplicated `typeof process`
checks. Error codes (`BROWSER_ENVIRONMENT`, `OPERATION_CANCELLED`)
are unchanged.

## UI boundary

React components never import `child_process`, `fs`, `os`, `path`,
or spawn processes (enforced by test across components, app, viewer,
input, processing, and flythrough code). The input workspace renders
an honest host line — `Browser (desktop backend unavailable)` with a
fixture pointer in browsers, `Desktop host` under Node — and disables
only what the host cannot do. Fixture-based viewer work always works.

## Process lifecycle (audited, Node implementation)

- Structured argv arrays, never shell strings; no user input reaches
  an executable path (paths travel as argv entries or stdin JSON).
- One process per operation, no shared handles: repeated executions
  cannot poison each other (proven by test).
- Cancellation kills the owned process and settles exactly once;
  aborting mid-flight after the first real stage line deterministically
  yields `OPERATION_CANCELLED` (proven by test).
- Exit codes, stderr separation, stdout JSON parsing, and timeouts
  produce structured errors; listeners and timers are released on
  every settlement path.
- Staged input files live in `mkdtemp` directories under the OS temp
  dir with sanitized basenames and guaranteed cleanup.

## Path handling

No hardcoded user, home, or machine paths exist. Bridge script paths
default relative (`scripts/backend_bridge.py`,
`scripts/depthwiz_service.py`) and are overridable per instance —
a packaged host is expected to resolve absolute locations and inject
them. Staged filenames are basename-sanitized and length-capped.

## Packaging contract (for a future native wrapper)

- Frontend build output: `dist/` from `vite build` (static assets).
- Runtime components: a Python 3.11+ environment with the
  `depthwizard` package installed (editable checkout today;
  `pyproject.toml` declares `pydantic`, `Pillow`, `rasterio`,
  `numpy`).
- Service entry points: `scripts/depthwiz_service.py` (wire contract
  v1 over stdio) and `scripts/backend_bridge.py` (terrain payloads);
  both speak JSON on stdout, diagnostics on stderr, exit codes on
  failure.
- Input paths: absolute staged files supplied by the host; temp dirs
  owned and cleaned by the frontend staging layer.
- Shutdown: abort in-flight operations first (controllers already do);
  each operation owns exactly one child process, so host shutdown
  kills at most the current run.
- Permissions: temp-dir read/write only; no other filesystem access
  is assumed.
- Cancellation: transport-level process termination mapping to the
  existing `cancelled` UI state.
- Future Tauri/Electron insertion point: implement the
  `HostCapabilities` shape plus `ServiceTransport`, and pass them
  into `BackendBridge`/`SubprocessServiceTransport` options — no
  component, adapter, or validator changes required.

## What the native wrapper must never do

Recalculate DSM, remesh, calibrate, resample, reinterpret units,
modify CRS, exaggerate height, or invent backend identity. Host code
transports data; science stays in `main/src/depthwizard`.
