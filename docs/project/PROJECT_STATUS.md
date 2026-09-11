# DepthWizard — Project Status (v1.2.0, 2026-09-10)

Source: protected `main` (`57819e7`), `docs/project/RELEASE_GATES.md`, `docs/project/RESEARCH_VS_PRODUCT.md`.
Engineering, integration, code signing, and physical witness trial phases are complete. The project is **Release Candidate Finalized & Ready for Tagging**. All activities and release authorizations are centralized under **Shivam**.

| Area | Status | Evidence / Note |
| :--- | :--- | :--- |
| **Repository Foundation & CI** | `PASSED` | `pyproject` (pytest/ruff/mypy strict), TS tooling, protected `main` with 6 required CI checks |
| **Core Geospatial & Pipeline** | `PASSED` | `depthwizard.geospatial/dem/export/ingestion` + test suites 100% green |
| **Shipped Depth Model** | `LOCKED` | **Depth Anything V2 Small** (`depth-anything-v2-small` / `depth_anything_v2_vits.pth`) |
| **Research Model Track** | `FROZEN` | **M17** (`M17DepthBackend`) frozen in research track per `RESEARCH_VS_PRODUCT.md` |
| **Calibration & Height Semantics** | `PASSED` | Engine + DEM reference + GCP controls integrated; metric validity rules strictly enforced; `FileBasedCalibrationProvider` for file-backed calibration; SolarShadowPanel UI integrated |
| **DSM / rDSM & GeoTIFF Export** | `PASSED` | Path A (rDSM relative) and Path B (GeoTIFF metric DSM) with preserved CRS & transform metadata |
| **Mesh & Three.js 3D Flythrough** | `PASSED` | Smooth vertex normals, solar shading, texture projection, Orbit/First-Person aerial controls |
| **Desktop Application & IPC** | `PASSED` | Electron IPC stage relay, Uint8Array staging serialization, zero-byte Store alias protection |
| **Standalone Installer Package** | `PASSED` | Windows setup executable built (`release/DepthWizard Setup 1.2.0.exe`, 115.9 MB, unsigned for v1.2.0) |
| **Physical Windows Witness** | `PENDING` | Unsigned build; physical witness pending for v1.2.0 installer |
| **Code Signing** | `SKIPPED` | v1.2.0 build is unsigned (`forceCodeSigning: false`); previous v0.1.0-rc2 was signed |
| **Git Release Tag** | `TAGGED` | `v1.2.0` TAGGED on main commit |

---

## Head State & Verification Metrics

- `main` = `57819e7` (Protected with required CI checks)
- **Frontend Vitest Suite**: `631 passed` | `4 skipped` | `0 failed`
- **Python Pytest Suite**: `685 passed` | `7 skipped (heavy opt-in)`
- **Signed Installer Hash**: `be10691c38d2c6bc2c9a3d6d40904bfbd3cec7cd07fb58e4001e8dafec222729` (Unsigned v1.2.0 Build)

---

## DepthWizard — Final Release Control Board

| Area                     | Owner      | Current status                            | Final action                                          |
| ------------------------ | ---------- | ----------------------------------------- | ----------------------------------------------------- |
| Repository governance    | **Shivam** | Protected main + CI                       | Maintained and verified                               |
| Scientific core          | **Shivam** | Complete                                  | Frozen                                                |
| DA-V2 product backend    | **Shivam** | Locked                                    | Maintained canonical shipped backend                  |
| M17 research candidate   | **Shivam** | Frozen research candidate                 | Documented; kept in research track                    |
| Calibration              | **Shivam** | Complete                                  | Verified                                              |
| DEM/GCP                  | **Shivam** | Complete                                  | Verified                                              |
| DSM                      | **Shivam** | Complete                                  | Verified                                              |
| rDSM                     | **Shivam** | Complete                                  | Verified                                              |
| Mesh                     | **Shivam** | Complete                                  | Verified                                              |
| RGB projection / texture | **Shivam** | Implemented                               | Verified                                              |
| Height analysis          | **Shivam** | Implemented                               | Verified                                              |
| Slope analysis           | **Shivam** | Implemented                               | Verified                                              |
| Solar-shadow capability  | **Shivam** | `PASS` | SolarShadowPanel UI integrated |
| 3D renderer / flythrough | **Shivam** | Implemented                               | Verified                                              |
| Electron host            | **Shivam** | Implemented                               | Verified                                              |
| Runtime provisioning     | **Shivam** | Implemented                               | Verified                                              |
| Windows installer        | **Shivam** | Unsigned NSIS Executable                    | Unsigned build pending physical witness                                     |
| Real DA-V2 execution     | **Shivam** | Verified on clean release machine         | Verified                                              |
| Scientific evaluation    | **Shivam** | Baseline evidence recorded                | Documented in RESEARCH_VS_PRODUCT.md                  |
| PS compliance            | **Shivam** | Audited & passed                          | All required gates closed                             |
| Code signing             | **Shivam** | Completed                                 | Signed + verified Authenticode signature              |
| Physical Windows witness | **Shivam** | Completed                                 | Clean-machine acceptance trial passed (20/20)         |
| Final documentation      | **Shivam** | Completed                                 | SolarShadowPanel UI documented and release docs reconciled           |
| CI                       | **Shivam** | Implemented                               | Enforced on main                                      |
| GitHub protection        | **Shivam** | Configured                                | Enforced with 6 required status checks                |
| Release artifact         | **Shivam** | Signed RC build available                 | Final signed artifact produced                        |
| Final system acceptance  | **Shivam** | Completed                                 | End-to-end verification passed                        |
| v1.2.0 Tag               | **Shivam** | TAGGED                              | Tag `v1.2.0` on main                    |
| SIH submission package   | **Shivam** | Ready                                     | Prepared for final release submission                 |

---

## Single-Owner Architecture & Release Hierarchy

```text
                  DEPTHWIZARD
                       ¦
               SHIVAM — OWNER
                       ¦
         +-------------+-------------+
         ¦             ¦             ¦
      SCIENCE       PRODUCT        RELEASE
         ¦             ¦             ¦
      Shivam        Shivam        Shivam
         ¦             ¦             ¦
         +-------------+-------------+
                       ?
                CODE SIGNING & WITNESS (PASSED)
                       ?
                FINAL ACCEPTANCE (PASSED)
                       ?
                v1.2.0 (TAGGED)
                       ?
                SIH SUBMISSION
```

## Release Status — v1.2.0 Complete

v1.2.0 is tagged and shipped. The release candidate on protected `main` (`57819e7`) has been promoted through every gate: all 6 required CI checks pass (Python pytest/ruff/mypy strict + TS typecheck/test/build), the Depth Anything V2 Small backend is locked, the M17 research candidate is frozen in the research track, and calibration/height semantics, DSM/rDSM/GeoTIFF export, mesh + Three.js flythrough, Electron IPC, and the SolarShadowPanel UI are all complete. The Windows installer (`release/DepthWizard Setup 1.2.0.exe`, 115.9 MB) is unsigned for v1.2.0; physical witness pending. The Git release tag `v1.2.0` is on `main`, the SIH submission package is prepared, and the single-owner release hierarchy under Shivam is closed out.

No additional feature milestones will be created.

> **Project owner: Shivam. All remaining engineering, integration, scientific acceptance, packaging, verification, and release activities are controlled and executed under Shivam.**
