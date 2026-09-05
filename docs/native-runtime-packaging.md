# Native Runtime Packaging Contract

## Current state

```text
Vite production build
+
canonical Python service (depthwiz_service / backend_bridge)
+
native host boundary abstraction (HostCapabilities)
```

## What exists

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
- DA-V2 runtime (pinned `a561b84`) + external checkpoint policy
  (git-ignored, SHA-pinned).

## What is missing

- Native host executable (no Electron/Tauri/Neutralino in dependencies).
- Installer of any kind.
- Managed/embedded Python runtime (strategy selected below, not yet built).
- Packaged checkpoint distribution (location contract defined below).
- First-run setup automation beyond `runtime_check` reporting.

## Native-framework audit (verified from package.json)

| Item                                                      | Status                                 |
| --------------------------------------------------------- | -------------------------------------- |
| Electron / Tauri / Neutralino / native host               | absent (no dependency, no executable)  |
| Installer                                                 | absent                                 |
| Python bundling (PyInstaller/Nuitka/Briefcase/conda-pack) | absent                                 |
| Model bundling                                            | absent (checkpoint external by policy) |
| `electron-to-chromium` in node_modules                    | transitive only, not a host            |

## Recommended final architecture

```text
Installed DepthWizard
        ↓
Native Host (Aryan-owned implementation)
        ↓
Managed Python Runtime (venv, provisioned; §strategy)
        ↓
depthwiz_service (control) + backend_bridge (payload)
        ↓
LocalService
        ↓
PipelineRunner
        ↓
DepthAnythingV2Backend (checkpoint via DW_DAV2_CKPT)
```

## Python runtime strategy (evaluated)

- **A — System Python**: rejected for production. Windows PATH
  unreliability already observed (`python` missing → error 9009);
  user environments irreproducible.
- **B — Managed virtual environment: SELECTED.** Provisioned once
  (network), then offline-capable; isolated; upgradable by
  re-provisioning; permissions are ordinary user-dir writes. Verified
  this task with two fresh venvs (full `[dav2]` install; core-only
  install + 114 passing tests).
- **C — Embedded Python**: deferred. Viable later for a zero-dependency
  installer, but larger build/licensing surface; no evidence it is
  needed yet.
- **D — Standalone executable (PyInstaller/Nuitka)**: rejected for now.
  The stack (torch + rasterio native libs) is high-risk to freeze and
  would complicate checkpoint/data-dir layout; revisit only with
  measured need.

## Dependency inventory

| Package                                 | Tier                                    |
| --------------------------------------- | --------------------------------------- |
| Python ≥ 3.11                           | core runtime                            |
| pydantic, Pillow, rasterio, numpy       | core runtime                            |
| torch, torchvision, opencv-python       | optional ML runtime (`dav2` extra only) |
| Depth Anything V2 source (pinned clone) | external runtime asset                  |
| `depth_anything_v2_vits.pth`            | external model asset (never committed)  |
| pytest, mypy, ruff, vitest tooling      | development only                        |

## Checkpoint strategy

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

## Provisioning (verified this task)

```bash
python -m venv <runtime-dir>
<runtime-dir>/Scripts/python -m pip install -e ".[dav2]"   # or "." for core-only
# place upstream DA-V2 source on PYTHONPATH (pinned a561b84)
# place depth_anything_v2_vits.pth in the data dir (or set DW_DAV2_CKPT)
python scripts/runtime_check.py --require-dav2 --pretty
```

Observed: cold model load ≈ 5–9 s, 64×64 inference ≈ 0.9–1.5 s CPU
(engineering observations, not benchmarks).

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

## Release blockers (explicit)

1. Native host executable + installer (Aryan-owned).
2. Managed-venv provisioning automation in the installer (Shivam
   contract defined here; host-side implementation pending).
3. Checkpoint distribution channel (host-side; hash contract defined).
4. GPU/long-run evidence, field accuracy (science track).

Ownership: Shivam — runtime requirements, Python packaging,
service/bridge contract, dependencies, checkpoint policy,
reproducibility, this contract. Aryan — host implementation,
packaging frontend, installer UX, UI/rendering.
