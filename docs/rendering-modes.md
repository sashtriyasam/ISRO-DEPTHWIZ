# Terrain Rendering Modes

How DepthWizard presents backend terrain in Shaded, Wireframe, and
Shaded + Wireframe modes — presentation only.

## Rule

“Rendering modes modify presentation only and never modify scientific terrain data.”

## Modes

| Mode | Surface | Overlay | Geometry cost |
| ---- | ------- | ------- | ------------- |
| Shaded (default) | `MeshStandardMaterial`, height tint when elevation data exists | None | One `BufferGeometry` |
| Wireframe | Same material with native `wireframe: true` | None | One `BufferGeometry` |
| Shaded + Wireframe | Shaded surface | `LineSegments` over `WireframeGeometry`, subtle tinted lines | Surface geometry plus one derived line geometry |

`RenderingMode = "shaded" | "wireframe" | "shaded-wireframe"` with a
registry and guard — no ad-hoc UI strings. The factory default
preserves the pre-existing combined look; the application default is
Shaded.

## Backend normals

When the artifact carries backend normals they are attached verbatim
to the geometry (asserted value-for-value in tests). When absent, the
renderer falls back to `computeVertexNormals()` purely so lighting
works — a display-only fallback, never presented as a scientific
attribute. No slope, color-ramp, or contour math exists anywhere.

## Picking rule

Only the surface `Mesh` is pickable (`userData.pickable = true`); the
line overlay is explicitly non-pickable (`false`). Raycasting targets
the mesh object directly, so inspection, measurement, and profile
clicks can never land on overlay lines in any mode.

## Ownership and lifecycle

- `createLayerMesh(artifact, layerId, mode)` builds one surface
  geometry plus, in combined mode, one derived line geometry and up to
  two materials. `disposeLayerMesh` releases all of them.
- The viewer rebuilds the group on artifact/layer/mode changes through
  one shared helper; mode switches never touch the camera, renderer,
  canvas, exaggeration, layers, or analysis state.
- Exaggeration applies as `mesh.scale.y` (plus overlay) after
  construction — geometry positions always equal artifact vertices
  exactly, at every exaggeration level and camera mode.

## Compatibility

Modes are orthogonal to layers (DSM/rDSM/AGL where available; the
`wireframe` layer id always renders wireframe regardless of mode),
cameras (Orbit/First-Person/Aerial), and analysis tools (identical
scientific inputs and results in every mode — mode switches are safe
mid-measurement).
