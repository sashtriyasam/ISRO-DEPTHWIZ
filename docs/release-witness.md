# DepthWizard — Release Witness

Generated: 2026-09-05 | Phase 6

## Purpose

This document provides a reproducible operator guide for validating the
remaining physical Windows release blockers. It allows the release owner
(or any operator) to complete acceptance without Aryan's direct involvement.

**Product**: DepthWizard — Python-prerequisite Windows desktop
**Branch**: `feat/aryan-native-host-installer`
**HEAD**: `cbe3144`

---

## Prerequisites (Operator Machine)

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| Windows | 10/11 x64 | Clean VM or physical machine preferred |
| Python | 3.10+ | Must be on PATH or set `DEPTHWIZARD_PYTHON` |
| torch | 2.x | CPU or CUDA |
| depthwizard | 0.1.0 | `pip install -e .` from source, or installed package |
| Checkpoint | `depth_anything_v2_vits.pth` | ~99 MB, placed manually |
| Display | Non-headless | For Three.js visual validation |

---

## 1. Run Preflight

```powershell
cd <repository-root>
.\scripts\windows_release_preflight.ps1
```

Expected: All checks PASS. DA-V2 capability PASS only if checkpoint is valid.

Record results in Section A below.

---

## 2. Run Service Capabilities Check

```powershell
echo '{"capabilities": true}' | python scripts\depthwiz_service.py
```

Expected output contains:
- `"available_backends": ["synthetic-depth"]` if no checkpoint
- `"available_backends": ["depth-anything-v2-small", "synthetic-depth"]` if checkpoint valid

Record in Section B.

---

## 3. Run Real DA-V2 Inference (CLI Smoke)

If you have a test image (PNG/JPG) and valid checkpoint:

```powershell
echo '{"request": {"backend": "depth-anything-v2-small", "input_path": "C:\path\to\test.png", "target_semantics": "height_agl_ndsm"}}' | python scripts\depthwiz_service.py
```

Expected:
- `"success": true` (if image is valid)
- `"backend_name": "depth-anything-v2-small"`
- `"depth_scale": "relative"` (raw output is relative, NOT metric)
- `"is_metric": false`
- `"units": null`

Record in Section C.

---

## 4. Visual Acceptance (Manual)

### Procedure

1. Launch installed DepthWizard (or `npm run electron:dev` from source).
2. Confirm host = "Desktop host (Electron)" in the UI.
3. Confirm DA-V2 capability appears (if checkpoint valid).
4. Select `depth-anything-v2-small` as backend.
5. Load a real RGB image (PNG/JPG) or GeoTIFF.
6. Click Generate / Run.
7. Wait for successful result (no error dialog).
8. Inspect metadata panel — confirm backend name, depth scale, units.
9. Toggle rendering modes: shaded → wireframe → combined.
10. Change height exaggeration: 1x → 2x → 5x → 10x → 1x.
    - Visual height must change.
    - Metadata values must NOT change.
11. Orbit the terrain (mouse drag).
12. Enter first-person mode.
13. Enter aerial mode.
14. Start flythrough — confirm waypoint route renders.
15. Click a point on terrain — confirm point inspection shows values.
16. Use measurement tool — confirm metric measurement works.
17. Generate elevation profile — confirm chart renders.
18. Reset workspace — confirm session clears.

### Evidence

For each step, record PASS/FAIL with screenshot or description.

Record in Section D.

---

## 5. Scientific Semantic Witness

**CRITICAL**: The raw DA-V2 model output is:
- `DepthScale.RELATIVE`
- `is_metric = false`
- `units = null`
- `ElevationSemantics.RELATIVE_DEPTH`

**ONLY after authoritative calibration** does output become metric.

The operator must NOT claim metres from raw DA-V2 output.

Record actual observed semantics in Section E.

---

## 6. Clean Windows Installation

### Before

- No previous DepthWizard installation
- No source checkout (use the NSIS installer only)
- Python prerequisite installed per product policy
- No old DepthWizard processes
- Checkpoint state documented

### Install

1. Run `DepthWizard Setup 0.1.0.exe`.
2. Choose custom install directory with spaces:
   Example: `C:\Program Files\DepthWizard Acceptance\`
3. Complete installation.
4. Verify desktop shortcut created.
5. Verify start menu shortcut created.

### Launch

6. Double-click desktop shortcut.
7. Wait for application window to appear.
8. Confirm host = Electron.

### After

9. Check `%APPDATA%\DepthWizard\` directory exists.
10. Run preflight script from installed location (if possible).

Record in Section F.

---

## 7. Relaunch

1. Close the application.
2. Wait 5 seconds.
3. Check for orphan processes:
   ```powershell
   Get-Process python -ErrorAction SilentlyContinue
   Get-Process DepthWizard -ErrorAction SilentlyContinue
   ```
   Expected: No output (no orphan processes).
4. Relaunch from shortcut.
5. Confirm application opens.
6. Confirm no corrupted state.

Record in Section G.

---

## 8. Uninstall

1. Run Windows "Add or Remove Programs".
2. Select DepthWizard → Uninstall.
3. Confirm uninstaller runs.
4. Check installation directory removed.
5. Check desktop shortcut removed.
6. Check start menu shortcut removed.
7. Check `%APPDATA%\DepthWizard\` — should still exist (checkpoint preserved).

Record in Section H.

---

## 9. Reinstall

1. Run `DepthWizard Setup 0.1.0.exe` again.
2. Install to same (or different) path.
3. Launch.
4. Confirm retained user data (checkpoint still detected).

Record in Section I.

---

## 10. Spaces-in-Path Test

With installation in a path containing spaces:

1. Launch the application.
2. Load an input file whose path contains spaces.
3. Run real DA-V2 inference.
4. Confirm no shell quoting errors.
5. Confirm process starts and backend runs.

Record in Section J.

---

## 11. Offline DA-V2 Test

After prerequisites and checkpoint are prepared:

```powershell
$env:HF_HUB_OFFLINE = "1"
echo '{"request": {"backend": "depth-anything-v2-small", "input_path": "C:\path\to\test.png", "target_semantics": "height_agl_ndsm"}}' | python scripts\depthwiz_service.py
Remove-Item Env:\HF_HUB_OFFLINE
```

Expected: Real inference succeeds without network.

If it fails, capture:
- Exact error message
- Process exit code
- Stage at which failure occurred
- Whether failure is host, backend, dependency, or model related

Record in Section K.

---

## 12. Orphan Process Validation

After each of the following, run:
```powershell
Get-Process python -ErrorAction SilentlyContinue
Get-Process DepthWizard -ErrorAction SilentlyContinue
```

| Scenario | Expected |
|----------|----------|
| Normal close | No orphan |
| Cancel during inference | No orphan |
| Backend failure | No orphan |
| Window close during inference | No orphan |
| Application quit during inference | No orphan |

Record in Section L.

---

## 13. Security Witness

From the installed application:

1. Attempt to navigate to an external URL — should be blocked.
2. Attempt to open a new window — should be denied.
3. Verify no popup or new browser window appears.
4. Verify no shell prompt or command execution occurs.
5. Verify no file dialog appears without user action.

Record in Section M.

---

## 14. Package Content Witness

Inspect `release/win-unpacked/` or installed directory:

**Expected present:**
- `DepthWizard.exe`
- `resources/app.asar`
- `resources/scripts/depthwiz_service.py`
- `resources/scripts/backend_bridge.py`

**Expected absent:**
- `.git/`
- `node_modules/`
- `src/`
- `.venv/`
- `*.pth` (checkpoint)
- credentials, logs, screenshots

Record in Section N.

---

## Evidence Sections

### Section A: Preflight Results

| Check | Status | Detail |
|-------|--------|--------|
| OS | | |
| Python Executable | | |
| Python Version | | |
| Checkpoint | | |
| DA-V2 Capability | | |
| Service Capabilities | | |

### Section B: Service Capabilities

```
(paste JSON output here)
```

### Section C: Real DA-V2 Inference (CLI)

```
(paste JSON output here)
```

Observed:
- Backend: 
- Depth scale: 
- Is metric: 
- Units: 

### Section D: Visual Acceptance

| Step | Action | PASS/FAIL | Notes |
|------|--------|-----------|-------|
| 1 | Launch app | | |
| 2 | Confirm Electron host | | |
| 3 | Confirm DA-V2 capability | | |
| 4 | Select DA-V2 backend | | |
| 5 | Load RGB image | | |
| 6 | Generate terrain | | |
| 7 | Wait for result | | |
| 8 | Inspect metadata | | |
| 9 | Toggle rendering modes | | |
| 10 | Height exaggeration 1x→10x→1x | | |
| 11 | Orbit | | |
| 12 | First-person | | |
| 13 | Aerial | | |
| 14 | Flythrough | | |
| 15 | Point inspection | | |
| 16 | Measurement | | |
| 17 | Elevation profile | | |
| 18 | Session reset | | |

### Section E: Scientific Semantics

| Field | Raw DA-V2 | After Calibration |
|-------|-----------|-------------------|
| Depth scale | | |
| Is metric | | |
| Units | | |
| Elevation semantics | | |

### Section F: Clean Installation

| Check | PASS/FAIL | Detail |
|-------|-----------|--------|
| Installer starts | | |
| Custom path works | | |
| Shortcuts created | | |
| App launches | | |
| App data directory created | | |
| Runtime detected | | |
| Checkpoint detected | | |

### Section G: Relaunch

| Check | PASS/FAIL | Detail |
|-------|-----------|--------|
| App closes cleanly | | |
| No orphan processes | | |
| Relaunch succeeds | | |
| No corrupted state | | |

### Section H: Uninstall

| Check | PASS/FAIL | Detail |
|-------|-----------|--------|
| Uninstaller runs | | |
| Install dir removed | | |
| Shortcuts removed | | |
| App data preserved | | |
| Checkpoint preserved | | |

### Section I: Reinstall

| Check | PASS/FAIL | Detail |
|-------|-----------|--------|
| Reinstall succeeds | | |
| App launches | | |
| Retained data works | | |
| Checkpoint detected | | |

### Section J: Spaces-in-Path

| Check | PASS/FAIL | Detail |
|-------|-----------|--------|
| Install path with spaces | | |
| Input path with spaces | | |
| No shell quoting errors | | |
| Backend runs | | |

### Section K: Offline DA-V2

| Check | PASS/FAIL | Detail |
|-------|-----------|--------|
| HF_HUB_OFFLINE=1 set | | |
| Real inference succeeds | | |
| No network dependency | | |

### Section L: Orphan Processes

| Scenario | PASS/FAIL | Process output |
|----------|-----------|----------------|
| Normal close | | |
| Cancel inference | | |
| Backend failure | | |
| Window close during inference | | |
| App quit during inference | | |

### Section M: Security

| Check | PASS/FAIL | Detail |
|-------|-----------|--------|
| External nav blocked | | |
| New window denied | | |
| No unexpected popups | | |
| No shell exposure | | |
| No renderer Node APIs | | |

### Section N: Package Contents

| Check | PASS/FAIL | Detail |
|-------|-----------|--------|
| DepthWizard.exe present | | |
| app.asar present | | |
| Python scripts present | | |
| No .git | | |
| No node_modules | | |
| No src | | |
| No checkpoint | | |

---

## Release Evidence Summary

Complete this after all sections:

```
Machine:
Windows version:
CPU:
GPU:
RAM:
Python:
Torch:
DepthWizard:
Electron:

Checkpoint:
Checkpoint SHA:

Input:
Input format:
Input dimensions:

Backend:
Model:
Model version:
Checkpoint identity:

Raw depth semantics:
Units:

Calibration:
DSM:
Mesh:
SceneArtifact:

Visual validation:
Flythrough:
Measurements:
Profile:
Metadata:
Offline inference:
Installer:
Uninstall:
Spaces-path:
Orphan-process check:

Release Candidate:
Aryan Freeze:
```
