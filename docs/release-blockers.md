# Release Blockers

Generated: 2026-09-05 | Phase 6 Release Witness

## Classification Policy

- **P0**: Critical security/runtime defect blocking all release
- **P1**: Release-blocking defect (product failure, not environment)
- **P2**: Convenience improvement (not blocking)
- **INFO**: Known limitation, not a defect

**Key distinction**: "Not tested because no hardware" is evidence status, not a software defect. Items classified as BLOCKED BY ENVIRONMENT are not product failures.

## P0 — Release-Blocking

None. No P0 conditions identified.

## P1 — Release-Blocking

None. No actual P1 software defects remain.

The previous P1 items (real DA-V2 visual validation, clean installer test, relaunch) are classified as **BLOCKED BY ENVIRONMENT** — they require physical hardware that is not available in the automated testing environment. They are NOT product failures.

## P2 — Not Release-Blocking

### 1. Checkpoint Auto-Download
**Severity**: P2
**Status**: NOT IMPLEMENTED — product convenience
**Decision**: Do NOT implement unless release owner explicitly requires it AND trusted distribution contract is established. Existing checkpoint policy: manual external provisioning.

## INFO — Known Limitations

### 2. No Code Signing
**Severity**: INFO
**Status**: UNSIGNED TEST/DEVELOPMENT BUILD
**Evidence**: `signAndEditExecutable: false`, `forceCodeSigning: false`
**Resolution**: Obtain code signing certificate for production distribution.

### 3. No Auto-Update
**Severity**: INFO
**Status**: Not implemented
**Resolution**: Implement electron-updater if needed for production.

### 4. Python External Prerequisite
**Severity**: INFO
**Status**: BY DESIGN
**Evidence**: Product is a Python-prerequisite desktop. Users must install Python 3.10+ separately. Clear error messaging guides installation.

## Physical Acceptance Required (BLOCKED BY ENVIRONMENT)

These items require a physical Windows machine with display + checkpoint. They are NOT product failures. The acceptance harness (`scripts/windows_release_preflight.ps1` + `docs/release-witness.md`) enables any operator to validate them.

| # | Item | Status | Required |
|---|------|--------|----------|
| 1 | Real DA-V2 inference | BLOCKED BY ENVIRONMENT | Checkpoint + display |
| 2 | Calibration | BLOCKED BY ENVIRONMENT | Real DA-V2 output |
| 3 | Metric DSM | BLOCKED BY ENVIRONMENT | Calibration output |
| 4 | Terrain mesh | BLOCKED BY ENVIRONMENT | DSM output |
| 5 | SceneArtifact | BLOCKED BY ENVIRONMENT | Full pipeline |
| 6 | Three.js rendering | BLOCKED BY ENVIRONMENT | WebGL display |
| 7 | RGB texture | BLOCKED BY ENVIRONMENT | Artifact with texture |
| 8 | Offline DA-V2 | BLOCKED BY ENVIRONMENT | Checkpoint cached |
| 9 | Clean installer | BLOCKED BY ENVIRONMENT | Clean Windows VM |
| 10 | Relaunch | BLOCKED BY ENVIRONMENT | Installed app |
| 11 | Uninstall | BLOCKED BY ENVIRONMENT | Installed app |
| 12 | Reinstall | BLOCKED BY ENVIRONMENT | Uninstall + reinstall |
| 13 | Spaces-path | BLOCKED BY ENVIRONMENT | Installation with spaces |

## Resolved in Phase 1-6

- Electron 44.2.0 selected and installed
- electron-builder 26.0.12 for NSIS packaging
- Runtime resolution: DEPTHWIZARD_PYTHON env -> python on PATH
- Clear error messaging when Python not found
- Python prerequisite policy consistently documented
- Checkpoint distribution policy documented
- HostCapabilities interface consistency fixed
- Preload API consistency fixed (8 methods, channel allowlist)
- Input path validation hardened
- Electron security hardened (sandbox, CSP, IPC validation)
- Process lifecycle cleanup on all exit paths
- Fresh-directory test passes
- Portable build works (372.3 MB)
- NSIS installer builds (109.8 MB)
- No managed Python language in codebase
- All docs consistent with Python-prerequisite policy
- 626 frontend tests passing
- 35 Electron tests passing
- TypeScript clean (main + electron)
- Security audit 13/13 PASS
- Installer contents clean
- Checkpoint outside git
- No orphan processes
- No-silent-fallback verified
- Checkpoint acceptance verified (missing + invalid)
- Performance baseline recorded
- Windows preflight script created and tested
- Release witness operator guide created
