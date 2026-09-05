# Shravan DA-V2 Integration

## Overview

Ports the Shravan `DepthAnythingV2-Small` legacy implementation into the
canonical `DepthBackend` architecture on `main`. The frozen backbone
inference is exposed through a standard adapter so the rest of
DepthWizard remains model-agnostic.

## Branch

`feat/shivam-shravan-dav2-integration` (from `main` at `e852c61`)

## Changes

### New files

| File                                            | Purpose                                    |
| ----------------------------------------------- | ------------------------------------------ |
| `src/depthwizard/backends/depth_anything_v2.py` | Canonical `DepthAnythingV2Backend` adapter |
| `tests/backends/test_depth_anything_v2.py`      | Contract + semantics test suite (49 tests) |
| `docs/shravan-dav2-integration.md`              | This document                              |

### Modified files

| File                                   | Change                                 |
| -------------------------------------- | -------------------------------------- |
| `src/depthwizard/backends/__init__.py` | Register `DepthAnythingV2Backend`      |
| `pyproject.toml`                       | Add `[dav2]` optional dependency group |

## Architecture

```
canonical adapter (new)          Shravan legacy (reference only)
─────────────────────────        ──────────────────────────────
DepthAnythingV2Backend           DepthAnythingV2Backend (different class)
  estimate_depth(inspection)       load() / infer(rgb) / close()
  -> DepthResult(relative)         -> np.ndarray (raw)
```

The new adapter consumes the **same upstream model** (pinned clone +
official checkpoint) but exposes it through the standard
`DepthBackend` protocol. The legacy class is a parallel implementation
with different semantics — it is NOT imported or referenced.

## Model metadata

| Property           | Value                                                              |
| ------------------ | ------------------------------------------------------------------ |
| Model              | Depth Anything V2 Small                                            |
| Encoder            | vits                                                               |
| Params             | 24 785 089                                                         |
| Checkpoint         | `depth_anything_v2_vits.pth`                                       |
| Checkpoint SHA-256 | `715fade13be8f229f8a70cc02066f656f2423a59effd0579197bbf57860e1378` |
| HF ID              | `depth-anything/Depth-Anything-V2-Small`                           |
| Upstream           | https://github.com/DepthAnything/Depth-Anything-V2                 |
| Upstream revision  | `a561b849ebae10a6f5ef49e26c83cbbcd36c71bf`                         |
| License            | Apache-2.0 (permissive scale)                                      |
| Device             | `cpu` / `cuda` / `mps` (auto-fail if unavailable)                  |
| Input size         | 518                                                                |

> **Provenance note:** `Upstream revision` is the git commit hash (40 hex
> chars) of the pinned repository. `Checkpoint SHA-256` is the file hash
> (64 hex chars) of the downloaded weights. These are distinct values
> serving different provenance purposes.

## Preprocessing (per official `infer_image` path)

| Step           | Detail                                                                 |
| -------------- | ---------------------------------------------------------------------- |
| Input color    | BGR uint8 HWC (cv2.imread convention)                                  |
| Colorscale     | BGR2RGB then `/255.0`                                                  |
| Resize         | keep aspect ratio, lower bound, `INTER_CUBIC`, `ensure_multiple_of=14` |
| Normalize      | ImageNet `mean=[0.485,0.456,0.406]` `std=[0.229,0.224,0.225]`          |
| Tensor         | `PrepareForNet` HWC→CHW `float32`                                      |
| Output restore | bilinear interpolate to `(source_H, source_W)`                         |

## Output semantics

| Property              | Value                                 |
| --------------------- | ------------------------------------- |
| `depth_scale`         | `DepthScale.RELATIVE`                 |
| `is_metric`           | `False` always                        |
| `units`               | `None` always                         |
| `elevation_semantics` | `ElevationSemantics.RELATIVE_DEPTH`   |
| CRS/transform         | Passed through from input (unchanged) |
| Calibration           | `None` (no calibration)               |
| Valid mask            | `None` (all samples assumed finite)   |

## Optional dependency

The `dav2` extra installs torch, torchvision, and opencv-python:

```bash
pip install -e ".[dav2]"
```

Without it, `DepthAnythingV2Backend` is importable but raises
`ModelInferenceError` on inference. Tests use dependency injection
(fake model) so no torch is required.

## Test suite

49 tests covering:

| Category                 | Tests                                                           |
| ------------------------ | --------------------------------------------------------------- |
| Backend contract         | Protocol conformance, model_name, model_version, checkpoint_id  |
| Relative semantics       | RELATIVE scale, no metric, no calibration                       |
| Output dimensions        | PNG/JPEG/GeoTIFF resolution, value count                        |
| Value preservation       | Deterministic fake output, sinusoidal verification              |
| Preprocessing record     | Keys present, configuration documented                          |
| Provenance               | Model name, checkpoint, input checksum, units, semantic meaning |
| Georeference passthrough | NON_GEOREFERENCED for PNG, CRS passthrough for GeoTIFF          |
| Input validation         | Rejects non-InputInspection, rejects None                       |
| Checkpoint missing       | ModelInferenceError with checkpoint info                        |
| Torch missing            | ModelInferenceError with install instructions                   |
| Device unavailable       | ValueError for unknown device                                   |
| Model output shape       | ModelInferenceError for wrong dimensions                        |
| Non-finite output        | NaN values still produce valid result                           |
| Source immutability      | Input files not modified                                        |
| Determinism              | Two calls produce equivalent results                            |
| Optional dependency      | Module importable without torch                                 |
| Image loading            | PNG, JPEG, GeoTIFF, single-band TIFF                            |
| Metadata constants       | Upstream URL, revision, SHA-256, encoder config, input size     |
| Provenance distinction   | Upstream revision (40 hex) vs checkpoint SHA-256 (64 hex)       |
| Dependency availability  | Importable without torch, torch available                       |

### Conditional real-model smoke test

A genuine DA-V2 inference test exists but is **opt-in** to avoid network
dependency and large downloads in CI:

```bash
DW_DAV2_REAL_SMOKE=1 DW_DAV2_CKPT=checkpoints/depth_anything_v2_vits.pth \
  pytest tests/backends/test_depth_anything_v2.py::TestRealModelSmoke -v
```

Verified facts (2026-09-05):

- Checkpoint SHA-256: `715fade13be8f229f8a70cc02066f656f2423a59effd0579197bbf57860e1378`
- Output: RELATIVE depth, all finite, restored to source size
- Model load: ~5.6s CPU, inference: ~1.0s per 64×64 image (CPU)
- Determinism: identical values across repeated runs

All tests run without torch/cv2 via dependency injection.
