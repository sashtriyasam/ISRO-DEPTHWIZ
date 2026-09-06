# PS Gap — 3D Neural Rendering (SIH 26175)

**Date:** 2026-09-06
**Auditor:** Shivam (Architecture Authority)
**Main:** `809801d45ac7f3be857b284539e4d9028e914e09`
**Status:** CONFIRMED GAP — no neural rendering exists. No code changes in this document.

---

## 1. Requirement

SIH PS 26175 references **3D neural rendering** as part of the reconstruction → visualization chain.

## 2. Current Capability

The desktop renders the canonical `TerrainMesh` with Three.js (`three@^0.177.0`): traditional GPU rasterization of triangulated geometry with UV RGB texture projection, waypoint flythrough camera, display-only height exaggeration.

Repository-wide search (`*.py`, `*.ts`, `*.tsx` under `src/`) for `NeRF|nerf|GaussianSplat|radiance field|novel-view|neural rend` returns **zero implementation matches**.

| Term                      | Honest verdict                                                        |
| ------------------------- | --------------------------------------------------------------------- |
| 3D visualization          | ✅ YES (interactive Three.js scene)                                   |
| 3D rendering              | ✅ YES (rasterization)                                                |
| Photorealistic flythrough | ⚠️ PARTIAL (textured mesh flythrough; "photorealistic" unmeasured)    |
| 3D neural rendering       | ❌ NO (no NeRF, no 3D Gaussian Splatting, no learned radiance fields) |

**Do not equate Three.js with 3D neural rendering. Do not equate terrain mesh with solar-shadow geometry.** Those are separate questions with separate answers.

## 3. Exact Mismatch

Neural rendering requires a learned scene representation (radiance field / Gaussians) fitted per scene plus a differentiable/neural view synthesizer. The current pipeline has neither: geometry comes from calibrated DSM triangulation, appearance from direct RGB texture projection.

## 4. Smallest Viable Implementation (if required)

1. Per-scene fitting step (NeRF or 3D-GS) from the single input view plus derived depth priors — itself a research problem for single-view satellite imagery.
2. Export of fitted representation (weights / Gaussian parameters) as a versioned artifact with provenance.
3. Viewer integration: WebGL/WASM renderer for the representation alongside (not replacing) the mesh path.
4. Quality protocol: novel-view error metrics on held-out views, reported — never eyeballed.

## 5. Computational Cost

- Fitting: GPU-hours per scene on workstation GPUs; infeasible on the current CPU-only lab and on end-user laptops at install time.
- Storage: fitted representations are scene-specific blobs (tens of MB), multiplying distribution size.
- Runtime: real-time neural view synthesis needs discrete-GPU-class hardware for usable frame rates.

## 6. Packaging Implications

- New native/GPU dependencies (CUDA builds, WASM bundles) in the installer; platform matrix explodes (x64/arm64 × GPU/CPU).
- Scene-fit cache layout in the managed data dir; cache invalidation rules.
- `electron-builder.yml` targets and `extraResources` must be re-scoped.

## 7. Offline Implications

Fitting requires shipping optimizer + framework weights or performing fits at build time per scene; either breaks the current offline-after-provisioning contract unless explicitly re-architected and re-verified (`HF_HUB_OFFLINE=1` gate must be re-run).

## 8. Evidence Required

- Held-out novel-view metrics (PSNR/SSIM/LPIPS or task-appropriate) vs the rasterized baseline.
- Frame-rate measurements on target hardware.
- Provenance: representation version + fit config + input checksum linkage.

## 9. Release Risk

**HIGH.** New research track + GPU dependency + packaging expansion + offline-contract rework. Classification **C (MAJOR GAP — NEW R&D SUBSYSTEM REQUIRED)**. Do not start implementation until separately scoped, resourced, and accepted. The honest interim product claim is "interactive textured-mesh 3D visualization and flythrough," not neural rendering.

---

**End of gap analysis.** No implementation performed; no evidence fabricated.
