# Processing / Job State UX

How DepthWizard represents a terrain-processing operation — and the
rules that keep the UI honest.

## Rules

“Never fabricate progress.”

“Processing state reflects backend reality.”

“Previous valid artifacts remain usable when a new processing attempt
fails, unless the backend explicitly invalidates them.”

## State machine (`src/processing/`)

```
idle → running → ready
            ↘ → error
            ↘ → cancelled
ready/error/cancelled → running (new operation)
any → idle (reset)
```

- `ProcessingState` is a discriminated union: `idle`, `running`,
  `ready`, `error`, `cancelled`. No scattered booleans.
- `transition(state, event)` is a pure reducer. A `start` event while
  `running` is refused (duplicate prevention); stage/complete/fail/
  cancel events outside `running` are no-ops. All covered by
  `transitions.test.ts`.
- Terminal states: `ready`, `error`, `cancelled`.

## Stages

Stage ids use the backend `PipelineState` vocabulary verbatim, plus a
frontend-only `loading` stage:

`loading → preprocessing → inference_running → calibrating →
dsm_generation → mesh_generation`

A stage line is emitted by `scripts/backend_bridge.py` on stderr
(`STAGE <name>`) only after that backend stage has genuinely finished.
The TypeScript bridge forwards them via `onStage`. There is no numeric
progress anywhere: the UI shows an indeterminate “Processing…” state.
`--terrain` results additionally carry a `stages` history array
(mirroring `ServiceResponse.states`).

## Cancellation

Backend cooperative cancellation is in-process only (per Shivam's
local-service design — never serialized, never cross-process), so the
frontend cancels by terminating the backend child process and
discarding the result. The previous artifact is retained; cancellation
is reported as `cancelled`, never as failure. `AbortSignal` flows
`App → runProcessingOperation → ArtifactLoader → source → bridge →
proc.kill()`.

## Errors

`BackendArtifactSource` throws `BackendOperationError` carrying the
structured `BridgeError[]` (phase: process/transport/validation/
adapter). The orchestrator unwraps the loader's `ArtifactError.cause`
chain instead of parsing message strings, and records
`{ code, message, stage, phase, previousAvailable }`. Python tracebacks
never reach the UI; the panel shows stage, error code, whether the
previous result survived, and a retry action.

## Artifact lifecycle

`runProcessingOperation` never touches the displayed artifact: on
success it returns the new `SceneArtifact` for the caller to install;
on failure or cancellation the previous terrain keeps rendering and
the camera is untouched. Starting an operation for a new source aborts
the in-flight one; re-selecting the active source is ignored.

## Future Tauri IPC

The layering is transport-agnostic by construction:

```
React → runProcessingOperation → ArtifactLoader → ArtifactSource
    → (today) child_process → scripts/backend_bridge.py
    → (future) Tauri command → Rust → Python/backend process
```

A future backend service transport can feed the same reducer with
`ServiceResponse.states` / `failure.stage` (see Shivam's
`feat/shivam-local-service`: `ServiceResponse{final_state, states[],
failure{code, message, stage}}`). No Rust/Cargo/Tauri tooling is
installed in this environment, so no IPC is implemented here.
