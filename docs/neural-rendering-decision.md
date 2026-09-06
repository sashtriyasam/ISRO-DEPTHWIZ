# Neural Rendering Decision — DepthWizard (SIH 26175)

**Date:** 2026-09-06
**Author:** Shivam (Architecture Authority)
**Main:** `02a0650`
**Status:** BOUNDED DECISION. No framework added. No implementation performed.

---

## 1. Question

Does the SIH solution need a neural/learned novel-view renderer (NeRF-family, 3D Gaussian Splatting, single-image view synthesis), or does the existing textured-mesh rasterization satisfy the product?

Authoritative input: the official PS 26175 text (portal-verified 2026-09-06) names "a rendering engine such as Unity, Three.js, or Babylon.js" — all traditional rasterization engines. No neural-rendering term exists in the PS or in any in-repo authoritative source. The "neural" wording arrived solely via secondary prompt description.

## 2. Current Baseline (guaranteed)

Textured `TerrainMesh` (UVs + source identity + preserved spatial context) rendered with Three.js rasterization, waypoint flythrough, display-only height exaggeration. Deterministic, CPU-capable, offline after provisioning, packaged in the existing installer with no new native dependencies. Contract: `depthwizard.texture.TextureProjection`; tests in `tests/texture/`.

## 3. Candidate Class Audit (from public, long-established knowledge)

| Candidate family                                         | Single-image?       | Remote-sensing fit                                                | License posture             | GPU need                                  | CPU fallback             | Windows/offline/packaging          |
| -------------------------------------------------------- | ------------------- | ----------------------------------------------------------------- | --------------------------- | ----------------------------------------- | ------------------------ | ---------------------------------- |
| NeRF-family (per-scene optimization)                     | No (multi-view fit) | Poor (needs dense views)                                          | Mixed (research codes vary) | Required for practical fit/render         | Infeasible frame rates   | Breaks installer matrix            |
| 3D Gaussian Splatting (per-scene optimization)           | No (multi-view fit) | Poor (same view requirement)                                      | Mixed                       | Required                                  | Infeasible               | Breaks installer matrix            |
| Single-image view-synthesis models (Zero-1-to-3 lineage) | Yes                 | Unproven on satellite DSM terrain; checkpoint licensing per-model | Per-model check required    | Strongly preferred; CPU minutes-per-frame | Degraded quality/latency | Large weight blobs in distribution |

No candidate was downloaded, executed, or benchmarked here — this is a paper-level triage, stated as such.

## 4. Evaluation Against Product Constraints

- **Single-image compatibility:** only the third family qualifies; all require per-scene quality evidence that does not exist in this repo.
- **Remote-sensing suitability:** unproven for satellite DSM terrain in every family.
- **Checkpoint availability/license:** would require per-model provenance work (SHA, upstream, license) with NC-licensed variants excluded as with DA3.
- **GPU requirement:** lab and target machines are CPU-only; neural fitting/synthesis without GPU is not shippable.
- **Windows/offline/packaging:** new native/CUDA/WASM dependencies explode the installer matrix and endanger the verified offline contract.
- **Determinism/reproducibility:** stochastic fitting breaks the deterministic-evidence bar unless pinned and re-verified.
- **DSM/mesh integration:** any neural path must consume (never replace) the calibrated DSM/mesh boundary.

## 5. Decision

**Do not implement neural rendering in this release.** The guaranteed baseline (textured-mesh rasterization) stands; neural rendering is recorded as an **explicit optional enhancement** with entry triggers:

1. An official requirement naming it (current PS does not).
2. A single-image-capable, permissively licensed checkpoint with satellite-terrain evidence.
3. CPU-viable or explicitly GPU-gated runtime story that preserves offline execution.
4. A scoped packaging plan for the new dependencies.

## 6. Prescribed Interface (if a future program proceeds)

```text
NeuralRendererBackend
    input image + geometry/scene context + camera path
    → rendered frame sequence + per-frame provenance
```

Records per run: model, checkpoint, SHA-256, upstream revision, license, runtime/device, seed/config. Requests for neural rendering when unavailable must fail loudly — no silent fallback to rasterization.

---

**End of decision.** Baseline reaffirmed; future work explicitly scoped, not started.
