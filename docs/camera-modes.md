# Camera Modes

How DepthWizard navigates display-space terrain across Orbit,
First-Person, and Aerial modes.

## Rule

“Camera navigation operates on display-space geometry and does not modify scientific data.”

## Modes

| Mode | Implementation | Pointer | Terrain picking |
| ---- | -------------- | ------- | --------------- |
| Orbit | `OrbitCameraController` over `OrbitControls` (damped rotate/pan/zoom) | Orbit gestures | Enabled |
| First Person | `FirstPersonCameraController` (drag-look, WASDQE + Shift) | Camera look (drag) | Paused (stated in UI) |
| Aerial | `AerialCameraController` composing `OrbitCameraController` with a top-down configuration | Orbit gestures | Enabled |

`CameraMode = "orbit" | "first-person" | "aerial"` with a `CAMERA_MODES`
registry and `isCameraMode` guard — no untyped mode strings.

## First person

- **Look**: press-and-drag with the mouse (a deliberate gesture; no
  pointer-lock capture, so the user is never trapped — the mechanism
  is replaceable behind the controller interface).
- **Move**: `W`/`A`/`S`/`D` fly-style along the look direction,
  `Q`/`E` down/up, `Shift` ×3 boost. No jumping, collision damage, or
  other game mechanics.
- **Speed**: derived from display bounds (`0.6 × max dimension` per
  second, adjustable ×0.1–×10); per-frame steps clamp to 100 ms so
  tab-switch hitches cannot teleport the camera.
- **Safety**: positions clamp to the display bounds box expanded by a
  margin — display-space only, never scientific coordinates.
- **Exit**: Esc key, the mode buttons, or any controller toggle.
  Entering the mode clears pending inspect/measure/profile picks so no
  hidden points are created.

## Aerial

An `OrbitControls` configuration, not a duplicate controller: polar
angle clamped near top-down, distances scaled to the scene, and the
initial viewpoint computed high above the bounds center from actual
dimensions (never hardcoded fixture coordinates). Frame Scene and
Reset re-derive the pose from current bounds.

## Lifecycle and switching

Every controller implements
`activate/update/deactivate/dispose` (+ `resize/getState/setState/
frameBounds/reset`). `CameraManager.activate` deactivates and disposes
the previous controller, so listeners never accumulate and exactly one
controller owns input. The single `WebGLRenderer`, canvas, and render
loop are untouched — controllers update from the existing animation
frame, keeping per-frame work allocation-light and all React state out
of the loop.

Mode switches never reload artifacts, layers, exaggeration, or
analysis state. On artifact replacement the viewer rebuilds (existing
behavior) and the requested mode is re-applied; `frameBounds` always
receives fresh display bounds so no controller navigates stale space.
Layer switches do not touch the camera.

## Exaggeration

Controllers receive already-scaled display bounds, so 1x/2x/5x/10x
just work: framing, speed, and clamps follow displayed geometry while
elevation values, metadata, and measurement results stay unchanged.

## Future trajectory work

The `CameraState` (mode, position, target, distance) plus the
controller interface are the seam a future waypoint/playback system
can drive. Nothing here records, persists, or plays back camera paths.
