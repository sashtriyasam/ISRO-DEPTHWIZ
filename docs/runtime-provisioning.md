# Runtime Provisioning

Host-invocable provisioning for the managed Python runtime. A future
native host only needs `provision → verify → launch` without knowing
anything about calibration, DSM, mesh, CRS, or model internals.

## Provisioning

```bash
# Core (non-ML application)
python scripts/provision_runtime.py --runtime-dir <dir> --mode core

# Full DA-V2 (needs network for pip/git/fetch; checkpoint stays local)
python scripts/provision_runtime.py --runtime-dir <dir> --mode dav2 \
    --checkpoint-src <verified-local-file>        # or --fetch-checkpoint
```

Output is one JSON status document (`ready`, per-step `ok`/`code`,
`core_ready`, `dav2_ready`, `service_launch_ready`, `offline_ready`);
location labels only, never absolute paths. Exit 0 = ready, 1 = not
ready, 2 = misuse. Re-running reuses valid state (venv, source,
checkpoint) and never replaces a verified checkpoint.

## Managed Python

A provisioned venv was selected over system Python (Windows PATH is
unreliable — observed error 9009), embedded interpreters (build cost
unjustified), and frozen executables (torch/rasterio freeze risk).
Layout: `<runtime>/Scripts/python.exe` (Windows),
`<runtime>/bin/python` (POSIX). No global mutation; user permissions.

## Runtime layout

```text
<runtime-dir>/            # isolated venv (python, pip packages)
<data-dir>/              # DEPTHWIZARD_DATA or OS default
  dav2-upstream/         # pinned git checkout (a561b849…)
  checkpoints/
    depth_anything_v2_vits.pth
```

OS defaults: `%APPDATA%/DepthWizard` (Windows),
`~/Library/Application Support/DepthWizard` (macOS),
`~/.local/share/depthwizard` (Linux).

## DA-V2 source

Fixed identity `DepthAnything/Depth-Anything-V2`, pinned revision
`a561b849ebae10a6f5ef49e26c83cbbcd36c71bf`. Provisioning clones (or
reuses), checks out the pin, and verifies remote identity + HEAD.
Present-but-wrong checkouts fail loudly instead of being replaced.

## Checkpoint

`depth_anything_v2_vits.pth`, SHA-256
`715fade13be8f229f8a70cc02066f656f2423a59effd0579197bbf57860e1378`.
Local sources are hash-verified before storage; `--fetch-checkpoint`
downloads only the fixed Hugging Face identity and discards mismatched
bytes. Mismatched stored files are quarantined (`.invalid`), never
trusted. The checkpoint is never committed to git.

## Offline execution

After provisioning, inference needs no network: verified with
`HF_HUB_OFFLINE=1` real inference, and a static test proves no
socket/HTTP/hub imports in the engine (provisioning-only fetch is the
single documented exception, fixed-identity only).

## Host integration

```text
provision_runtime.py --runtime-dir … --mode dav2 --checkpoint-src …
→ runtime_check.py --require-dav2        # verify
→ DEPTHWIZARD_PYTHON=<runtime>/Scripts/python.exe
→ DW_DAV2_CKPT=<data-dir>/checkpoints/depth_anything_v2_vits.pth
→ spawn depthwiz_service.py / backend_bridge.py   # launch
```

The host consumes `ready`, `dav2_ready`, step `code`s, and
`available_backends`; scientific internals stay behind the service.

## Security

Fixed repository/package/checkpoint identities only; argv-list
subprocess calls (no shell); hash-before-trust checkpoints; writes
confined to runtime/data/temp/caller outputs; no global Python
changes; no downloads at import or test time.

## Failure modes

`PYTHON_VERSION_UNSUPPORTED`, `PYTHON_NOT_FOUND`, `VENV_CREATION_FAILED`,
`PIP_INSTALL_FAILED`, `UPSTREAM_CLONE_FAILED`,
`UPSTREAM_REPOSITORY_MISMATCH`, `UPSTREAM_REVISION_MISMATCH`,
`CHECKPOINT_MISSING`, `CHECKPOINT_HASH_MISMATCH`,
`CHECKPOINT_FETCH_FAILED`, `DEVICE_UNAVAILABLE`,
`PROVISION_INVALID_RUNTIME_DIR`, `PROVISION_PERMISSION_DENIED`,
`PROVISION_RUNTIME_DIR_CONFLICT`. Unknown backends remain loudly
rejected — never synthetic substitution.

## Ownership

Shivam owns provisioning logic, dependency requirements, checkpoint
and source verification, self-checks, and this contract. Aryan owns
installer UI, native host, and first-run UX built on top of it.
