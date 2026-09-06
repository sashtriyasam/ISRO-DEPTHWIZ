# DepthWizard — Project Status (Release Candidate Witness Phase, 2026-09-06)

Source: protected `main` (`c1f07ca`), `docs/project/RELEASE_GATES.md`, `docs/project/RESEARCH_VS_PRODUCT.md`.
Engineering & integration phase is complete. The project is in the **Release Candidate Witness & Final Audit Phase**.

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
| **Standalone Installer Package** | `RC BUILD` | Windows setup executable built (`DepthWizard Setup 1.0.0.exe`) |
| **Physical Windows Witness** | `IN PROGRESS` | Clean-machine installation, runtime discovery, offline execution, and uninstall trial |
| **Code Signing** | `RELEASE GATE` | Production signing certificate configuration and signature verification |

---

## Head State & Verification Metrics

- `main` = `c1f07ca` (Protected with required CI checks)
- **Frontend Vitest Suite**: `627 passed` | `4 skipped (heavy opt-in)`
- **Python Pytest Suite**: `549 passed` | `4 skipped (heavy opt-in)`
- **TypeScript Strict Compiler**: `0 errors`

---

## Control Board & Handoff Responsibilities

| Owner | Role | Current Assignment | Stop Condition |
| :--- | :--- | :--- | :--- |
| **Shivam** | Lead Architecture & Release | Code signing configuration + final system audit + release authorization | RC1 accepted |
| **Aryan** | Desktop App & Packaging | Clean Windows physical acceptance trial (Install → Launch → Runtime → DA-V2 → DSM → Flythrough → Uninstall) | Witness trial passes |
| **Shravan** | ML & Benchmarks | ML frozen; evidence clarification & GAMUS 32-tile benchmark pack | Already frozen |

---

## Release Finish Sequence

```
                    PROTECTED MAIN (c1f07ca)
                               │
               ┌───────────────┴───────────────┐
               │                               │
         PHYSICAL WITNESS               CODE SIGNING
      Aryan clean Windows trial      Shivam cert & SHA-256
               │                               │
               └───────────────┬───────────────┘
                               │
                               ▼
                       FINAL SYSTEM AUDIT
                               │
                               ▼
                        RC1 TAG & SUBMIT
```

