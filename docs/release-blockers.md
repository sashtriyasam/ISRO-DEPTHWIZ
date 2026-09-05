# Release Blockers

Generated: 2026-09-05 | Phase 5 Final Acceptance

## P0 — Release-Blocking

None. No P0 conditions identified.

## P1 — Release-Blocking (require physical hardware)

### 1. Real DA-V2 Desktop Visual Validation
**Severity**: P1
**Status**: BLOCKED — requires checkpoint + non-headless display
**Evidence**: Checkpoint `depth_anything_v2_vits.pth` not present on acceptance machine. DA-V2 import chain works (`DepthAnythingV2Backend` imports successfully). Service correctly excludes DA-V2 when checkpoint missing. Architecture verified end-to-end in automated tests.
**Resolution**: Provision checkpoint to `%APPDATA%/DepthWizard/checkpoints/` on a machine with display + Python + torch, then run real DA-V2 flow.

### 2. Clean Windows Installer Test
**Severity**: P1
**Status**: BLOCKED — requires clean Windows VM/machine
**Evidence**: NSIS installer builds (109.8 MB, unsigned). Portable build works (372.3 MB). Installer contents clean (no source, no checkpoints, no credentials).
**Resolution**: Test on clean Windows machine: install → launch → verify runtime → close → relaunch → uninstall.

### 3. Installed-App Launch/Relaunch Validation
**Severity**: P1
**Status**: BLOCKED — requires clean install
**Evidence**: Application data directory creation, shortcut creation, and relaunch behavior cannot be validated without physical installation.
**Resolution**: Part of clean Windows installer test.

## P2 — Not Release-Blocking

### 4. Checkpoint Auto-Download
**Severity**: P2
**Status**: NOT IMPLEMENTED — product convenience, not release-blocking
**Resolution options**:
- A. Document manual placement (current state)
- B. Implement first-run download from HuggingFace (requires: approved URL, HTTPS, fixed artifact identity, SHA-256, resume, atomic write)

**Decision**: Do NOT implement auto-download to remove P2. Only implement if project/release owner explicitly requires it AND the trusted distribution contract is established.

## INFO — Known Limitations

### 5. No Code Signing
**Severity**: INFO
**Status**: UNSIGNED TEST/DEVELOPMENT BUILD
**Evidence**: `signAndEditExecutable: false`, `forceCodeSigning: false` in electron-builder.yml
**Resolution**: Obtain code signing certificate for production distribution. Do not claim production signing.

### 6. No Auto-Update
**Severity**: INFO
**Status**: Not implemented
**Resolution**: Implement electron-updater if needed for production.

### 7. Python External Prerequisite
**Severity**: INFO
**Status**: BY DESIGN
**Evidence**: Product is a Python-prerequisite desktop. Users must install Python 3.10+ separately. Clear error messaging guides installation.
**Resolution**: Document in installer prerequisites / README.

## Resolved in Phase 1–5

- ✅ Electron 44.2.0 selected and installed
- ✅ electron-builder 26.0.12 for NSIS packaging
- ✅ Runtime resolution simplified: `DEPTHWIZARD_PYTHON` → `python` on PATH
- ✅ Clear error messaging when Python not found
- ✅ Python prerequisite policy consistently documented across all docs
- ✅ Checkpoint distribution policy (external provision) documented
- ✅ HostCapabilities interface consistency fixed
- ✅ Preload API consistency fixed (8 methods, channel allowlist)
- ✅ Input path validation hardened (rejects `..` traversal, executable extensions)
- ✅ Electron security hardened (sandbox, CSP, IPC validation, navigation restrictions)
- ✅ Process lifecycle cleanup on all exit paths
- ✅ Fresh-directory test passes
- ✅ Portable build works (372.3 MB)
- ✅ NSIS installer builds (109.8 MB)
- ✅ No managed Python language in codebase
- ✅ No bundled checkpoint language in codebase
- ✅ All docs consistent with Python-prerequisite policy
- ✅ 626 frontend tests passing
- ✅ 35 Electron tests passing
- ✅ TypeScript clean (main + electron)
- ✅ Security audit 13/13 PASS
- ✅ No-science-in-Electron audit 4/4 PASS
- ✅ Installer contents clean
- ✅ Checkpoint outside git
- ✅ No orphan processes
- ✅ No-silent-fallback verified
- ✅ Checkpoint acceptance verified (missing + invalid)
- ✅ Performance baseline recorded
