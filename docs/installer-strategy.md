# Installer Strategy

Generated: 2026-09-04 | Updated: 2026-09-05

## Packaging Tool

**electron-builder 26.0.12** — the single maintained packager for this project.

## Build Configuration

| Aspect | Value |
|--------|-------|
| App ID | `com.depthwizard.desktop` |
| Product Name | `DepthWizard` |
| Format | NSIS installer (Windows) |
| Output | `release/` directory |
| Asar | Enabled, with `scripts/` and `checkpoints/` unpacked |

## Windows Behavior

| Aspect | Implementation |
|--------|---------------|
| Executable | `DepthWizard.exe` |
| Install directory | User-selectable (default: `%LOCALAPPDATA%/DepthWizard`) |
| App data | `%APPDATA%/DepthWizard/` |
| Temp directory | `%TEMP%/DepthWizard/` |
| Runtime directory | `<install>/resources/python/` |
| Checkpoint location | `%APPDATA%/DepthWizard/checkpoints/` |
| Logs | `%APPDATA%/DepthWizard/logs/` |
| Uninstall | Windows Programs & Features + NSIS uninstaller |
| Desktop shortcut | Created |
| Start menu shortcut | Created |

## NSIS Configuration

| Setting | Value |
|---------|-------|
| One-click | `false` (allows custom install directory) |
| Change install directory | Allowed |
| Desktop shortcut | Created |
| Start menu shortcut | Created |
| Uninstall display name | `DepthWizard` |

## Managed Runtime Strategy

The packaged product bundles a Python runtime so users don't need Python installed.

### Resolution Order

1. Explicit managed path (`<install>/resources/python/python.exe`)
2. `DEPTHWIZARD_PYTHON` environment variable
3. `python` on PATH (development fallback)

### Packaged Layout

```
DepthWizard-win32-x64/
  DepthWizard.exe
  resources/
    app.asar
    scripts/
      depthwiz_service.py
      backend_bridge.py
    checkpoints/
      depth_anything_v2_vits.pth
```

## Checkpoint Distribution

| Aspect | Decision |
|--------|----------|
| Strategy | External provision (not bundled in installer) |
| Default location | `%APPDATA%/DepthWizard/checkpoints/` |
| Verification | SHA-256 hash matching |
| Offline | Manual placement |
| Size | ~99MB (DA-V2 Small weights) |

### First-Run Flow

1. Native host checks `%APPDATA%/DepthWizard/checkpoints/depth_anything_v2_vits.pth`
2. If missing → prompt user or download from HuggingFace
3. Verify SHA-256 matches `715fade13be8f229f8a70cc02066f656f2423a59effd0579197bbf57860e1378`
4. If hash mismatch → delete and report error

## Upgrade Behavior

- NSIS installer supports upgrade (same install location)
- Python runtime: upgrade in-place
- Checkpoint: preserved across upgrades (same hash)
- App data: preserved across upgrades

## Uninstall Behavior

### Removed

- Application binaries
- Start menu shortcuts
- Desktop shortcuts
- Bundled resources (scripts, runtime)

### Preserved (with user confirmation)

- User model/runtime cache (`%APPDATA%/DepthWizard/`)
- Checkpoint files
- Application data
- Logs

## License

| Component | License |
|-----------|---------|
| Electron | MIT |
| electron-builder | MIT |
| DepthWizard | Project license |

No unlicensed binaries.
