# Native Host

Generated: 2026-09-04 | Updated: 2026-09-05

## Technology

**Electron 44.2.0** (stable, Sep 3, 2026)
- Chromium: 152.0.7977.76
- Node.js: 24.20.0
- License: MIT

## Architecture

```
Renderer (React + Three.js)
    ↕ contextBridge (preload.ts)
Electron Main Process (main.ts)
    ↕ child_process.spawn()
Python Service (depthwiz_service.py)
    ↕ depthwizard package
DA-V2 Backend / Synthetic Backend
```

## Security Configuration

| Setting | Value |
|---------|-------|
| `contextIsolation` | `true` |
| `nodeIntegration` | `false` |
| `sandbox` | `true` |
| `webSecurity` | `true` |
| `allowRunningInsecureContent` | `false` |
| `experimentalFeatures` | `false` |
| `nodeIntegrationInWorker` | `false` |
| `nodeIntegrationInSubFrames` | `false` |
| `navigateOnDragDrop` | `false` |

## CSP

```
default-src 'self';
script-src 'self';
style-src 'self' 'unsafe-inline';
img-src 'self' data: blob:;
font-src 'self' data:;
connect-src 'self';
media-src 'none';
object-src 'none';
frame-src 'none';
worker-src 'self' blob:;
```

## IPC Security

- **Sender validation**: Every handler checks `event.sender === mainWindow?.webContents`
- **Channel allowlist**: Preload uses explicit set, rejects unknown channels
- **No raw ipcRenderer**: Exposed via `safeInvoke()` wrapper only
- **No wildcard handlers**: No `ipcMain.handle("*", ...)`

## Preload API

| Method | Purpose |
|--------|---------|
| `getHostCapabilities()` | Read-only host info (runtime, platform, packaged) |
| `resolvePythonPath()` | Resolved Python executable path |
| `resolveCheckpointPath()` | Resolved checkpoint file path |
| `getCheckpointStatus()` | Checkpoint existence + hash info |
| `getScriptsDir()` | Resolved scripts directory path |
| `launchService(args)` | Start long-running Python service |
| `terminateService()` | Kill owned subprocess |
| `executeService(args)` | One-shot service execution with timeout |

## Runtime Resolution

### Python

**Packaged mode** (priority):
1. `DEPTHWIZARD_PYTHON` env (developer override)
2. `<resources>/python/python.exe` (managed runtime)
3. No fallback to system Python

**Development mode**:
1. `DEPTHWIZARD_PYTHON` env
2. `python` on PATH

### Checkpoint

1. `DW_DAV2_CKPT` env (explicit override)
2. `%APPDATA%/DepthWizard/checkpoints/depth_anything_v2_vits.pth` (user data)
3. `<resources>/checkpoints/depth_anything_v2_vits.pth` (bundled, if present)

## Process Lifecycle

| Event | Action |
|-------|--------|
| App ready | Register IPC, create window |
| `before-quit` | Kill service |
| `will-quit` | Kill service |
| `window-all-closed` | Kill service, quit (non-macOS) |
| Renderer crash | Kill service, log error |
| Service timeout | Kill process, return error |

## Build Commands

```bash
npm run build:electron          # Build renderer + compile Electron TS
npm run electron:dev            # Development with hot reload
npm run electron:build:win      # Windows NSIS installer
npm run electron:build:portable # Portable unpacked build
```
