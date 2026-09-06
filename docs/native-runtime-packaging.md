# Native Runtime Packaging Contract

**Updated:** 2026-09-06 — Native host + installer now ON MAIN (PR #2)

## Current State

```text
Vite production build
+
canonical Python service (depthwiz_service / backend_bridge)
+
native host boundary abstraction (HostCapabilities)
+
Electron native host (44.2.0) + NSIS installer
```

## What Exists

- `HostCapabilities` (`src/host/host.ts`): `runtime`/`processSpawning`/
  `localFilesystem` detection with overrides. Canonical — reused, not
  duplicated.
- `BackendBridge` / `SubprocessServiceTransport`: spawn the Python
  service scripts; interpreter order is explicit option →
  `DEPTHWIZARD_PYTHON` → `"python"`; backend passed explicitly, never
  substituted.
- Service entrypoints: `scripts/depthwiz_service.py` (control plane:
  `LocalService` → `PipelineRunner`, metadata only) and
  `scripts/backend_bridge.py` (payload plane: arrays/mesh). Both are
  canonical in their plane — not competitors.
- `scripts/runtime_check.py`: setup verification + runtime self-check
  (JSON, exit 0/1/2). Never downloads, installs, or phones home.
- `depthwizard.runtime` diagnostics: checkpoint resolution order
  explicit → `DW_DAV2_CKPT` → packaged data dir → repo-dev
  `checkpoints/` → `cwd/checkpoints/`; SHA-256 verification;
  import-discovery availability; upstream revision reporting.
- **Electron native host (44.2.0)** (`electron/main.ts`, `electron/preload.ts`)
- **Windows NSIS installer** (`electron-builder.yml`) — 115 MB installer, 334 MB portable
- **Windows release preflight** (`scripts/windows_release_preflight.ps1`)
- DA-V2 runtime (pinned `a561b84`) + external checkpoint policy
  (git-ignored, SHA-pinned).

## What Was Missing (Now Resolved)

| Item                             | Status       | Location                                      |
| -------------------------------- | ------------ | --------------------------------------------- |
| Native host executable           | ✅ RESOLVED  | `electron/main.ts` (Electron 44.2.0)          |
| Installer                        | ✅ RESOLVED  | `electron-builder.yml` (NSIS, 115 MB)         |
| Managed/embedded Python runtime  | ✅ RESOLVED  | `scripts/provision_runtime.py` (managed venv) |
| Packaged checkpoint distribution | ❌ BY DESIGN | External provision (`DW_DAV2_CKPT`)           |
| First-run setup automation       | ✅ PARTIAL   | `provision_runtime.py` + `runtime_check.py`   |

## Native-Framework Audit (Verified from package.json)

| Item                                                      | Status                                      |
| --------------------------------------------------------- | ------------------------------------------- |
| Electron / Tauri / Neutralino / native host               | ✅ Electron 44.2.0                          |
| Installer                                                 | ✅ NSIS via electron-builder 26.0.12        |
| Python bundling (PyInstaller/Nuitka/Briefcase/conda-pack) | ✅ Managed venv (selected strategy)         |
| Model bundling                                            | ❌ External by policy (checkpoint external) |
| `electron-to-chromium` in node_modules                    | Transitive only, not a host                 |

## Recommended Final Architecture

```text
Installed DepthWizard
        ↓
Native Host (Electron, Aryan-owned)
        ↓
Managed Python Runtime (venv, provisioned via S18)
        ↓
depthwiz_service (control) + backend_bridge (payload)
        ↓
LocalService
        ↓
PipelineRunner
        ↓
DepthAnythingV2Backend (checkpoint via DW_DAV2_CKPT)
```

## Python Runtime Strategy (Evaluated)

- **A — System Python**: rejected for production. Windows PATH
  unreliability already observed (`python` missing → error 9009);
  user environments irreproducible.
- **B — Managed virtual environment: SELECTED.** Provisioned once
  (network), then offline-capable; isolated; upgradable by
  re-provisioning; permissions are ordinary user-dir writes. Verified
  this task with fresh venvs (core install + 503 passing tests).
- **C — Embedded Python**: deferred. Viable later for a zero-dependency
  installer, but larger build/licensing surface; no evidence it is
  needed yet.
- **D — Standalone executable (PyInstaller/Nuitka)**: rejected for now.
  The stack (torch + rasterio native libs) is high-risk to freeze and
  would complicate checkpoint/data-dir layout; revisit only with
  measured need.

## Dependency Inventory

| Package                                 | Tier                                    |
| --------------------------------------- | --------------------------------------- |
| Python ≥ 3.11                           | core runtime                            |
| pydantic, Pillow, rasterio, numpy       | core runtime                            |
| torch, torchvision, opencv-python       | optional ML runtime (`dav2` extra only) |
| Depth Anything V2 source (pinned clone) | external runtime asset                  |
| `depth_anything_v2_vits.pth`            | external model asset (never committed)  |
| pytest, mypy, ruff, vitest tooling      | development only                        |

## Checkpoint Strategy

- File: `depth_anything_v2_vits.pth`, SHA-256
  `715fade13be8f229f8a70cc02066f656f2423a59effd0579197bbf57860e1378`
  (upstream revision `a561b84…` kept as a separate field).
- Packaged location: host data dir —
  `%APPDATA%/DepthWizard/checkpoints` (Windows),
  `~/Library/Application Support/DepthWizard` (macOS),
  `~/.local/share/depthwizard` (Linux) — override `DEPTHWIZARD_DATA`.
- Injection: host sets `DW_DAV2_CKPT` to the absolute packaged path
  (already the backend's first resolution rule; no developer paths).
- Verification: `runtime_check --checkpoint` / `--require-dav2`
  rejects hash mismatches; service registry stays synthetic-only
  without a verified asset.

## Provisioning (Verified)

```bash
python -m venv <runtime-dir>
<runtime-dir>/Scripts/python -m pip install -e ".[dav2]"   # or "." for core-only
# place upstream DA-V2 source on PYTHONPATH (pinned a561b84)
# place depth_anything_v2_vits.pth in the data dir (or set DW_DAV2_CKPT)
python scripts/runtime_check.py --require-dav2 --pretty
```

Observed: core provisioning → `ready: true`, `service_launch_ready: true`, `offline_ready: true`

## Runtime

After provisioning: fully offline (`HF_HUB_OFFLINE=1` verified; no
network imports in `src/depthwizard`). Cancellation: cooperative
in-process token + AbortSignal at the spawn boundary (existing).
Shutdown: synchronous scripts exit per request; no daemon state.
Logs/errors: stderr diagnostics + structured JSON errors with domain
codes (`unknown backend`, `CHECKPOINT_HASH_MISMATCH`,
`DEVICE_UNAVAILABLE`, …); never a bare "something went wrong".

## Security

No arbitrary shell execution (fixed argv); no executable paths from
untrusted input (interpreter from explicit option or host env only);
no URL downloads in runtime code (verified by test); checkpoints
hash-pinned; writes confined to caller-chosen outputs, temp staging,
and the data dir; reports use location labels, not absolute paths.

## Release Blockers (Explicit)

1. ~~Native host executable + installer (Aryan-owned).~~ → **RESOLVED** (PR #2)
2. Managed-venv provisioning automation in the installer → **RESOLVED** (S18 on main)
3. Checkpoint distribution channel (host-side; hash contract defined).
4. GPU/long-run evidence, field accuracy (science track).

Ownership: Shivam — runtime requirements, Python packaging,
service/bridge contract, dependencies, checkpoint policy,
reproducibility, this contract. Aryan — host implementation,
packaging frontend, installer UX, UI/rendering.
