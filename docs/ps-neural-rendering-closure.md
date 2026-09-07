# PS Closure — 3D Neural Rendering (SIH 26175)

**Date:** 2026-09-06
**Author:** Shivam (Architecture Authority)
**Main audited:** `809801d45ac7f3be857b284539e4d9028e914e09`
**Status:** REQUIREMENT ANALYSIS + MINIMUM-SCOPE DESIGN. No implementation performed.

---

## 1. What the Authoritative In-Repo Sources Require

The authoritative problem-statement sources available **in the repository** were inspected:

- `docs/project/MASTER_PLAN.md` — "Single-View Height Estimation and 3D Flythrough"; pipeline ends in RGB projection → interactive 3D flythrough. No mention of neural rendering, NeRF, or Gaussian Splatting.
- `docs/project/SIH_REQUIREMENT_TRACEABILITY.md` (R1–R15) — RGB input, rDSM, GeoTIFF, calibration, GeoTIFF export, mesh, RGB texture projection (R7), flythrough (R8), analysis tools, validation, deployment, docs. No solar, neural, or photorealism requirement rows.
- `docs/project/RELEASE_GATES.md` (GATE 1–11) — mesh + texture (GATE 6), interactive 3D (GATE 7). No neural-rendering gate.
- `docs/sih-architecture.md` — textured mesh → interactive 3D viewer. No neural rendering.

**Finding:** the "3D neural rendering" wording comes from the externally supplied PS description, not from any in-repo authoritative source. It is treated here as an externally asserted requirement and audited honestly against the implementation.

## 2. Implementation Audit (verified by repository search)

Search over `src/` (`*.py`, `*.ts`, `*.tsx`) for `NeRF|nerf|GaussianSplat|gaussian_splat|radiance field|radiance_field|novel-view|novel_view|neural rend|view synth` returns **zero matches**. There is no NeRF, no 3D Gaussian Splatting, no neural radiance field, no learned view synthesis, no neural volumetric rendering, no neural appearance representation, no novel-view synthesis anywhere in the codebase.

## 3. What Currently Exists (documented separately, not conflated)

| Capability             | Implementation                                                          | Evidence                                            |
| ---------------------- | ----------------------------------------------------------------------- | --------------------------------------------------- |
| DSM                    | `DSMGrid` (metres, nodata=NaN, CRS preserved)                           | `tests/dsm/`, `tests/export/` pass                  |
| Terrain mesh           | `TerrainMesh` (local + georeferenced)                                   | `tests/mesh/` pass                                  |
| Textured mesh          | Mesh UVs + source identity (`meshAdapter.ts`); RGB projection in viewer | `src/backend/meshAdapter.ts`, `RenderingControls`   |
| Three.js rasterization | `three@^0.177.0` triangulated-mesh rasterizer                           | `package.json`, `src/viewer/`, `src/components/`    |
| Camera system          | Orbit / first-person / aerial + waypoint flythrough                     | `src/camera/`, `src/flythrough/`, `FlythroughPanel` |
| Texture pipeline       | Backend mesh adapter → transport → viewer texturing                     | `src/backend/meshAdapter.ts`, transport tests       |

Honest terminology mapping:

| Term                      | Verdict                                                            |
| ------------------------- | ------------------------------------------------------------------ |
| 3D visualization          | ✅ YES                                                             |
| 3D rendering              | ✅ YES (rasterization)                                             |
| Photorealistic flythrough | ⚠️ PARTIAL (textured-mesh flythrough; "photorealistic" unmeasured) |
| 3D neural rendering       | ❌ NO                                                              |

## 4. Classification

**C — MAJOR NEW R&D SUBSYSTEM** (if the externally asserted wording is binding). A learned scene representation (radiance field / Gaussians) fitted per scene plus a neural view synthesizer, with GPU fitting, new distribution blobs, installer/platform expansion, and offline-contract rework, is a research program — not a focused patch. See `docs/ps-neural-rendering-gap.md` for cost, packaging, offline, and evidence analysis.

## 5. Minimum Viable Compliance Design (if mandated)

1. Per-scene fitting (NeRF or 3D-GS) from the single input view + derived depth priors — itself open research for single-view satellite imagery.
2. Versioned fitted-representation artifact with provenance (weights/Gaussian parameters, fit config, input checksum linkage).
3. Viewer integration: WebGL/WASM neural renderer alongside (never replacing) the mesh path.
4. Quality protocol: held-out novel-view metrics (PSNR/SSIM/LPIPS or task-appropriate) vs the rasterized baseline, plus frame-rate measurements on target hardware.
5. Re-verification of the offline-after-provisioning contract (`HF_HUB_OFFLINE=1` gate re-run).

No placeholder "AI" features, no hardcoded demo tricks, no terminology inflation: either this program is resourced and accepted, or the product claim stays at "interactive textured-mesh 3D visualization and flythrough."

---

**End of closure analysis.** Classification recorded; implementation explicitly not started.
