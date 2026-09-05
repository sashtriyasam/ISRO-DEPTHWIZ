# Native Host Technology Decision

Generated: 2026-09-04

## Candidates

| Criterion | Tauri | Electron | Weight |
|-----------|-------|----------|--------|
| 1. Current repo compatibility | ❌ No Rust/Cargo installed | ✅ Node.js v24.14.0 available | High |
| 2. Vite/React compatibility | ✅ Good (tauri-plugin-vite) | ✅ Excellent (electron-vite) | High |
| 3. Windows support | ✅ Excellent | ✅ Excellent | High |
| 4. Python subprocess management | ✅ Rust std::process | ✅ Node child_process | High |
| 5. Filesystem access | ✅ Rust fs | ✅ Node fs | Medium |
| 6. Installer support | ✅ tauri-bundler (WiX/NSIS) | ✅ electron-builder (NSIS/WiX) | Medium |
| 7. Security model | ✅ Rust IPC, capabilities | ⚠️ Node IPC, contextIsolation | Medium |
| 8. Runtime footprint | ✅ ~5-10MB | ⚠️ ~150-200MB (Chromium) | Low |
| 9. Build complexity | ⚠️ Requires Rust toolchain | ✅ Node-only | High |
| 10. CI/build reproducibility | ⚠️ Rust version pinning | ✅ Node version pinning | Medium |
| 11. Long-term maintenance | ✅ Active, memory-safe | ✅ Active, large ecosystem | Low |
| 12. License | ✅ MIT/Apache-2.0 | ✅ MIT | Low |
| 13. Team familiarity (repo evidence) | ❌ No Rust in repo | ✅ Node.js throughout | High |
| 14. Dependency footprint | ✅ Minimal native deps | ⚠️ Bundles Chromium | Medium |

## Decision

**Electron** is selected.

### Evidence-Based Reasons

1. **No Rust toolchain exists** on this system. Installing Rust globally just to make Tauri selectable violates the principle of smallest mature technology.

2. **Node.js is already available** (v24.14.0). Electron requires only Node.js + npm.

3. **The entire repository is Node.js/TypeScript.** Electron integrates naturally with the existing Vite/React build pipeline.

4. **Python subprocess management** is identical in both — `child_process.spawn()` in Electron mirrors what the current `SubprocessServiceTransport` already does via Node.

5. **The team's repo evidence is entirely Node.js.** No Rust, no Cargo, no CMake.

6. **Build complexity** is minimal with Electron — `npm run build` produces the app.

### When Tauri Would Be Preferred

If the project later requires:
- Native memory safety guarantees
- <10MB binary size
- No Chromium bundling
- Rust backend services

...then a Tauri migration is possible. The host seam is designed to be framework-neutral.

## Security Model

### Allowed (Native Host API)

| Capability | Scope |
|-----------|-------|
| Get host capabilities | Read-only system info |
| Resolve Python path | `DEPTHWIZARD_PYTHON` env or `python` on PATH |
| Resolve checkpoint path | `DW_DAV2_CKPT` env or default location |
| Launch service | Spawn `depthwiz_service.py` subprocess |
| Terminate service | Kill owned subprocess |
| Read stdout/stdout | Protocol data + diagnostics |
| Stage input files | Write to temp directory |
| Clean staged files | Delete temp directory |

### Denied (Renderer → Native)

| Capability | Reason |
|-----------|--------|
| Arbitrary executable path | Security: code execution |
| Arbitrary shell strings | Security: injection |
| Arbitrary URLs | Security: network |
| Arbitrary pip install | Security: package injection |
| Arbitrary Python module execution | Security: code execution |
| Arbitrary filesystem read/write | Security: data exfiltration |

### IPC Boundary

```
Renderer (React)
    ↕ invoke('method', args)
Native Main Process (Electron)
    ↕ child_process.spawn()
Python Service (depthwiz_service.py)
```

The renderer never directly spawns processes. All subprocess management goes through the native main process.
