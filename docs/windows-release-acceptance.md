# Windows Release Acceptance Procedure

**DepthWizard — SIH 26175**  
**Target Release:** v0.1.0-sih-26175-rc1  
**Document Version:** 1.0  
**Date:** 2026-09-06

---

## Purpose

This document defines the exact human acceptance procedure for the Windows release of DepthWizard. It must be executed on a **clean Windows machine/VM** with display + checkpoint to validate the complete installed application workflow.

**Do not claim these tests are complete from the existence of this document.** A human witness must physically execute each step and record PASS/FAIL.

---

## Prerequisites

### A. Clean Windows Machine/VM

- Windows 10/11 (build 19041+)
- Clean install — no prior DepthWizard, no Python, no DA-V2 checkpoint
- Display attached (required for renderer validation)
- Administrator privileges for installation

### B. Installer Artifact

- **File:** `DepthWizard Setup 0.1.0.exe`
- **SHA-256:** `2606648234c275dbf41797f5f881b02521f0295d16947c80e501e569c93f0311`
- **Size:** 115,174,663 bytes
- **Source:** `release/DepthWizard Setup 0.1.0.exe` from `npm run electron:build:win`

### C. Checkpoint File

- **File:** `depth_anything_v2_vits.pth`
- **SHA-256:** `715fade13be8f229f8a70cc02066f656f2423a59effd0579197bbf57860e1378`
- **Location:** Place at `%APPDATA%\DepthWizard\checkpoints\depth_anything_v2_vits.pth`

### D. DA-V2 Upstream Source (for DA-V2 mode)

- Pinned revision: `a561b849ebae10a6f5ef49e26c83cbbcd36c71bf`
- Repository: `https://github.com/DepthAnything/Depth-Anything-V2`
- Must be available on PYTHONPATH (cloned by provisioning or manually)

---

## Acceptance Procedure

### Phase 1: Baseline Verification

| Step | Action                                                                                              | Expected                              | PASS/FAIL |
| ---- | --------------------------------------------------------------------------------------------------- | ------------------------------------- | --------- |
| 1.1  | Verify installer SHA-256 matches `2606648234c275dbf41797f5f881b02521f0295d16947c80e501e569c93f0311` | Match                                 |           |
| 1.2  | Verify no prior DepthWizard installation                                                            | Clean                                 |           |
| 1.3  | Verify no Python on PATH                                                                            | `python --version` fails or not 3.10+ |           |
| 1.4  | Verify no checkpoint at `%APPDATA%\DepthWizard\checkpoints\`                                        | Empty/missing                         |           |

---

### Phase 2: Installation

| Step | Action                                             | Expected                                                                               | PASS/FAIL |
| ---- | -------------------------------------------------- | -------------------------------------------------------------------------------------- | --------- |
| 2.1  | Run `DepthWizard Setup 0.1.0.exe`                  | Installer launches, NSIS UI appears                                                    |           |
| 2.2  | Accept license, choose install directory (default) | Proceeds without error                                                                 |           |
| 2.3  | Complete installation                              | Exit code 0, shortcuts created                                                         |           |
| 2.3  | Verify installation directory contents             | `DepthWizard.exe`, `resources/app.asar`, `resources/scripts/`, `resources/elevate.exe` |           |

---

### Phase 3: First Launch — Python Missing

| Step | Action                                                | Expected                                                                                                       | PASS/FAIL |
| ---- | ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | --------- |
| 3.1  | Launch DepthWizard from Start Menu / Desktop shortcut | Application window opens                                                                                       |           |
| 3.2  | Observe renderer loads                                | React UI visible, no console errors                                                                            |           |
| 3.3  | Attempt to load an image (any PNG/JPG)                | File picker works                                                                                              |           |
| 3.4  | Click "Process" (or equivalent action)                | **Error dialog**: "Python not found. Install Python 3.10+ and ensure it is on PATH, or set DEPTHWIZARD_PYTHON" |           |
| 3.4  | Verify no crash, graceful degradation                 | App remains responsive                                                                                         |           |

---

### Phase 4: Python Installation & Runtime Detection

| Step | Action                                             | Expected                                                                                      | PASS/FAIL |
| ---- | -------------------------------------------------- | --------------------------------------------------------------------------------------------- | --------- |
| 4.1  | Install Python 3.10+ from python.org (Add to PATH) | `python --version` shows 3.10+                                                                |           |
| 4.2  | Restart DepthWizard                                | App launches                                                                                  |           |
| 4.3  | Verify `DEPTHWIZARD_PYTHON` resolution             | Settings/Logs show resolved Python path                                                       |           |
| 4.4  | Attempt processing without checkpoint              | **Error**: "depth-anything-v2-small not available (checkpoint missing)" — NOT silent fallback |           |

---

### Phase 5: Runtime Check & Provisioning

| Step | Action                                                                                                     | Expected                                                                               | PASS/FAIL |
| ---- | ---------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | --------- |
| 5.1  | Open terminal in install directory                                                                         | `scripts/runtime_check.py` accessible                                                  |           |
| 5.2  | Run `python scripts/runtime_check.py --pretty`                                                             | `core_ready: true`, `checkpoint_location: "absent"`, `dav2_ready: false`               |           |
| 5.2  | Run `python scripts/provision_runtime.py --mode core --runtime-dir %APPDATA%\DepthWizard\runtime --pretty` | `ready: true`, `core_ready: true`, `service_launch_ready: true`, `offline_ready: true` |           |
| 5.3  | Re-run provisioning (idempotent)                                                                           | `venv.reused: true`                                                                    |           |
| 5.3  | Run `python scripts/runtime_check.py --pretty` again                                                       | `core_ready: true`, `service_launch_ready: true`, `offline_ready: true`                |           |

---

### Phase 6: Service Launch & Backend Capability Discovery

| Step | Action                                                   | Expected                                                                              | PASS/FAIL |
| ---- | -------------------------------------------------------- | ------------------------------------------------------------------------------------- | --------- |
| 6.1  | Launch DepthWizard                                       | App opens                                                                             |           |
| 6.2  | Load a test PNG/JPG image                                | Image loads in viewer                                                                 |           |
| 6.3  | Select "synthetic-depth" backend (if UI allows)          | Backend selection works                                                               |           |
| 6.4  | Execute processing                                       | **Success**: Relative depth mesh generated, `available_backends: ["synthetic-depth"]` |           |
| 6.4  | Verify no synthetic fallback when real backend requested | If DA-V2 selected without assets → explicit error, NOT synthetic                      |           |
| 6.5  | Verify renderer displays mesh                            | Three.js scene renders mesh                                                           |           |
| 6.6  | Verify height exaggeration slider works (display-only)   | Mesh visual changes, scientific data unchanged                                        |           |

---

### Phase 7: Real DA-V2 Selection (Requires Checkpoint)

| Step | Action                                                                             | Expected                                                                               | PASS/FAIL |
| ---- | ---------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | --------- |
| 7.1  | Place checkpoint at `%APPDATA%\DepthWizard\checkpoints\depth_anything_v2_vits.pth` | File exists, SHA-256 verified                                                          |           |
| 7.2  | Ensure DA-V2 upstream source available on PYTHONPATH                               | `git -C <source> rev-parse HEAD` = `a561b849...`                                       |           |
| 7.3  | Run `python scripts/runtime_check.py --require-dav2 --pretty`                      | `dav2_ready: true`, `dav2_source_revision: "a561b84..."`, `checkpoint.sha_match: true` |           |
| 7.4  | Restart DepthWizard, select "depth-anything-v2-small" backend                      | Backend appears in capabilities                                                        |           |
| 7.5  | Execute processing with DA-V2                                                      | **Success**: Real relative depth inference executes                                    |           |
| 7.6  | Verify output is RELATIVE (`units=None`)                                           | UI/metadata shows relative semantics                                                   |           |
| 7.7  | Verify deterministic output (re-run same image)                                    | Identical output                                                                       |           |

---

### Phase 8: Checkpoint SHA-256 Verification

| Step | Action                                                                                                                   | Expected                                           | PASS/FAIL |
| ---- | ------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------- | --------- |
| 8.1  | Run `python scripts/runtime_check.py --checkpoint %APPDATA%\DepthWizard\checkpoints\depth_anything_v2_vits.pth --pretty` | `explicit_checkpoint.ok: true`, `code: "OK"`       |           |
| 8.2  | Corrupt checkpoint (flip one byte)                                                                                       | `CHECKPOINT_HASH_MISMATCH`, backend not registered |           |
| 8.3  | Remove checkpoint                                                                                                        | `CHECKPOINT_MISSING`, DA-V2 not registered         |           |
| 8.3  | Verify no silent fallback                                                                                                | Explicit DA-V2 request → error, NOT synthetic      |           |

---

### Phase 9: Metric Calibration Path (Requires GeoTIFF + GCP/DEM)

| Step | Action                                                 | Expected                                           | PASS/FAIL |
| ---- | ------------------------------------------------------ | -------------------------------------------------- | --------- |
| 9.1  | Prepare GeoTIFF with CRS/transform + GCP/DEM reference | Valid GeoTIFF                                      |           |
| 9.2  | Run with calibration target `height_agl_ndsm`          | Calibration executes, `CalibrationResult` produced |           |
| 9.3  | Verify `ScientificHeightProduct` has `units="meters"`  | Metric semantics                                   |           |
| 9.3  | Verify `DSMGrid` has `units="meters"`, `nodata=NaN`    | Metric DSM                                         |           |
| 9.3  | Verify `TerrainMesh` has CRS + `units="meters"`        | Metric mesh                                        |           |

---

### Phase 10: DSM & Mesh Generation

| Step | Action                               | Expected                           | PASS/FAIL |
| ---- | ------------------------------------ | ---------------------------------- | --------- |
| 10.1 | Verify DSM export (GeoTIFF)          | Valid GeoTIFF with CRS/transform   |           |
| 10.2 | Verify mesh export (if applicable)   | Valid mesh format                  |           |
| 10.3 | Verify renderer displays metric mesh | Three.js renders with metric scale |           |

---

### Phase 11: Renderer Display

| Step | Action                                            | Expected                                           | PASS/FAIL |
| ---- | ------------------------------------------------- | -------------------------------------------------- | --------- |
| 11.1 | Navigate 3D view (orbit, pan, zoom)               | Smooth interaction                                 |           |
| 11.2 | Toggle height exaggeration                        | Visual changes, scientific data unchanged          |           |
| 11.3 | Toggle measurement tools                          | Measurements in correct units (relative vs metric) |           |
| 11.4 | Toggle flythrough mode                            | Camera follows trajectory                          |           |
| 11.4 | Toggle rendering modes (wireframe, solid, points) | All modes render                                   |           |

---

### Phase 12: Shutdown & Cleanup

| Step | Action                                         | Expected                        | PASS/FAIL |
| ---- | ---------------------------------------------- | ------------------------------- | --------- |
| 12.1 | Close DepthWizard via window close             | Clean exit, no orphan processes |           |
| 12.2 | Verify `Get-Process python` returns empty      | No orphan Python                |           |
| 12.2 | Verify `Get-Process DepthWizard` returns empty | No orphan app                   |           |

---

### Phase 13: Offline Execution

| Step | Action                                           | Expected                             | PASS/FAIL |
| ---- | ------------------------------------------------ | ------------------------------------ | --------- |
| 13.1 | Disable network (airplane mode / disconnect)     | Network disabled                     |           |
| 13.2 | Launch DepthWizard, run with provisioned runtime | App launches, processing works       |           |
| 13.2 | Set `HF_HUB_OFFLINE=1` and run DA-V2 inference   | Inference executes, no network calls |           |
| 13.3 | Re-enable network                                | Network restored                     |           |

---

### Phase 14: Uninstall / Reinstall / Reinstall

| Step | Action                                         | Expected                           | PASS/FAIL |
| ---- | ---------------------------------------------- | ---------------------------------- | --------- |
| 14.1 | Uninstall via Windows Settings / Control Panel | Clean removal, shortcuts removed   |           |
| 14.2 | Verify `%APPDATA%\DepthWizard\` preserved      | Checkpoint, logs, config remain    |           |
| 14.2 | Reinstall                                      | Clean install, shortcuts recreated |           |
| 14.3 | Launch, verify previous checkpoint detected    | App works, checkpoint detected     |           |
| 14.3 | Uninstall again                                | Clean removal                      |           |

---

### Phase 15: Missing Checkpoint / Runtime Failure Modes

| Step | Action                              | Expected                                                | PASS/FAIL |
| ---- | ----------------------------------- | ------------------------------------------------------- | --------- |
| 15.1 | Remove checkpoint, request DA-V2    | Explicit error: "depth-anything-v2-small not available" |           |
| 15.2 | Verify NO synthetic fallback        | No silent substitution                                  |           |
| 15.2 | Remove Python from PATH, launch app | Clear error: "Python not found..."                      |           |
| 15.3 | Request unknown backend             | Explicit error: "unknown backend"                       |           |
| 15.3 | Verify NO silent fallback           | Never synthetic substitution                            |           |

---

### Phase 16: Spaces Path Install

| Step | Action                                                               | Expected          | PASS/FAIL |
| ---- | -------------------------------------------------------------------- | ----------------- | --------- |
| 16.1 | Install to path with spaces (e.g., `C:\Program Files\Depth Wizard\`) | Install succeeds  |           |
| 16.2 | Launch, verify all functionality                                     | All features work |           |

---

## Summary Table

| Category                | Total Tests | PASS | FAIL | NOT TESTED |
| ----------------------- | ----------- | ---- | ---- | ---------- |
| Installation            | 4           |      |      |            |
| Python/Runtime          | 8           |      |      |            |
| Service/Backend         | 10          |      |      |            |
| DA-V2 Real Inference    | 7           |      |      |            |
| Checkpoint Verification | 4           |      |      |            |
| Metric Path             | 4           |      |      |            |
| DSM/Mesh                | 3           |      |      |            |
| Renderer                | 5           |      |      |            |
| Shutdown                | 2           |      |      |            |
| Offline                 | 3           |      |      |            |
| Uninstall/Reinstall     | 4           |      |      |            |
| Failure Modes           | 5           |      |      |            |
| Spaces Path             | 2           |      |      |            |
| **TOTAL**               | **65**      |      |      |            |

---

## Witness Sign-off

| Role                           | Name | Signature | Date |
| ------------------------------ | ---- | --------- | ---- |
| **Aryan (Release Engineer)**   |      |           |      |
| **Shivam (Release Authority)** |      |           |      |

---

## Evidence Collection

For each PASS/FAIL, record:

- Screenshot or screen recording
- Console/log output
- File SHA-256 where applicable
- Timing measurements where relevant

---

**End of Acceptance Procedure.** This document defines the complete acceptance criteria. Do not mark any test complete without physical execution and evidence.
