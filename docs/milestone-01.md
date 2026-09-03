# DepthWizard — Desktop & 3D Foundation (Milestone 01)

## Architecture

### Desktop Shell

**Selected: Tauri 2 (pending Rust toolchain installation)**

Rust/Cargo is not currently installed on this development machine. The frontend is architecturally compatible with Tauri 2 but currently runs via Vite dev server. Desktop packaging will be completed when the Rust toolchain is installed.

The Vite dev server is used only for development. The application is designed as a standalone desktop application, not a web application.

### Frontend Stack

- **TypeScript** — strict mode, ES2022 target
- **React 19** — UI/application state
- **Three.js** — 3D rendering (direct, not R3F)
- **Vite** — build tooling
- **Vitest** — testing

### Directory Structure

```
src/
├── app/App.tsx              # Root application component
├── components/
│   ├── AppShell/            # Layout shell (header, viewport, panel, statusbar)
│   └── StatusBar/           # Status bar component
├── viewer/
│   └── Viewer.tsx           # Three.js renderer with lifecycle management
├── fixtures/
│   ├── deterministicFixture.ts  # Synthetic test terrain
│   ├── useTestFixture.ts        # React hook for fixture
│   └── deterministicFixture.test.ts
├── types/
│   ├── scene.ts             # SceneArtifact type contract
│   └── scene.test.ts
├── styles/
│   └── global.css           # Design system tokens
└── test/
    └── setup.ts             # Test setup
```

### Design System

CSS custom properties establish reusable tokens:

- **Spacing**: `--spacing-xs` through `--spacing-2xl`
- **Typography**: `--font-size-xs` through `--font-size-lg`
- **Colors**: `--color-bg-*`, `--color-border-*`, `--color-text-*`, `--color-status-*`
- **Radii**: `--radius-sm`, `--radius-md`, `--radius-lg`

### Application Shell

Four-region layout:
- **Header** (40px): Application title and version
- **Viewport** (flex): Three.js 3D canvas
- **Panel** (280px): Inspector/scene info
- **Statusbar** (24px): Development fixture notice

## Scene/Artifact Contract

`SceneArtifact` is the typed frontend contract for rendered content:

```typescript
interface SceneArtifact {
  id: string;
  label: string;
  mesh: MeshData;          // vertices, indices, normals, uvs
  texture?: TextureData;   // optional RGB texture
  elevation?: ElevationData; // optional height grid
  metadata: SceneMetadata; // CRS, transform, bounds, units, source
}
```

**Ownership**: Frontend owns presentation. Scientific/backend owns elevation, AGL, DSM, rDSM, slope, spatial coordinates, CRS, geotransforms.

**Independence**: Contract is not coupled to Shravan's neural-network, Sat3DGen internals, or any ML model.

## Deterministic Test Fixture

`createDeterministicFixture()` generates a synthetic 8×8 sinusoidal terrain grid.

- Marked as `source: "deterministic-fixture"`
- Clearly documented as NOT scientific output
- Deterministic: identical output on every call
- Used for renderer validation before backend integration

## Three.js Viewer Lifecycle

1. **Mount**: Create renderer, camera, scene, geometry, materials, lights
2. **Render loop**: `requestAnimationFrame` with slow orbital camera
3. **Resize**: Window resize listener updates camera aspect and renderer size
4. **Unmount**: Dispose geometry, materials, renderer; remove canvas; cancel animation frame; remove event listeners

**Design rules**:
- Three.js scene lifecycle is outside React render cycles
- React manages UI/application state only
- No duplicate WebGL contexts
- Clean GPU resource disposal on unmount
- Future terrain meshes can be supplied without rewriting the renderer

## Height Exaggeration Architecture

Not implemented in this milestone. Architecture separates:

```
scientific elevation
    ├── measurement/export/backend values (never modified)
    └── display transform → renderer
```

`DEFAULT_DISPLAY_TRANSFORM` defines `heightExaggeration: 1.0`.

## Camera Architecture

Minimal perspective camera with slow orbital animation. No first-person flythrough, aerial mode, or trajectory editor yet. Structured so camera controllers can be introduced later.

## How to Run

```bash
npm install
npm run dev          # Start dev server on port 1420
npm run build        # Production build
npm run test         # Run tests
npm run typecheck    # TypeScript type checking
```

## Testing

```bash
npm run test         # Run all tests (13 tests across 3 files)
```

Tests cover:
- Fixture validity and determinism
- SceneArtifact type contract
- AppShell component rendering

## Upstream Audit: Sat3DGen

**Repository**: https://github.com/qianmingduowan/Sat3DGen  
**License**: MIT  
**Commit**: latest main  
**Language**: Python (PyTorch, Diffusers)

**Findings**:
- Python-based ML pipeline for satellite-to-3D generation
- Has DSM processing, mesh export (OBJ), trajectory generation
- Gradio web demo (Python)
- No reusable TypeScript/React code for this milestone
- Architecture concepts (DSM processing, mesh formats) inform future integration

**No Sat3DGen source code copied in this milestone; architecture reviewed for future integration.**

## Dependencies Added

| Package | Version | Purpose |
|---------|---------|---------|
| react | ^19.1.0 | UI framework |
| react-dom | ^19.1.0 | DOM rendering |
| three | ^0.177.0 | 3D rendering |
| typescript | ~5.8.3 | Type checking |
| vite | ^6.3.5 | Build tooling |
| vitest | ^3.2.1 | Testing |
| @types/react | ^19.1.8 | React types |
| @types/three | ^0.177.0 | Three.js types |
| jsdom | ^26.1.0 | Test DOM |
| @testing-library/react | ^16.3.0 | Component testing |
| @testing-library/jest-dom | ^6.6.3 | DOM matchers |

## Interface Changes

None. This is the initial foundation.

## Known Issues

- Rust toolchain not installed; Tauri 2 desktop packaging deferred
- Three.js bundle is ~679KB (expected for Three.js; code-splitting can be added later)
