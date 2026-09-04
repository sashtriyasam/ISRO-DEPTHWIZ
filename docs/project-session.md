# Project Session Lifecycle

This document describes the workspace session lifecycle in DepthWizard, which tracks the application state from empty workspace through artifact loading, analysis, and reset.

## Session Phases

The workspace session transitions through these phases:

### 1. Empty
- No artifact loaded
- No processing in progress
- Default state on startup

### 2. Processing
- Backend operation is running
- No artifact available yet
- User can cancel the operation

### 3. Ready
- Artifact is loaded and available for interaction
- User can perform inspections, measurements, profiles
- Can generate new terrain (invalidates current artifact)

### 4. Error
- Processing failed and no artifact is available
- User can retry or select new input
- Previous artifact is preserved if it existed

## State Derivation

Session state is derived from multiple independent state slices:

```typescript
interface SessionSnapshot {
  hasArtifact: boolean;
  processing: ProcessingState;
  waypoints: FlythroughWaypoint[];
  playbackStatus: PlaybackStatus;
  measurement: MeasurementState;
  profile: ProfileState;
  inspection: InspectionState;
}
```

### Phase Derivation
```typescript
deriveSessionPhase({
  hasArtifact: artifact !== null,
  processing: processingState
})
```

Rules:
- If `processing.status === "running"` → `"processing"`
- If `hasArtifact` → `"ready"`
- If `processing.status === "error"` and no artifact → `"error"`
- Otherwise → `"empty"`

### Dirty State Derivation
```typescript
deriveSessionDirty({
  waypoints,
  measurement: measurementState,
  profile: profileState
})
```

Rules:
- If waypoints array is non-empty → `"dirty"`
- If measurement completed → `"dirty"`
- If profile completed → `"dirty"`
- Otherwise → `"clean"`

## Lifecycle Transitions

### From Empty
- Select input → generate → **Processing**
- Can reset (no-op)

### From Processing
- Success → **Ready** (artifact loaded)
- Failure with previous artifact → **Ready** (previous preserved)
- Failure without previous → **Error**
- Cancel → **Empty** or **Ready** (based on previous artifact)

### From Ready
- Generate new → **Processing** (current artifact invalidated)
- User interaction → dirty state
- Reset → **Empty**

### From Error
- Retry → **Processing**
- Select new input → generate → **Processing**
- Reset → **Empty**

## Reset Orchestration

Reset clears all workspace state in a specific order:

```typescript
resetSession({
  abortOperation: () => { /* abort any in-flight operation */ },
  setProcessingIdle: () => { /* reset processing state */ },
  clearArtifact: () => { /* remove artifact and reset to idle */ },
  clearLayers: () => { /* remove layer state */ },
  clearAnalysis: () => { /* clear measurements, profiles, selections */ },
  clearFlythrough: () => { /* clear waypoints and playback */ },
  resetCameraToOrbit: () => { /* reset camera mode to orbit */ },
});
```

The reset is triggered by the "Reset Workspace" button in the SessionStatus component.

## Pending Selection Handling

When starting a new operation while analysis tools are active:
1. Detect pending selections (measurement/profile selecting, inspection selected)
2. Clear all selection states before starting new operation
3. This prevents stale UI state from interfering with new operations

## Integration Points

### App Component
- Computes `sessionPhase` and `sessionDirty` via `useMemo`
- Provides `handleResetWorkspace` callback
- Cancels pending selections on operation start

### SessionStatus Component
- Displays current phase with color-coded indicator
- Shows "unsaved" badge when dirty state is detected
- Provides reset button when workspace can be reset

### ProcessingPanel
- Receives phase information for display
- Shows backend/target metadata on success

## Constraints

1. **No mutation of source artifacts** - All state is derived, never mutated
2. **Ordered cleanup** - Reset follows a specific sequence to prevent intermediate inconsistent states
3. **Idempotent reset** - Multiple resets are safe
4. **Atomic transition** - New operations cancel previous in-flight work
