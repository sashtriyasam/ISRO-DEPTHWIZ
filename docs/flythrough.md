# Waypoint Flythrough

How DepthWizard plays camera trajectories over terrain — viewer
state driving the existing camera seam.

## Rule

“A trajectory is viewer state. It is not scientific spatial data.”

## Model

- `FlythroughWaypoint`: frontend-local id plus display-space camera
  `position` and look `target` (never latitude/longitude/altitude —
  no authoritative camera CRS exists).
- `FlythroughTrajectory`: ordered waypoints with one fixed
  `segmentDurationMs` (3 s default). Duration is segment count ×
  segment duration — deterministic and explainable; per-waypoint
  timing is an explicit future extension, not a hidden feature.
- `PlaybackSpeed = 0.5 | 1 | 2` (default 1×) scales trajectory time
  only — never terrain, metadata, or results.
- Playback needs ≥ 2 waypoints (`idle` below that, `ready` above);
  statuses are `idle | ready | playing | paused | completed`, never
  parallel booleans.

## Evaluation (pure)

`evaluateTrajectory(trajectory, timeMs)` linearly interpolates
positions and spherically interpolates orientations (quaternion
slerp — never naive Euler blending) between segment endpoints
derived from look-at matrices. Times clamp to `[0, duration]`, so
playback lands exactly on the final waypoint with no overshoot, and
repeated evaluation is bit-identical. No scene, renderer, or clock
lives in this function.

## Playback engine

`TrajectoryCameraController` implements the standard controller
interface, so the manager, render loop, and disposal paths treat it
like any mode:

- time advances in `update()` from a clamped frame delta (≤ 100 ms —
  tab-switch hitches cannot jump the camera);
- poses apply as camera position + quaternion, clamped to
  display-space bounds;
- completion fires exactly once, waypoint-index callbacks fire only
  on segment change (React is never updated per frame);
- the controller owns zero DOM listeners, so deactivation cannot leak.

`CameraManager.activateController()` injects it through the same seam
as manual modes (bare `activate("trajectory")` without data is a
deliberate safe no-op). `CAMERA_MODES` lists all four modes while the
manual UI buttons stay at three.

## Ownership and conflicts

Playback takes camera ownership: manual controllers are disposed on
entry, their buttons lock, terrain picking pauses (the pointer
controls nothing while flying), and measurement/profile picks are
cleared on the way in so no hidden points are created. Analysis
*c*alculations are untouched — only camera pose moves.

Stopping restores the previous manual mode (orbit/aerial keep their
position and retarget; first-person reframes to its start pose, as
documented). Pause freezes trajectory time; resume continues it;
reset returns to the first waypoint; replay restarts from zero.

## Preview

One `THREE.Line` (accent, depth-test off, `pickable: false`) rebuilt
only when waypoints change — never per frame — and disposed with the
viewer. Raycasting targets the terrain mesh object directly, so the
line can never intercept scientific picks.

## Invalidation (predictable)

- New artifact → trajectory, preview, and playback reset (a path may
  not survive unrelated geometry).
- Layer/exaggeration rebuilds keep waypoints, drop back to `ready`,
  and re-sync the preview (positions are display-space snapshots and
  may sit differently under a new exaggeration — stated, not hidden).

## Future trajectory work

Waypoint reorder, persistence, import/export, easing editors, and
terrain-following autopilot are explicitly out of scope. The
`CameraState` seam plus the pure evaluator are the integration points
a future system would reuse.
