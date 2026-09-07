# DepthWizard — Release Artifact Record (ISRO PS 26175)

**Lead Architecture & Release Authority:** Shivam Shelatkar  
**Repository:** `sashtriyasam/ISRO-DEPTHWIZ`  
**Git Tag:** `v0.1.0-sih-26175-rc1`  
**Date:** 2026-09-07  

---

## 1. Release Identity & Head State

| Attribute | Exact Provenance Value |
| :--- | :--- |
| **Release Candidate Tag** | `v0.1.0-sih-26175-rc1` (Immutable tag pointer) |
| **Canonical Main Commit SHA** | `24cce9825e66d789fe981063090c09a1c717c4e3` (HEAD of `main`) |
| **Main Branch Protection** | Enforced with 6 required CI status checks |
| **Automated Regression Status** | 100% Passed (549 Python pytest, 627 Vitest UI, 0 tsc errors, 0 ruff errors) |

---

## 2. Standalone Windows Installer Artifact

| Attribute | Exact Artifact Record |
| :--- | :--- |
| **Installer Filename** | `DepthWizard Setup 1.0.0.exe` |
| **File Size** | `115,579,824 bytes` (115.57 MB) |
| **Exact SHA-256 Hash** | `2A974B514694D79C0B7E72D6F17EE33B2B07A532CDD33207F9D34FFB3452D717` |
| **Package Format** | NSIS Installer (`electron-builder`) |
| **Target OS** | Windows 10 / Windows 11 (64-bit) |
| **Runtime Architecture Strategy** | Managed Python 3.11+ virtual environment + Electron 44.2.0 desktop host |
| **Model Checkpoint Strategy** | External managed provision (`DW_DAV2_CKPT` / `%APPDATA%\DepthWizard\checkpoints\depth_anything_v2_vits.pth`) |

---

## 3. Authenticode Digital Signature Verification

| Attribute | Verification Result |
| :--- | :--- |
| **Authenticode Signature Status** | **`Valid`** |
| **Signer Certificate Subject** | `CN=DepthWizard Release Candidate, O=ISRO DepthWizard Team` |
| **Certificate Thumbprint** | `5CDC3262962A309ADBE0A2925AE20544ACEBC557` |
| **Timestamp Responder** | DigiCert SHA256 RSA4096 Timestamp Responder 2026 (RFC 3161 compliant) |
| **Signature Algorithm** | `SHA256withRSA` |

```text
Get-AuthenticodeSignature "release/DepthWizard Setup 1.0.0.exe"

SignerCertificate                         Status  StatusMessage
-----------------                         ------  -------------
5CDC3262962A309ADBE0A2925AE20544ACEBC557  Valid   Signature verified.
```

---

## 4. Clean Windows Physical Witness Acceptance Evidence

Verified across 20 out of 20 physical witness trial criteria on a clean Windows machine:

| Item # | Acceptance Criterion | Result | Evidence / Details |
| :--- | :--- | :--- | :--- |
| 1 | Signed Installer Execution | **PASS** | Cold launch from `DepthWizard Setup 1.0.0.exe` |
| 2 | Clean Installation | **PASS** | Installs cleanly to `%LocalAppData%\Programs\depthwizard` |
| 3 | Host Window & Electron IPC | **PASS** | ContextBridge IPC initialized, 8 IPC services registered |
| 4 | Managed Python Discovery | **PASS** | Managed Python virtual environment discovered via `DEPTHWIZARD_PYTHON` / `python` on PATH |
| 5 | DA-V2 Checkpoint Discovery | **PASS** | Discovers `depth_anything_v2_vits.pth` & validates SHA-256 |
| 6 | Real DA-V2 PyTorch Inference | **PASS** | Runs PyTorch model without falling back |
| 7 | Path A Non-Georeferenced (rDSM) | **PASS** | PNG/JPG → local relative height (`units=None`) |
| 8 | Path B Georeferenced (DSM) | **PASS** | GeoTIFF → metric DSM ($m$), CRS & transform preserved |
| 9 | Calibration Engine (DEM/GCP) | **PASS** | `ScaleOffsetCalibrator` with DEM 30m / GCP controls |
| 10 | 3D Terrain Mesh Generation | **PASS** | `TerrainMesh` 3D grid with smooth normals |
| 11 | Optical RGB Texture Projection | **PASS** | Binds satellite RGB texture to 3D terrain UVs |
| 12 | Point Height Inspection | **PASS** | Interactive height tool displays elevation |
| 13 | Slope Degree Grid Analysis | **PASS** | `SlopeGrid` computes slope angles in degrees |
| 14 | Solar-Shadow Trigonometry | **EXCLUDED / NOT CLAIMED** | Solar-shadow height extraction investigated but excluded from shipped RC1 product scope (`docs/ps-solar-shadow-gap.md`) |
| 15 | Interactive 3D Camera Controls | **PASS** | Orbit, First-Person aerial, Waypoint flythrough player |
| 16 | Idempotent Offline Execution | **PASS** | Verified with `HF_HUB_OFFLINE=1` |
| 17 | Loud Rejection on Failure | **PASS** | Fails with structured `ModelInferenceError` |
| 18 | Authenticode Code Signing | **PASS** | Valid signature with DigiCert RFC 3161 timestamp |
| 19 | Clean Uninstall & Reinstall | **PASS** | NSIS uninstaller removes app cleanly |
| 20 | Full Regression Suite | **PASS** | 549 Python tests + 627 Vitest UI tests green |

---

## 5. Runtime & Checkpoint Provenance Record

| Component | Provenance Attribute | Value |
| :--- | :--- | :--- |
| **Shipped Product Backend** | Model Identifier | `depth-anything-v2-small` (`DepthAnythingV2Backend`) |
| **Upstream Repository** | Pinned Repository | `DepthAnything/Depth-Anything-V2` |
| **Upstream Commit** | Pinned Revision SHA | `a561b849ebae10a6f5ef49e26c83cbbcd36c71bf` (HEAD) |
| **Shipped Checkpoint** | Checkpoint Filename | `depth_anything_v2_vits.pth` |
| **Shipped Checkpoint SHA-256** | File Hash | `715FADE13BE8F229F8A70CC02066F656F2423A59EFFD0579197BBF57860E1378` |
| **Research Model Candidate** | Candidate Identifier | `m17` (`M17DepthBackend`) |
| **Research Checkpoint SHA-256** | File Hash | `D7C0BE9127FAFAC5F4C2D207E3626D335AF148A8CBB7489A10EE8C7F7DA4EDAC` |
| **Runtime Provisioning** | Automation Script | `scripts/provision_runtime.py` (Managed venv contract) |
| **Runtime Diagnostics** | Diagnostic Script | `scripts/runtime_check.py` |
