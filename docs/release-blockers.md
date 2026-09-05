# Release Blockers

Generated: 2026-09-05

## Actual Blockers

### 1. Managed Python Runtime Not Bundled
**Severity**: P1
**Status**: BLOCKING

The packaged Electron app falls back to `python` on PATH when the managed runtime (`<resources>/python/python.exe`) is missing. No Python runtime is actually bundled with the installer.

**Impact**: Users must install Python separately and ensure it's on PATH. The packaged product is not fully self-contained.

**Resolution options**:
- Bundle `python-embeddable` with the installer (~15MB)
- Or document Python as a prerequisite and improve error messaging

### 2. Real DA-V2 Desktop Visual Validation
**Severity**: P1
**Status**: BLOCKING

The DA-V2 inference pipeline (Python → torch → DA-V2 → calibration → DSM → mesh → Three.js) has not been visually validated in a non-headless Electron environment.

**Impact**: Cannot confirm the end-to-end pipeline produces correct terrain rendering.

**Resolution**: Run on a machine with display, Python, torch, and DA-V2 checkpoint.

### 3. NSIS Installer Not Manually Tested
**Severity**: P1
**Status**: BLOCKING

The installer (`DepthWizard Setup 0.1.0.exe`, 109.8 MB) has been built but not tested on a clean Windows installation.

**Impact**: Cannot confirm install → launch → runtime check → backend → render works from installed location.

**Resolution**: Test on clean Windows machine or VM.

### 4. Checkpoint Not Auto-Downloaded
**Severity**: P2
**Status**: BLOCKING

The ~99MB DA-V2 checkpoint must be manually placed in `%APPDATA%/DepthWizard/checkpoints/`. No auto-download mechanism exists.

**Impact**: First-time users cannot use DA-V2 without manual setup.

**Resolution**: Implement first-run download from HuggingFace or document manual placement.

## Non-Blocking Issues

### 5. No Code Signing
**Severity**: P2
**Status**: KNOWN

The installer is unsigned. Windows SmartScreen will warn users.

**Resolution**: Obtain code signing certificate for production distribution.

### 6. No Auto-Update
**Severity**: P3
**Status**: KNOWN

No auto-update mechanism. Users must re-download and reinstall for updates.

**Resolution**: Implement electron-updater if needed for production.

## Resolved in Phase 3

- ✅ Managed Python resolution contract clarified
- ✅ Checkpoint distribution policy (external provision)
- ✅ Provisioning vs self-check distinguished
- ✅ HostCapabilities interface consistency fixed
- ✅ Preload API consistency fixed
- ✅ Input path validation hardened
- ✅ Duplicate script bundling fixed
- ✅ Electron security hardened (sandbox, CSP, IPC validation)
- ✅ Process lifecycle cleanup on all exit paths
- ✅ Fresh-directory test passes
- ✅ Portable build works (372 MB)
- ✅ NSIS installer builds (109.8 MB)
