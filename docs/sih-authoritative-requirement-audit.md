# SIH Authoritative Requirement Audit — DepthWizard (SIH 26175)

**Date:** 2026-09-06
**Auditor:** Shivam (Architecture Authority)
**Main:** `02a065070ba88c75f016956ae651a3269c55da63`
**Status:** Source audit only. No implementation. No portal access in this environment.

---

## 1. Method

Searched the repository for the authoritative problem-statement source: `docs/project/MASTER_PLAN.md`, `docs/project/SIH_REQUIREMENT_TRACEABILITY.md` (R1–R15), `docs/project/RELEASE_GATES.md` (GATE 1–11), `docs/project/TEAM_OWNERSHIP.md`, `docs/sih-architecture.md`, plus full-tree search for `solar|shadow geometr|neural rendering|NeRF|photorealistic`.

**Update 2026-09-06: the live SIH portal WAS reached** (`https://www.sih.gov.in/sih2026PS`, fetched via HTTPS; entry modal `ViewProblemStatement26175`). PS 26175 is an SIH 2026 statement by the Indian Space Research Organisation (ISRO), titled exactly "DepthWizard - Single-View Height Estimation and 3D Flythrough". The full entry text was extracted and searched: **zero matches** for `solar|shadow|neural|nerf|photoreal|trigonometr|gaussian` across the entire PS block (verified programmatically).

## 2. Requirement Table

| Requirement                        | Source                                                                 | Exact wording (where present)                                                         | Authority level                         | Current implementation                            | Evidence                                      | Status                         | Release blocker   | Owner          |
| ---------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | --------------------------------------- | ------------------------------------------------- | --------------------------------------------- | ------------------------------ | ----------------- | -------------- |
| Single optical monocular image     | MASTER_PLAN; traceability R1                                           | "Single-view optical RGB remote-sensing imagery"                                      | **Authoritative (repo)**                | `InputInspection` PNG/JPG/GeoTIFF                 | `tests/ingestion/` pass                       | PASS                           | No                | Shivam         |
| Monocular depth foundation model   | MASTER_PLAN; traceability (GATE 3)                                     | "Monocular geometry / depth runtime"; DA-V2 Small                                     | **Authoritative (repo)**                | `DepthAnythingV2Backend`                          | `tests/backends/` pass                        | PASS                           | No                | Shivam/Shravan |
| Height estimation                  | MASTER_PLAN; traceability R4, R9                                       | "Height estimation"; "Absolute metric DSM calibration"                                | **Authoritative (repo)**                | Relative + calibrated metric paths                | `tests/calibration/`, `tests/height/` pass    | PASS (contract)                | No                | Shivam         |
| Solar-shadow geometry/trigonometry | Portal PS 26175 full text + all in-repo sources searched               | — (term absent from official text)                                                    | **Not required (portal-verified)**      | None (correctly absent)                           | Zero matches in PS block (programmatic)       | NOT REQUIRED                   | No                | Shivam         |
| 3D cityscape reconstruction        | MASTER_PLAN ("3D cityscape" not verbatim; mesh + texture + flythrough) | "terrain mesh → RGB projection → interactive 3D flythrough"                           | **Authoritative (repo, partial scope)** | Single-tile textured mesh                         | `tests/mesh/`, viewer                         | PARTIAL                        | Partial           | Aryan/Shivam   |
| 3D flythrough                      | MASTER_PLAN; traceability R8                                           | "Interactive 3D flythrough (orbit / FP / aerial, waypoints)"                          | **Authoritative (repo)**                | `FlythroughPanel`, camera system                  | `tests/` + viewer                             | PASS                           | No                | Aryan          |
| Photorealistic visualization       | Portal PS 26175 ("visual fidelity" under 50% visualization)            | "visual fidelity" (not "photorealistic")                                              | **Authoritative (portal)**              | Textured-mesh rasterization; fidelity unwitnessed | `src/viewer/`, `src/components/`              | PARTIAL                        | Partial (witness) | Aryan          |
| 3D neural rendering                | Portal PS 26175 (names "Unity, Three.js, or Babylon.js")               | "integrate the result with a rendering engine such as Unity, Three.js, or Babylon.js" | **Not required (portal-verified)**      | Three.js rasterization (PS-sanctioned engine)     | Zero neural matches + PS names raster engines | SATISFIED AS WRITTEN           | No                | Aryan/Shivam   |
| Standalone desktop platform        | MASTER_PLAN; traceability R14                                          | "Standalone deployment (native host, installer, fresh-machine)"                       | **Authoritative (repo)**                | Electron host + NSIS installer + provisioning     | Build exit 0, 115 MB                          | PASS (build; physical pending) | Yes (physical)    | Aryan          |

## 3. Authority Finding

The live portal text (SIH 2026, ISRO, modal `ViewProblemStatement26175`, retrieved 2026-09-06) is now the binding authority, and it **contains none of the three wordings**. The repository-authored contract (MASTER_PLAN → traceability R1–R15 → gates) agrees — it never contained them either. Both wordings arrive solely via the externally supplied prompt description (secondary mirror), which is hereby **overruled by primary evidence**:

- **Solar-shadow: NOT REQUIRED** — absent from official PS text (verified zero-match). Prior gap/closure docs (`docs/ps-solar-shadow-gap.md`, `docs/ps-solar-shadow-closure.md`) are retained as historical analysis; their decision-C program is **cancelled for lack of a requirement**. No implementation.
- **Neural rendering: NOT REQUIRED** — absent from official PS text, which explicitly sanctions rasterization engines ("Unity, Three.js, or Babylon.js"). The Three.js implementation satisfies the requirement as written. Prior gap/closure docs retained as historical analysis; decision-C program **cancelled**. No implementation.
- **Photorealistic: NOT REQUIRED as a term** — the PS requires "visual fidelity" (50% visualization), which remains to be witnessed, not measured here. Product claim stays capped at "textured-mesh visualization and flythrough."

## 4. Rule Applied

Do not implement solar or neural rendering on the basis of a secondary mirror alone. Portal evidence now proves neither is required; both C-classified programs are cancelled. If a future official PS revision introduces either term, re-open G15A/G15B from the filed gap docs.

---

**End of authoritative audit.** Portal retrieved 2026-09-06 (`https://www.sih.gov.in/sih2026PS`, entry `ViewProblemStatement26175`); reference dataset repo renamed to `IMG-PROCESS-SAC/SIH-DepthWizard-2026` (verified via API).
