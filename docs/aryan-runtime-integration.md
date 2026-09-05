# Aryan Runtime Integration

Generated: 2026-09-04 | Updated: 2026-09-05

## Canonical Main State

| Feature | Status |
|---------|--------|
| Python scientific engine | ✅ ON MAIN (`src/depthwizard/`) |
| DA-V2 production backend | ✅ ON MAIN (`src/depthwizard/backends/depth_anything_v2.py`) |
| DA-V2 runtime verification | ✅ ON MAIN (commit `6ed623e`) |
| Aryan desktop integration | ✅ ON MAIN (merged via `feat/shivam-aryan-integration-readiness`) |
| Runtime provisioning | ❌ NOT ON MAIN (branch `daf3482`) |
| Runtime packaging | ❌ NOT ON MAIN (branch `31389f3`) |
| `runtime_check.py` | ❌ NOT ON MAIN |
| `src/depthwizard/runtime/` | ❌ NOT ON MAIN |

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

| Backend | Name | Availability |
|---------|------|-------------|
| Synthetic | `synthetic-depth` | Always available |
| DA-V2 | `depth-anything-v2-small` | Requires `depth_anything_v2` + `torch` + checkpoint |

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

| Component | Owner | Aryan Consumes |
|-----------|-------|---------------|
| Python scientific engine | Shivam | Via service protocol |
| DA-V2 backend | Shivam | Via service protocol |
| Checkpoint verification | Shivam | Via service protocol |
| Runtime provisioning | Shivam (branch only) | NOT on main |
| `runtime_check.py` | Shivam (branch only) | NOT on main |
| Runtime resolution | **Aryan (native host)** | Implements in `electron/main.ts` |
| Service launch | **Aryan (native host)** | Spawns subprocess |
| Service lifecycle | **Aryan (native host)** | Manages process |
