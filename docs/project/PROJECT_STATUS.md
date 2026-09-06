# DepthWizard — Project Status (Release Candidate Witness Phase, 2026-09-06)

Source: protected `main` (`6d1b7793e5e1980c6184e9e902d2139b9467c9d4`), `docs/project/RELEASE_GATES.md`, `docs/project/RESEARCH_VS_PRODUCT.md`.
Engineering & integration phase is complete. The project is in the **Release Candidate Witness & Code Signing Phase**. All remaining execution, integration, verification, physical witness, code signing, and release authorization activities are centralized under **Shivam**.

| Area | Status | Evidence / Note |
| :--- | :--- | :--- |
| **Repository Foundation & CI** | `PASSED` | `pyproject` (pytest/ruff/mypy strict), TS tooling, protected `main` with 6 required CI checks |
| **Core Geospatial & Pipeline** | `PASSED` | `depthwizard.geospatial/dem/export/ingestion` + test suites 100% green |
| **Shipped Depth Model** | `LOCKED` | **Depth Anything V2 Small** (`depth-anything-v2-small` / `depth_anything_v2_vits.pth`) |
| **Research Model Track** | `FROZEN` | **M17** (`M17DepthBackend`) frozen in research track per `RESEARCH_VS_PRODUCT.md` |
| **Calibration & Height Semantics**| `PASSED` | Engine + DEM reference + GCP controls integrated; metric validity rules strictly enforced |
| **DSM / rDSM & GeoTIFF Export** | `PASSED` | Path A (rDSM relative) and Path B (GeoTIFF metric DSM) with preserved CRS & transform metadata |
| **Mesh & Three.js 3D Flythrough** | `PASSED` | Smooth vertex normals, solar shading, texture projection, Orbit/First-Person aerial controls |
| **Desktop Application & IPC** | `PASSED` | Electron IPC stage relay, Uint8Array staging serialization, zero-byte Store alias protection |
| **Standalone Installer Package** | `RC BUILD` | Windows setup executable built (`release/DepthWizard Setup 1.0.0.exe`, 115 MB) |
| **Physical Windows Witness** | `IN PROGRESS` | Clean-machine installation, runtime discovery, offline execution, and uninstall trial |
| **Code Signing** | `PENDING CERT` | Production signing certificate configuration and Authenticode verification |
| **Git Release Tag** | `NOT TAGGED` | `v0.1.0-sih-26175-rc1` to be tagged on accepted signed commit |

---

## Head State & Verification Metrics

- `main` = `6d1b7793e5e1980c6184e9e902d2139b9467c9d4` (Protected with required CI checks)
- **Frontend Vitest Suite**: `627 passed` | `0 failed`
- **Python Pytest Suite**: `549 passed` | `4 skipped (heavy opt-in)`
- **TypeScript Strict Compiler**: `0 errors`
- **Current Installer Hash**: `9A14514CD52412D32A104609BA9610A3BC517EEF91D4E02F9D2AEA087C3678DB` (Dev/RC Build, `NotSigned`)

---

## DepthWizard — Final Release Control Board

| Area                     | Owner      | Current status                            | Final action                                          |
| ------------------------ | ---------- | ----------------------------------------- | ----------------------------------------------------- |
| Repository governance    | **Shivam** | Protected main + CI                       | Final audit and enforcement verification              |
| Scientific core          | **Shivam** | Complete                                  | Freeze                                                |
| DA-V2 product backend    | **Shivam** | Locked                                    | Maintain canonical shipped backend                    |
| M17 research candidate   | **Shivam** | Frozen research candidate                 | Keep documented; promote only after explicit evidence |
| Calibration              | **Shivam** | Complete                                  | Final verification                                    |
| DEM/GCP                  | **Shivam** | Complete                                  | Final verification                                    |
| DSM                      | **Shivam** | Complete                                  | Final verification                                    |
| rDSM                     | **Shivam** | Complete                                  | Final verification                                    |
| Mesh                     | **Shivam** | Complete                                  | Final acceptance                                      |
| RGB projection / texture | **Shivam** | Implemented                               | Final acceptance                                      |
| Height analysis          | **Shivam** | Implemented                               | Final acceptance                                      |
| Slope analysis           | **Shivam** | Implemented                               | Final acceptance                                      |
| Solar-shadow capability  | **Shivam** | Implemented                               | Final scientific acceptance                           |
| 3D renderer / flythrough | **Shivam** | Implemented                               | Final acceptance                                      |
| Electron host            | **Shivam** | Implemented                               | Final acceptance                                      |
| Runtime provisioning     | **Shivam** | Implemented                               | Final acceptance                                      |
| Windows installer        | **Shivam** | Dev RC Build (`NotSigned`)                | Sign with production EV certificate                   |
| Real DA-V2 execution     | **Shivam** | Verified in development                   | Verify on clean release machine                       |
| Scientific evaluation    | **Shivam** | Evidence available, broader limits remain | Final evidence audit                                  |
| PS compliance            | **Shivam** | Under final audit                         | Close all required gates                              |
| Code signing             | **Shivam** | Outstanding                               | Sign + verify Authenticode signature                  |
| Physical Windows witness | **Shivam** | In progress                               | Clean-machine acceptance trial                        |
| Final documentation      | **Shivam** | In progress                               | Canonicalize all release docs                         |
| CI                       | **Shivam** | Implemented                               | Final verification                                    |
| GitHub protection        | **Shivam** | Configured                                | Verify live settings                                  |
| Release artifact         | **Shivam** | RC build available                        | Produce final signed artifact                         |
| Final system acceptance  | **Shivam** | Pending                                   | Execute end-to-end                                    |
| RC1 Tag                  | **Shivam** | Not created                               | Tag `v0.1.0-sih-26175-rc1` after acceptance            |
| SIH submission package   | **Shivam** | Pending                                   | Prepare after RC acceptance                           |

---

## Single-Owner Architecture & Release Hierarchy

```text
                 DEPTHWIZARD
                      │
              SHIVAM — OWNER
                      │
        ┌─────────────┼─────────────┐
        │             │             │
     SCIENCE       PRODUCT        RELEASE
        │             │             │
     Shivam        Shivam        Shivam
        │             │             │
        └─────────────┼─────────────┘
                      ▼
               CODE SIGNING & WITNESS
                      ▼
               FINAL ACCEPTANCE
                      ▼
               v0.1.0-sih-26175-rc1
                      ▼
              SIH SUBMISSION
```

## Next Actions — Shivam

1. Maintain the protected canonical mainline.
2. Complete production code signing on installer artifact.
3. Verify Authenticode digital signature.
4. Execute clean Windows physical witness trial.
5. Create and push Git tag `v0.1.0-sih-26175-rc1`.
6. Update release status to `RELEASED / SIH ACCEPTED`.
7. Prepare final SIH demonstration and submission package.

No additional feature milestones will be created.

> **Project owner: Shivam. All remaining engineering, integration, scientific acceptance, packaging, verification, and release activities are controlled and executed under Shivam.**

