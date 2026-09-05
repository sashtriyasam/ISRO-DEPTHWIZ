# Installer Strategy

Generated: 2026-09-04 | Updated: 2026-09-05

## Packaging Tool

**electron-builder 26.0.12**

## Build Output

| Artifact | Size | Description |
|----------|------|-------------|
| `DepthWizard Setup 0.1.0.exe` | 109.8 MB | NSIS installer |
| `release/win-unpacked/` | 372.2 MB | Portable unpacked build |

## NSIS Configuration

| Setting | Value |
|---------|-------|
| One-click | `false` (allows custom install directory) |
| Change install directory | Allowed |
| Desktop shortcut | Created |
| Start menu shortcut | Created |
| Uninstall display name | `DepthWizard` |

## Packaged Layout

```
DepthWizard Setup 0.1.0.exe (NSIS installer)
  └─ DepthWizard/
       DepthWizard.exe
       resources/
         app.asar              (renderer + electron main/preload)
         scripts/
           depthwiz_service.py
           backend_bridge.py
         elevate.exe
         app-update.yml
```

## Checkpoint Policy

**External provision** — checkpoint is NOT bundled in the installer.

| Aspect | Value |
|--------|-------|
| Location | `%APPDATA%/DepthWizard/checkpoints/depth_anything_v2_vits.pth` |
| Size | ~99 MB |
| Verification | SHA-256 hash matching |
| Download | Manual placement or future auto-download |

## Runtime Policy

**No Python bundled** — users must have Python installed.

| Aspect | Value |
|--------|-------|
| Resolution | `DEPTHWIZARD_PYTHON` → `<resources>/python/python.exe` → `python` on PATH |
| Packaged fallback | System Python on PATH |

## Upgrade Behavior

- NSIS supports in-place upgrade
- App data preserved across upgrades
- Checkpoint preserved across upgrades

## Uninstall Behavior

### Removed by NSIS uninstaller
- Application binaries
- Start menu shortcuts
- Desktop shortcuts

### Preserved
- `%APPDATA%/DepthWizard/` (checkpoint, logs, config)
