# Native Release Acceptance Matrix

Generated: 2026-09-05

| # | Case | Status | Evidence | Environment | Owner | Blocker? |
|---|------|--------|----------|-------------|-------|----------|
| 1 | Browser fixture | ✅ PASS | 625 Vitest tests passing | Headless | Aryan | No |
| 2 | Electron fixture | ✅ PASS | 34 Electron security + API tests passing | Headless | Aryan | No |
| 3 | Managed runtime | ⚠️ PARTIAL | `getManagedPythonPath()` resolves `<resources>/python/python.exe` when packaged; falls back to `python` on PATH if missing | Headless | Aryan | Yes — no actual managed Python bundled |
| 4 | Runtime self-check | ✅ PASS | Service capabilities response includes `available_backends` | Headless | Shivam | No |
| 5 | Real backend capability | ✅ PASS | `depth-anything-v2-small` registered when `depth_anything_v2` + `torch` + checkpoint discoverable | Headless | Shivam | No |
| 6 | Explicit DA-V2 selection | ✅ PASS | `backend: "depth-anything-v2-small"` in ServiceRequestWire | Headless | Aryan | No |
| 7 | Missing DA-V2 | ✅ PASS | Capabilities exclude `depth-anything-v2-small`; request returns error | Headless | Shivam | No |
| 8 | Missing checkpoint | ✅ PASS | `build_backends()` returns only `synthetic-depth` when checkpoint missing | Headless | Shivam | No |
| 9 | Checkpoint mismatch | ✅ PASS | Python backend verifies SHA-256; mismatch → `ModelInferenceError` | Headless | Shivam | No |
| 10 | Synthetic explicit mode | ✅ PASS | `backend: "synthetic-depth"` explicitly selected; labeled as development | Headless | Aryan | No |
| 11 | No silent fallback | ✅ PASS | DA-V2 unavailable → explicit error, never synthetic substitution | Headless | Aryan | No |
| 12 | Real DA-V2 inference | ⚠️ NOT TESTED | Requires real Python + torch + checkpoint; cannot run in headless env | Headless | Aryan | Yes — requires visual validation |
| 13 | Calibration | ⚠️ NOT TESTED | Depends on real DA-V2 execution | Headless | Shivam | Yes — requires visual validation |
| 14 | Metric DSM | ⚠️ NOT TESTED | Depends on real DA-V2 + calibration | Headless | Shivam | Yes — requires visual validation |
| 15 | Terrain mesh | ⚠️ NOT TESTED | Depends on real DA-V2 + calibration + DSM | Headless | Shivam | Yes — requires visual validation |
| 16 | SceneArtifact | ⚠️ NOT TESTED | Depends on real DA-V2 pipeline | Headless | Aryan | Yes — requires visual validation |
| 17 | Three.js rendering | ⚠️ NOT TESTED | Requires non-headless WebGL | Headless | Aryan | Yes — requires visual validation |
| 18 | RGB texture | ⚠️ NOT TESTED | Depends on artifact contract | Headless | Aryan | No — architecture ready |
| 19 | Height exaggeration | ✅ PASS | Existing tests verify display-only via `mesh.scale.y` | Headless | Aryan | No |
| 20 | Flythrough | ✅ PASS | Existing tests verify trajectory workflow | Headless | Aryan | No |
| 21 | Measurements | ✅ PASS | Existing tests verify measurement tools | Headless | Aryan | No |
| 22 | Profile | ✅ PASS | Existing tests verify elevation profile | Headless | Aryan | No |
| 23 | Metadata | ✅ PASS | Existing tests verify scientific metadata | Headless | Aryan | No |
| 24 | Session reset | ✅ PASS | Existing tests verify session lifecycle | Headless | Aryan | No |
| 25 | Offline DA-V2 | ⚠️ NOT TESTED | Requires real DA-V2 + checkpoint cached + `HF_HUB_OFFLINE=1` | Headless | Aryan | Yes — requires real runtime |
| 26 | Cancellation | ✅ PASS | `killServiceProcess()` on abort signal; test coverage exists | Headless | Aryan | No |
| 27 | Shutdown | ✅ PASS | `before-quit` + `will-quit` + `window-all-closed` all call `killServiceProcess()` | Headless | Aryan | No |
| 28 | No orphan process | ✅ PASS | All exit paths call `killServiceProcess()` | Headless | Aryan | No |
| 29 | Portable build | ✅ PASS | `release/win-unpacked/` created (372 MB); no node_modules, no src, no .git | Windows | Aryan | No |
| 30 | NSIS installer | ✅ PASS | `DepthWizard Setup 0.1.0.exe` created (109.8 MB) | Windows | Aryan | No |
| 31 | Install | ⚠️ NOT TESTED | Requires running NSIS installer on clean Windows | Windows | Aryan | Yes — requires manual test |
| 32 | Relaunch | ⚠️ NOT TESTED | Requires install + launch + close + relaunch | Windows | Aryan | Yes — requires manual test |
| 33 | Uninstall | ⚠️ NOT TESTED | Requires running NSIS uninstaller | Windows | Aryan | Yes — requires manual test |

## Summary

- **PASS**: 18
- **PARTIAL**: 1 (managed runtime resolution works but no bundled Python)
- **NOT TESTED**: 9 (require real runtime, visual validation, or manual Windows testing)

## Release Blockers

1. **Managed Python not bundled** — No actual Python runtime is packaged with the installer. Users must have Python installed on their system.
2. **Real DA-V2 not visually validated** — Cannot run DA-V2 inference in headless environment.
3. **Installer not manually tested** — NSIS installer created but not tested on clean Windows.
4. **Checkpoint not bundled** — External provision required; no auto-download mechanism.
