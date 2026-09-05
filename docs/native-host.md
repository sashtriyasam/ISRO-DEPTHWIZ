# Native Host Technology Decision

Generated: 2026-09-04 | Updated: 2026-09-05

## Technology

**Electron 44.2.0** (stable, released Sep 3, 2026)

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

## Security Model

### BrowserWindow Configuration

| Setting | Value | Reason |
|---------|-------|--------|
| `contextIsolation` | `true` | Prevents renderer accessing Electron internals |
| `nodeIntegration` | `false` | No Node.js APIs in renderer |
| `sandbox` | `true` | Renderer runs in sandboxed process |
| `webSecurity` | `true` | Enforces same-origin policy |
| `allowRunningInsecureContent` | `false` | Blocks mixed content |
| `experimentalFeatures` | `false` | No experimental Chromium features |
| `nodeIntegrationInWorker` | `false` | Workers sandboxed |
| `nodeIntegrationInSubFrames` | `false` | Sub-frames sandboxed |
| `navigateOnDragDrop` | `false` | No drag-to-navigate |

### Navigation Restrictions

- `will-navigate`: blocks all navigation except localhost in dev mode
- `setWindowOpenHandler`: denies all new window creation
- External URLs are never loaded in the application window

### Content Security Policy

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

### IPC Security

- **Sender validation**: Every IPC handler verifies the request originates from the main window's WebContents
- **Channel allowlist**: Preload uses explicit allowlist, rejects unknown channels
- **No wildcard handlers**: No `ipcMain.handle("*", ...)`
- **No raw ipcRenderer exposure**: Preload wraps all calls through `safeInvoke()`

### Preload API (Minimized)

| Method | Purpose |
|--------|---------|
| `getHostCapabilities()` | Read-only host info |
| `launchService(args)` | Start Python service subprocess |
| `terminateService()` | Kill owned subprocess |
| `executeService(args)` | One-shot service execution with timeout |

**Not exposed**: `ipcRenderer`, `shell`, `fs`, `path`, `child_process`, `process`, `require`

### Input Path Validation

- Rejects executable extensions (`.exe`, `.bat`, `.cmd`, `.com`, `.ps1`, `.sh`, `.vbs`)
- Requires normalized paths (no `..` or `.` segments)
- Only passed to known application operations

## Process Lifecycle

| Event | Action |
|-------|--------|
| App ready | Register IPC, create window |
| Window close | Set mainWindow = null |
| `window-all-closed` | Kill service, quit (non-macOS) |
| `before-quit` | Kill service |
| `will-quit` | Kill service |
| Renderer crash | Kill service, log error |
| Service crash | Clean up process handle |
| Service timeout | Kill process, reject promise |

**No orphan Python processes** after application exit.

## Environment Modes

| Mode | Vite Dev Server | Packaged Assets | Detection |
|------|----------------|-----------------|-----------|
| Development | Yes | No | `isDevMode()` = `!app.isPackaged` |
| Production | No | Yes | `isDevMode()` = `false` |

## Runtime Resolution

| Priority | Source | Fallback |
|----------|--------|----------|
| 1 | `DEPTHWIZARD_PYTHON` env | — |
| 2 | `python` on PATH | — |

The main process decides the executable. The renderer cannot control which Python is used.

## Managed Runtime (Packaged)

```
<app-root>/
  python/                         # Managed Python runtime
    python.exe
    Lib/site-packages/depthwizard/
  resources/scripts/
    depthwiz_service.py
    backend_bridge.py
  resources/checkpoints/
    depth_anything_v2_vits.pth
```

## Build System

| Tool | Purpose |
|------|---------|
| Vite | Renderer build |
| TypeScript | Main + preload compilation |
| electron-builder | Packaging + installer |

### Build Commands

```bash
npm run build:electron        # Build renderer + compile Electron TS
npm run electron:dev          # Development with hot reload
npm run electron:build:win    # Windows NSIS installer
npm run electron:build:portable  # Portable unpacked build
```
