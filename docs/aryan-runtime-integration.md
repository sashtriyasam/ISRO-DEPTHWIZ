# Aryan Runtime Integration

**Generated:** 2026-09-06 | **Updated:** 2026-09-06

## Canonical Main State (as of 809801d)

| Feature                           | Status     | Location                                                                       |
| --------------------------------- | ---------- | ------------------------------------------------------------------------------ |
| Python scientific engine          | ✅ ON MAIN | `src/depthwizard/`                                                             |
| DA-V2 production backend          | ✅ ON MAIN | `src/depthwizard/backends/depth_anything_v2.py`                                |
| DA-V2 runtime verification (S16R) | ✅ ON MAIN | Commit `6ed623e` / `07bc635`                                                   |
| Aryan desktop integration         | ✅ ON MAIN | Merged via `feat/shivam-aryan-integration-readiness`                           |
| **Runtime provisioning (S18)**    | ✅ ON MAIN | `scripts/provision_runtime.py`, `src/depthwizard/runtime/provision.py` (PR #1) |
| **Runtime packaging (S17)**       | ✅ ON MAIN | `scripts/runtime_check.py`, `src/depthwizard/runtime/diagnostics.py` (PR #1)   |
| `runtime_check.py`                | ✅ ON MAIN | `scripts/runtime_check.py`                                                     |
| `src/depthwizard/runtime/`        | ✅ ON MAIN | `diagnostics.py`, `provision.py`, `__init__.py`                                |
| Native Electron host              | ✅ ON MAIN | `electron/main.ts`, `electron/preload.ts` (PR #2)                              |
| Windows installer (NSIS)          | ✅ ON MAIN | `electron-builder.yml` (PR #2)                                                 |

## Canonical Runtime Contract

### Python Runtime Resolution

This application requires Python to be installed externally. No Python runtime is bundled.

**Resolution priority:**

1. `DEPTHWIZARD_PYTHON` env (explicit override)
2. `python` on PATH (system Python)

If Python is not found, a clear error message is displayed: "Install Python 3.10+ and ensure it is on PATH."

### Service Entrypoint

```
scripts/depthwiz_service.py
```

- Reads JSON from stdin
- Writes JSON to stdout
- Diagnostics to stderr
- Exit 0 for valid wire exchange (even failed runs)
- Non-zero for wire/process failure only

### Backend Selection

| Backend   | Name                      | Availability                                        |
| --------- | ------------------------- | --------------------------------------------------- |
| Synthetic | `synthetic-depth`         | Always available                                    |
| DA-V2     | `depth-anything-v2-small` | Requires `depth_anything_v2` + `torch` + checkpoint |

**Policy:** Explicit DA-V2 request + unavailable → ERROR. Never silently fall back to synthetic.

### Checkpoint Resolution

1. `DW_DAV2_CKPT` env
2. `%APPDATA%/DepthWizard/checkpoints/depth_anything_v2_vits.pth`
3. `<resources>/checkpoints/depth_anything_v2_vits.pth`

Expected SHA-256: `715fade13be8f229f8a70cc02066f656f2423a59effd0579197bbf57860e1378`

### Service Capabilities

Request: `{"capabilities": true}`
Response: `{"capabilities": {"contract_version": "1", "available_backends": [...], ...}}`

The `available_backends` list advertises which backends are registered.

## Consumed Interface vs Canonical Implementation

| Component                      | Owner                   | Aryan Consumes                   |
| ------------------------------ | ----------------------- | -------------------------------- |
| Python scientific engine       | Shivam                  | Via service protocol             |
| DA-V2 backend                  | Shivam                  | Via service protocol             |
| Checkpoint verification        | Shivam                  | Via service protocol             |
| **Runtime provisioning (S18)** | **Shivam**              | ✅ **ON MAIN**                   |
| **`runtime_check.py` (S17)**   | **Shivam**              | ✅ **ON MAIN**                   |
| Runtime resolution             | **Aryan (native host)** | Implements in `electron/main.ts` |
| Service launch                 | **Aryan (native host)** | Spawns subprocess                |
| Service lifecycle              | **Aryan (native host)** | Manages process                  |

---

**Note:** This document was previously stale (claiming S17/S18 "NOT ON MAIN"). Updated to reflect actual main state at `809801d`.
