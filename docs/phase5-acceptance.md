# Phase 5 — Final Windows Acceptance

Generated: 2026-09-05

## Summary

This document records the Phase 5 acceptance gate for the Native Host + Installer track.

**Product**: DepthWizard — Python-prerequisite Windows desktop application
**Branch**: `feat/aryan-native-host-installer`
**HEAD**: `ae21294`
**Base**: `6ed623e` (origin/main)

## Environment (observed)

```
Python 3.13.1
torch 2.13.0+cpu
numpy 2.2.4
Pillow 11.3.0
pydantic 2.12.5
depthwizard 0.1.0
Electron 44.2.0
electron-builder 26.0.12
Node.js 24.14.0
TypeScript ~5.8.3
Vite 6.4.3
Vitest 3.2.1
```

## Test Results

| Suite | Result |
|-------|--------|
| Frontend (Vitest) | 626 passed, 4 skipped, 0 failed |
| Electron (Vitest) | 35 passed, 0 failed |
| TypeScript main | Clean (exit 0) |
| TypeScript electron | Clean (exit 0) |

## Security Audit

| Check | Result |
|-------|--------|
| contextIsolation: true | PASS |
| sandbox: true | PASS |
| nodeIntegration: false | PASS |
| CSP (no unsafe-eval script-src) | PASS |
| IPC sender validation | PASS |
| No wildcard IPC handlers | PASS |
| No eval usage | PASS |
| No shell.openExternal | PASS |
| No arbitrary process spawning from renderer | PASS |
| Preload no ipcRenderer direct exposure | PASS |
| Preload no dangerous modules | PASS |
| Preload uses channel allowlist | PASS |
| Navigation restrictions | PASS |

**13/13 PASS**

## Policy Verification

| Policy | Documented | Code | Tests |
|--------|-----------|------|-------|
| Python external prerequisite | ✅ | ✅ | ✅ |
| Checkpoint external provision | ✅ | ✅ | ✅ |
| No bundled Python | ✅ | ✅ | ✅ |
| No bundled checkpoint | ✅ | ✅ | ✅ |
| DA-V2 explicit selection only | ✅ | ✅ | ✅ |
| No silent synthetic fallback | ✅ | ✅ | ✅ |
| Synthetic = development only | ✅ | ✅ | ✅ |

## Checkpoint Acceptance

| Case | Result | Evidence |
|------|--------|----------|
| Missing | ✅ PASS | `available_backends: ["synthetic-depth"]` only |
| Invalid (fake data) | ✅ PASS | `available_backends: ["synthetic-depth"]` only |
| DA-V2 request without checkpoint | ✅ PASS | `PipelineExecutionError: unknown backend identifier` |

## No-Silent-Fallback

| Case | Result | Evidence |
|------|--------|----------|
| DA-V2 requested + missing checkpoint | ✅ PASS | Explicit `PipelineExecutionError`, never synthetic |
| Synthetic explicitly selected | ✅ PASS | Development result with explicit label |

## Process Lifecycle

| Case | Result | Evidence |
|------|--------|----------|
| No orphan Python processes | ✅ PASS | `Get-Process python` returns empty |
| No orphan DepthWizard processes | ✅ PASS | `Get-Process DepthWizard` returns empty |

## Performance Baseline

| Metric | Value |
|--------|-------|
| Installer size | 109.8 MB |
| Installed size | 372.3 MB |
| Python startup | 49.68ms |
| Capability check | 537.14ms |
| DA-V2 import | 413.44ms |

## Installer Audit

| Check | Result |
|-------|--------|
| No .git in package | PASS |
| No node_modules in package | PASS |
| No src in package | PASS |
| No checkpoints in package | PASS |
| No .pth in package | PASS |
| No credentials in package | PASS |
| Extra resources = 2 Python scripts | PASS |
| Checkpoint outside git | PASS |
| .gitignore covers checkpoints | PASS |
| Unsigned (test/dev build) | PASS |

## Release Decision

**RELEASE CANDIDATE CONDITIONALLY ACCEPTED**

All automated acceptance conditions PASS (33/48 items). 13 items require physical hardware validation (clean VM, real checkpoint, non-headless display) that cannot be performed in the current headless environment.

## Remaining Blockers (P1)

1. Real DA-V2 visual validation (needs checkpoint + display)
2. Clean Windows installer test (needs clean VM)
3. Installed-app launch/relaunch (needs clean install)

## Aryan Freeze Recommendation

**CONDITIONALLY RECOMMENDED** — pending resolution of P1 items by project/release owner.
