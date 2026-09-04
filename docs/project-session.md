# Project Session Lifecycle

This document describes the workspace session lifecycle in DepthWizard. The session tracks application state from empty workspace through artifact loading, analysis, and reset. **No persistence exists** — all state is in-memory only.

## Session Phases

The workspace session transitions through four phases:

### 1. Empty
- No artifact loaded
- No processing in progress
- Default state on startup

### 2. Processing
- Backend operation is running
- May or may not have a previous artifact (artifact replacement)
- User can cancel the operation

### 3. Ready
- Artifact is loaded and available for interaction
- User can perform inspections, measurements, profiles
- Can generate new terrain (invalidates current artifact)

### 4. Error
- Processing failed and no artifact is available
- User can retry or select new input
- Previous artifact is preserved if it existed (phase stays "ready")

## Phase Derivation Rules

```typescript
deriveSessionPhase({ hasArtifact, processing })
```

| hasArtifact | processing.status | Result |
|-------------|------------------|--------|
| false | idle | empty |
| false | running | processing |
| false | error | error |
| false | cancelled | empty |
| true | idle | ready |
| true | running | processing |
| true | error | ready |
| true | cancelled | ready |

Key invariant: **ERROR phase only occurs when there is no artifact.** If a replacement operation fails and a previous artifact exists, the phase remains "ready".

## Session Modification State

The session modification state tracks whether the user has created analysis artifacts that would be lost on reset.

```typescript
deriveSessionModified({ waypoints, measurement, profile })
```

| Condition | Result |
|-----------|--------|
| Waypoints array non-empty | modified |
| Measurement completed | modified |
| Profile completed | modified |
| Otherwise | clean |

### What counts as "modified"

**SESSION-MODIFYING** (tracked):
- Flythrough waypoints (route data)
- Completed measurement results
- Completed elevation profiles

**NOT modified** (transient/display-only):
- Inspection selection (transient viewer state)
- Camera position/mode (transient viewer state)
- Rendering mode (display preference)
- Height exaggeration (display preference)
- Selected layer (display preference)
- Metadata panel visibility (UI state)

**No persistence exists.** The "modified" label indicates analysis state is active in the current session, not that changes are unsaved to a file.

## Reset Orchestration

Reset clears all workspace state in this order:

```typescript
resetSession({
  abortOperation:    // 1. Abort any in-flight operation
  setProcessingIdle: // 2. Reset processing state to idle
  clearArtifact:     // 3. Remove artifact, set state to idle
  clearLayers:       // 4. Remove layer state
  clearAnalysis:     // 5. Clear measurements, profiles, selections
  clearFlythrough:   // 6. Clear waypoints and playback
  resetCameraToOrbit:// 7. Reset camera mode to orbit
})
```

The reset is:
- **Idempotent** — multiple calls are safe
- **Deterministic** — same order every time
- **Safe during processing** — aborts in-flight operation
- **Safe during flythrough** — clears playback state

## Artifact Invalidation

When a new operation starts:

1. **Pending selections cleared** — any active measurement/profile/inspection selection is cleared before the new operation begins
2. **On success** — previous artifact replaced, analysis state cleared, flythrough cleared
3. **On failure with previous artifact** — previous artifact preserved, phase stays "ready"
4. **On failure without previous artifact** — phase transitions to "error"
5. **On cancellation** — previous artifact preserved (if any), phase returns to "empty" or "ready"

## Error Recovery

From error phase:
- Retry with same input → processing
- Select new input → generate → processing
- Reset → empty

The error state does not imply the previous terrain disappeared — only that the latest operation failed and no artifact is currently available.

## State Categories

| State Slice | Category | Modified? |
|-------------|----------|-----------|
| Flythrough waypoints | session-modifying | yes |
| Measurement result | session-modifying | yes |
| Profile result | session-modifying | yes |
| Inspection selection | transient viewer | no |
| Camera mode/position | transient viewer | no |
| Rendering mode | display preference | no |
| Height exaggeration | display preference | no |
| Selected layer | display preference | no |
| Metadata visibility | UI state | no |
| Input selection | UI state | no |

## Integration Points

### App Component
- Computes `sessionPhase` and `sessionModified` via `useMemo`
- Provides `handleResetWorkspace` callback
- Cancels pending selections on operation start

### SessionStatus Component
- Displays current phase with color-coded indicator (text label always present, not color-only)
- Shows "modified" badge when analysis state is active
- Provides reset button when workspace can be reset

## Constraints

1. **No mutation of source artifacts** — All state is derived, never mutated
2. **Ordered cleanup** — Reset follows a specific sequence
3. **Idempotent reset** — Multiple resets are safe
4. **Atomic transition** — New operations cancel previous in-flight work
5. **No persistence** — All state is in-memory; no project files exist
6. **No scientific calculations** — Session module contains no terrain/elevation logic
