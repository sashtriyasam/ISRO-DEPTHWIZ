# DepthWizard — Project Status (v1.3.1, 2026-09-22)

Source: protected `main`, `docs/project/RELEASE_GATES.md`, `docs/project/RESEARCH_VS_PRODUCT.md`.
Engineering, integration, satellite-backend wiring, and release packaging are under **Shivam**.

| Area | Status | Evidence / Note |
| :--- | :--- | :--- |
| **Repository Foundation & CI** | `PASSED` | `pyproject` (pytest/ruff/mypy), TS tooling, protected `main` with 6 required CI checks |
| **Core Geospatial & Pipeline** | `PASSED` | `depthwizard.geospatial/dem/export/ingestion` + flat-depth variance warning |
| **Shipped Depth Model** | `LOCKED` | **Depth Anything V2 Small** (`depth-anything-v2-small`) |
| **Satellite Adaptation Backend** | `WIRED` | `depth-anything-v2-satellite` advertised when `DW_DAV2_SAT_CKPT` / repo checkpoint present; relative depth only |
| **Research Model Track** | `FROZEN` | **M17** frozen in research track per `RESEARCH_VS_PRODUCT.md` |
| **Calibration & Height Semantics** | `PASSED` | Selectable calibrators + `FileBasedCalibrationProvider`; SolarShadowPanel UI |
| **DSM / rDSM & GeoTIFF Export** | `PASSED` | Path A (rDSM relative) and Path B (metric DSM) with preserved CRS & transform |
| **Mesh & Three.js 3D Flythrough** | `PASSED` | Texture projection, Orbit / First-Person / waypoint flythrough |
| **Desktop Application & IPC** | `PASSED` | Electron injects `DW_DAV2_CKPT` + `DW_DAV2_SAT_CKPT` into service spawns |
| **Standalone Installer Package** | `IN PROGRESS` | Windows NSIS installer for `v1.3.1` (unsigned, `forceCodeSigning: false`) |
| **Physical Windows Witness** | `PENDING` | Installer install/check after `v1.3.1` publish |
| **Code Signing** | `SKIPPED` | `forceCodeSigning: false` for this cut |
| **Git Release Tag** | `PENDING` | `v1.3.1` to be tagged on merge tip after CI |

---

## Head State & Verification Metrics

- Satellite smoke training produced a local finite-loss checkpoint (git-ignored); SHA-256 pinned in `SatelliteDepthBackend.CHECKPOINT_SHA256`.
- Service capabilities advertise `depth-anything-v2-satellite` when the checkpoint resolves.
- Frontend / bridge prefer Large ? Satellite ? Small ? M17 when available.
- Weights and GAMUS tiles are never committed (`.gitignore`).

---

## DepthWizard — Final Release Control Board

| Area                     | Owner      | Current status                            | Final action                                          |
| ------------------------ | ---------- | ----------------------------------------- | ----------------------------------------------------- |
| Repository governance    | **Shivam** | Protected main + CI                       | Maintained                                            |
| Scientific core          | **Shivam** | Complete                                  | Frozen protocol                                       |
| DA-V2 product backend    | **Shivam** | Locked                                    | Canonical shipped backend                             |
| Satellite adaptation     | **Shivam** | Wired + smoke-trained                     | Relative only; metric requires calibration evidence   |
| M17 research candidate   | **Shivam** | Frozen research candidate                 | Research track                                        |
| Calibration / DEM / DSM  | **Shivam** | Complete                                  | Verified                                              |
| Desktop / Electron       | **Shivam** | Satellite env injection complete          | Installer cut for v1.3.1                              |
| Release artifact         | **Shivam** | v1.3.1 packaging                          | Publish after merge + installer build                 |
| SIH submission package   | **Shivam** | Active                                    | Controlled under Shivam                               |

---

## Single-Owner Architecture & Release Hierarchy

```text
                  DEPTHWIZARD
                       |
               SHIVAM — OWNER
                       |
         +-------------+-------------+
         |             |             |
      SCIENCE       PRODUCT        RELEASE
         |             |             |
      Shivam        Shivam        Shivam
         |             |             |
         +-------------+-------------+
                       |
                v1.3.1 (satellite wiring complete)
                       |
                SIH SUBMISSION
```

> **Project owner: Shivam. All remaining engineering, integration, scientific acceptance, packaging, verification, and release activities are controlled and executed under Shivam.**

> **Scientific truthfulness:** relative depth ? metric DSM. The satellite backend remains `metric=false` until calibration / reference evidence is attached.
