# Flythrough UX

How the waypoint flythrough stays predictable: explicit states,
locked conflicts, and display-only route graphics.

## Rule

“A trajectory is viewer state. It is not scientific spatial data.”
Waypoints carry display-space camera positions and look targets —
never altitude, CRS, or elevation claims.

## Playback states

`idle` (fewer than 2 waypoints) → `ready` → `playing` ⇄ `paused` →
`completed`, plus `ready` after stop/reset. Statuses are a single
state value, never parallel booleans. Play starts deterministically
from waypoint 1; pause freezes pose and time; resume continues from
the stored time; stop restores the previous camera mode; reset
returns to the start pose and back to `ready`; completion lands
exactly on the final waypoint, fires once, and restores the previous
mode. Repeated play clicks cannot fork controllers — the manager
disposes the previous owner on every activation.

## Camera ownership policy

| UI state | Manual camera | Terrain picking | Waypoint editing |
| -------- | ------------- | --------------- | ---------------- |
| idle/ready/completed | Full | Full | Full |
| playing | Locked (mode buttons, Frame, Reset disabled) | Paused (pointer owned by flight) | Locked |
| paused | Locked (camera stays owned) | Paused | Locked (prevents stale controller paths) |

Measurement/profile start buttons lock during flight, and starting
playback clears pending picks so no stranded selection states survive.
First-person keyboard can never fight playback: its controller is
disposed on entry, and Esc stops the flight (restoring the prior
mode) instead.

## Progress without per-frame React

The panel shows `Segment i of N · Waypoint j of M` plus total
duration, updated only on segment transitions and status changes —
never per animation frame. The 3D route mirrors this: the preview
line splits into dim completed vs bright future segments, and the
current waypoint marker scales up, rebuilt only on waypoint or index
changes.

## Route graphics

One `THREE.Group` per trajectory: path line(s) plus one sphere per
waypoint (green start, red end, accent middle, enlarged current).
Everything is `pickable: false`, depth-test off, and disposed as a
unit on waypoint edits, artifact replacement, clear, and viewer
teardown. Raycasting targets the terrain mesh object directly, so
route graphics can never intercept inspection, measurement, or
profile clicks. Marker size derives from display bounds; no data
values are encoded in markers.

## Invalidation

- New artifact → waypoints, preview, and playback reset (a path must
  not survive unrelated geometry).
- Layer/exaggeration rebuilds keep waypoints, step back to `ready`,
  and re-sync the preview (positions are display-space snapshots and
  may sit differently afterward — stated in the panel flow, not
  hidden).
- Speed (0.5×/1×/2×) scales trajectory time only; geometry, metadata,
  measurements, and profiles are untouched (proven by invariant
  tests).

## Edge cases

Zero/one waypoint explains itself instead of offering playback;
duplicate and degenerate (zero-length, coincident look target)
segments evaluate to finite poses without NaN; unmount and rebuild
paths dispose controllers, listeners (there are none to leak — the
controller is update-driven), and preview resources; repeated
play/stop/reset cycles stay deterministic.

## Visual validation

Validated headlessly against the production build (M25) with real
Chromium WebGL (SwiftShader) driven over CDP — no mocks, no
fabricated screenshots (harness kept outside the repo; no new
dependencies):

- Environment: Edge headless + `vite preview` on Windows; fixture
  terrain (the browser-usable path — Python-backed sources need a
  desktop bridge, which the UI reports honestly instead of faking).
- Workflows: fixture → generate → 3 waypoints across orbit/aerial
  poses → play → pause → resume → stop → replay → natural completion
  → reset; speed 2× mid-flight; first-person capture; Esc handling.
- Confirmed: route line plus green-start/red-end markers render and
  track the camera poses; mid-flight camera motion, pause freeze,
  resume continuation, exact final-pose landing, and single-fire
  completion; mode restoration on stop/completion; waypoint progress
  text; wireframe/combined rendering with the route legible;
  exaggeration sweep 1x→10x→1x with route retained; terrain picking
  during flight creates no selection while idle picking works
  (selection marker verified); artifact replacement clears the
  route; single canvas throughout; narrow (900×700) layout intact;
  all interactive controls expose accessible names with correct
  disabled states.
- Not tested visually: pointer-lock-free drag feel nuances,
  multi-monitor sizing, and touch input (no touch device present).

## Explicitly out of scope

Reorder, persistence, import/export, easing editors, splines,
terrain-following, geospatial conversion, and backend-generated
routes. The pure evaluator plus the controller seam are the
integration points if any of those ever land.
