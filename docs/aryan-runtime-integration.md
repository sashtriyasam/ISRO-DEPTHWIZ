# Aryan Runtime Integration

Generated: 2026-09-04

## Canonical Main State

| Feature | Status |
|---------|--------|
| Python scientific engine | ✅ ON MAIN (`src/depthwizard/`) |
| DA-V2 production backend | ✅ ON MAIN (`src/depthwizard/backends/depth_anything_v2.py`) |
| DA-V2 runtime verification | ✅ ON MAIN (commit `6ed623e`) |
| Aryan desktop integration | ✅ ON MAIN (merged via `feat/shivam-aryan-integration-readiness`) |
| Runtime packaging | ❌ NOT ON MAIN (no installer/packaging branches exist) |
| Native host support | ❌ NOT ON MAIN (browser/node detection only) |
| Installer | ❌ NOT ON MAIN |

## Canonical Runtime Contract

### Python Runtime Resolution

The service expects a Python interpreter with `depthwizard` installed.

**Resolution order:**
1. `DEPTHWIZARD_PYTHON` environment variable (explicit path)
2. `python` on PATH (development fallback)

**Packaged products should prefer an explicit managed runtime path.** The native host provides this.

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
| Synthetic | `synthetic-depth` | Always available (development) |
| DA-V2 | `depth-anything-v2-small` | Requires torch + checkpoint |

**Policy:** Explicit real DA-V2 request + unavailable runtime = ERROR. Never silently fall back to synthetic.

### Checkpoint Resolution

```
DW_DAV2_CKPT environment variable
  → checkpoints/depth_anything_v2_vits.pth (project root fallback)
```

- Checkpoint is externally provisioned (not in git)
- SHA-256 verification: `715fade13be8f229f8a70cc02066f656f2423a59effd0579197bbf57860e1378`
- Python runtime is authority for final validation
- Host may perform early existence preflight

### Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `DEPTHWIZARD_PYTHON` | Python interpreter path | No (dev fallback) |
| `DW_DAV2_CKPT` | DA-V2 checkpoint path | No (uses default) |

### Expected Directory Structure (Packaged)

```
<app-root>/
  python/                    # Managed Python runtime
    python.exe               # Windows
    Lib/site-packages/       # depthwizard installed here
  checkpoints/
    depth_anything_v2_vits.pth
  resources/
    depthwiz_service.py      # Service entrypoint
    backend_bridge.py        # Bridge script
```

### Failure Taxonomy

| Error | Cause | Resolution |
|-------|-------|-----------|
| `ImportError` | depthwizard not installed | Install in managed runtime |
| `ModelInferenceError` | DA-V2 inference failed | Check checkpoint, GPU memory |
| `InvalidInputError` | Bad input file | User action: different file |
| Wire error | Service protocol failure | Check stderr, restart service |
| Non-zero exit | Process/wire failure | Check stderr diagnostics |

## Consumed Interface vs Canonical Implementation

| Component | Owner | Aryan Consumes |
|-----------|-------|---------------|
| Python scientific engine | Shivam | Via service protocol |
| DA-V2 backend | Shivam | Via service protocol |
| Checkpoint verification | Shivam | Via service protocol |
| Runtime provisioning | **Aryan (native host)** | Implements resolution |
| Service launch | **Aryan (native host)** | Spawns subprocess |
| Service lifecycle | **Aryan (native host)** | Manages process |
