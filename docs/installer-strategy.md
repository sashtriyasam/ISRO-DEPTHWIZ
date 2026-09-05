# Installer Strategy

Generated: 2026-09-04

## Selected Strategy

**Electron Builder (NSIS installer) — Windows first.**

## Distribution Model

| Aspect | Decision |
|--------|----------|
| Framework | Electron Builder |
| Format | NSIS installer (Windows) |
| Package manager | npm (Node.js) |
| Managed runtime | Bundled Python via `python-embeddable` or `pyinstaller`-bundled service |
| Checkpoint | External provision (first-run download or manual placement) |

## Windows Behavior

| Aspect | Implementation |
|--------|---------------|
| Executable | `DepthWizard.exe` |
| App data | `%APPDATA%/DepthWizard/` |
| Temp directory | `%TEMP%/DepthWizard/` |
| Runtime directory | `%LOCALAPPDATA%/DepthWizard/python/` |
| Checkpoint location | `%APPDATA%/DepthWizard/checkpoints/` |
| Logs | `%APPDATA%/DepthWizard/logs/` |
| Uninstall | Windows Programs & Features + NSIS uninstaller |

## Managed Runtime Strategy

The packaged product bundles a Python runtime so users don't need Python installed.

### Options Evaluated

| Option | Pros | Cons |
|--------|------|------|
| `python-embeddable` | Official, small, no install | Windows-only, limited pip |
| `PyInstaller` single-file | Cross-platform, self-contained | Large binary, slow startup |
| `conda-pack` | Full environment | Very large |
| User-provided Python | No bundling | Requires user setup |

### Selected: python-embeddable + pip install

Bundle `python-embeddable` for Windows. On first run:
1. Extract embedded Python to app data directory
2. Run `python -m pip install -e .` to install depthwizard
3. Verify with `runtime_check`

This gives a self-contained product without requiring user Python installation.

## Checkpoint Distribution

| Aspect | Decision |
|--------|----------|
| Strategy | First-run download from HuggingFace |
| Verification | SHA-256 hash matching |
| Offline | Manual placement in checkpoints directory |
| Size | ~100MB (DA-V2 Small weights) |

### First-Run Flow

1. Native host checks `%APPDATA%/DepthWizard/checkpoints/depth_anything_v2_vits.pth`
2. If missing → download from `https://huggingface.co/depth-anything/Depth-Anything-V2-Small/resolve/main/depth_anything_v2_vits.pth`
3. Verify SHA-256 matches `715fade13be8f229f8a70cc02066f656f2423a59effd0579197bbf57860e1378`
4. If hash mismatch → delete and retry or report error

### Offline Support

For machines without internet:
1. User manually downloads checkpoint file
2. Places it in `%APPDATA%/DepthWizard/checkpoints/`
3. Native host detects existing file, verifies hash, proceeds

## Upgrade Behavior

- NSIS installer supports upgrade (same install location)
- Python runtime: upgrade in-place
- Checkpoint: preserved across upgrades (same hash)
- App data: preserved across upgrades

## Uninstall Behavior

- NSIS uninstaller removes:
  - Application files
  - Python runtime
  - Checkpoint files
  - App data (with user confirmation)
  - Start menu shortcuts

## Application Data Layout

```
%APPDATA%/DepthWizard/
  checkpoints/
    depth_anything_v2_vits.pth
  logs/
    depthwizard.log
  config.json
```

%LOCALAPPDATA%/DepthWizard/
  python/
    python.exe
    Lib/site-packages/depthwizard/
```
