# M17 Product Promotion Analysis — DepthWizard (SIH 26175)

**Date:** 2026-09-06
**Author:** Shivam (Architecture + Release Authority)
**Main:** `02a065070ba88c75f016956ae651a3269c55da63`
**Status:** ANALYSIS ONLY. No model swap performed. No experiment created.

---

## 1. Current Candidate (research-locked)

M17 per `docs/final-ml-candidate.md` (on main via PR #3):

| Element            | Value                                                              |
| ------------------ | ------------------------------------------------------------------ |
| Model              | DA-V2-Small frozen backbone + 23k Pearson-adapted head, epoch 6    |
| Checkpoint         | `experiments/m17-geonrw-struct-e01/checkpoints/best.pt`            |
| SHA-256            | `D7C0BE9127FAFAC5F4C2D207E3626D335AF148A8CBB7489A10EE8C7F7DA4EDAC` |
| Upstream           | `a561b849…` (same pin as product)                                  |
| Output semantics   | RELATIVE (`is_metric=False`, units None)                           |
| Preprocessing      | Frozen (RGB HWC uint8 → first-3 → ImageNet/518; frozen M10 zstats) |
| External evidence  | Probe Pearson 0.37 (6/6 cities over M10 0.25); slopes <1 persist   |
| Formal test cities | BLOCKED on data access (verification-only role)                    |

## 2. Current Product Backend

`DepthAnythingV2Backend` (`src/depthwizard/backends/depth_anything_v2.py`): frozen DA-V2 Small, official `infer_image` path, checkpoint `depth_anything_v2_vits.pth` (SHA256 `715fade…378`), RELATIVE output, registered as `depth-anything-v2-small` only when upstream source + torch + checkpoint resolve.

## 3. Exact Mismatch

| Aspect            | Product (DA-V2 Small)                                                  | Candidate (M17)                                                       |
| ----------------- | ---------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Weights           | HF `depth_anything_v2_vits.pth`                                        | `best.pt` (23k adapted head)                                          |
| Preprocessing     | BGR→RGB/255, keep-aspect resize, ImageNet norm, restore to source size | First-3 channels, ImageNet/518, source-grid output, frozen zscore I/O |
| Output grid       | Restored to source (H,W)                                               | Follows source grid (`out_hw` = H/W)                                  |
| Provenance fields | `MODEL_NAME/VERSION`, `CHECKPOINT_SHA256`, `UPSTREAM_REVISION`         | Additional: M10 base SHA, GeoNRW set SHA, epoch, Pearson              |
| Registration      | `depth-anything-v2-small`                                              | No registered name; no service wiring                                 |

The two are **not drop-in interchangeable**: preprocessing, checkpoint identity, and provenance shape all differ.

## 4. Promotion Requirements

1. **New backend class** (e.g. `M17DepthBackend`) implementing the unchanged `DepthBackend` protocol — the protocol itself must not change.
2. **Checkpoint distribution**: `best.pt` placed under the existing checkpoint policy (external, SHA-verified, never committed); `CHECKPOINT_SHA256` extended per-backend, not replaced.
3. **Preprocessing isolation**: all M17 specifics inside the backend; the rest of DepthWizard stays model-agnostic.
4. **Provenance extension**: candidate, M10 base SHA, GeoNRW set SHA, epoch carried in `ProductProvenance` without breaking existing fields.
5. **Registration**: distinct backend id (never silent substitution for `depth-anything-v2-small`); service capabilities advertise both.
6. **Runtime**: CPU-validated already (probe ran CPU-only); provisioning gains a `best.pt` fetch/verify path mirroring the existing checkpoint flow.
7. **Desktop**: transport renders M17 products through the same `SceneArtifact` boundary; no viewer changes required.

## 5. Checkpoint Handling

`best.pt` follows the exact policy of `depth_anything_v2_vits.pth`: external file, resolved via `DW_DAV2_CKPT`-style explicit env (new var, e.g. `DW_M17_CKPT`) → data dir → repo-dev; SHA-256 verified before registration; mismatches quarantined. Never committed.

## 6. Preprocessing Requirements

Frozen §13 of the candidate doc, implemented verbatim inside the new backend class. Any deviation invalidates the probe evidence and reopens evaluation.

## 7. Provenance Requirements

Per §4.4 above; calibration and downstream stages consume only the protocol surface (`DepthResult` + validity + provenance), so no downstream changes are needed if the protocol is honored.

## 8. Runtime Packaging Impact

- Provisioning: one more verified asset (same machinery, new identity).
- Installer: unchanged (checkpoint stays external).
- Offline: unchanged (local checkpoint after provisioning).
- `pyproject` optional dependencies: **no change** — M17 needs exactly the existing `dav2` extra (torch, torchvision, opencv); no new third-party packages.

## 9. Regression Tests Required

- Protocol conformance (new backend satisfies `DepthBackend`).
- RELATIVE semantics preserved (`units=None`, never metres).
- Determinism (repeat inference identical).
- Preprocessing pinned to source-grid behavior.
- Unknown-backend rejection still loud; no synthetic fallback.
- Existing DA-V2 Small path untouched (full suite green).

## 10. Is Promotion Currently Justified?

**Not yet.** The candidate is honestly strong on probe evidence, but: formal test-city scoring is pending (its defined verification role), calibration with M17 outputs is undemonstrated, and the product path (DA-V2 Small) is frozen and verified. Promoting now would swap a verified backend for an unverified-in-product one. Recommendation: hold M17 in research until (a) formal test-city verification completes, and (b) a backend-class PR with the regression tests above passes review. **Do not create another M-series experiment to resolve this — the evidence program is defined; only execute it.**

---

**End of promotion analysis.** No code changed; no experiment created.
