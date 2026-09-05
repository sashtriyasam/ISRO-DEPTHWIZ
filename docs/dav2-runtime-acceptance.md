# Real DA-V2 Runtime Desktop Acceptance

## Runtime model (as found)

No Electron/Tauri/native host exists in the repository. The desktop
runtime is the Vite production build (`npm run build` → `vite preview`),
which starts correctly in real Chrome (verified below). In a plain
browser the app honestly reports "Host: Browser (desktop backend
unavailable)" and disables Python-backed paths — process spawning
requires a native host that does not yet exist (release blocker, not
claimed otherwise).

## Fixes in this task

| #   | Location                                      | Change                                                                                                                                           |
| --- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | `BackendBridge`, `SubprocessServiceTransport` | `DEPTHWIZARD_PYTHON` env fallback for the interpreter (`option > env > "python"`); no machine-specific paths committed                           |
| 2   | `App.tsx` SceneInfo `sourceLabel`             | used the canonical `sourceStatusLabel`: real backends now read `Backend model (<name>)` instead of the hardcoded "Synthetic Development Backend" |
| 3   | `ApplicationBackendSource`                    | optional `backend` plumbed to `FileInputSource` and the default bridge; `backendLabel` model-aware, synthetic default preserved                  |

Regression tests: interpreter-resolution cases in `bridge.test.ts`
(+2 pass), backend-label cases in `applicationSource.test.ts` (+2 pass).

## Runtime evidence (real DA-V2 Small, CPU, HF_HUB_OFFLINE=1)

Headless Chrome 144 (SwiftShader WebGL2 verified working) rendered the
real 64×64 terrain through the repo's own modules
(`adaptTerrainProduct` → `createLayerMesh` → framed camera →
`WebGLRenderer`), bundled with the repo's esbuild, served statically:

| Observation           | Value                                                                              |
| --------------------- | ---------------------------------------------------------------------------------- |
| WebGL renderer        | created, 1 call, 7938 triangles                                                    |
| Non-background pixels | 98,867 / 480,000                                                                   |
| Mesh                  | 4096 vertices / 23814 indices, finite                                              |
| Camera                | finite framed position, bounds sphere ≈ 44.56                                      |
| Exaggeration ×10      | display pixels change, source vertices bit-identical, reset restores base checksum |

Production app in real Chrome: full UI renders (camera modes, Frame
Scene, flythrough, exaggeration with "Display only" notice, rendering
modes, measurement, profile, inspector, metadata); browser host gating
behaves as designed.

64×64 mesh structure: 4096 vertices / 7938 triangles, as expected.
Offline: real smoke + bridge tests pass with `HF_HUB_OFFLINE=1`
(provisioning vs runtime separated; no runtime network code exists in
`src/depthwizard`).
Failure paths: unknown backend, missing checkpoint, missing interpreter
all fail loudly with domain errors; no synthetic substitution.

## Validation

pytest 410 passed / 2 skipped; DA-V2 real smoke pass; ruff, format,
mypy clean; tsc clean; build succeeds; vitest 502 passed / 87 failed /
4 skipped (failures byte-identical pre-existing baseline: DOM queries +
Windows `python`-on-PATH spawns).

## Remaining blockers

Native host with process spawning (for in-app Python execution),
GPU/long-run/installer evidence, field accuracy. The project is ready
for scientific benchmarking of the verified pipeline; it is not yet a
packaged desktop product.
