# GAMUS Dataset (evaluation reference)

Selected because it pairs high-resolution RGB orthophotos with a
metric nDSM/AGL height reference in metres — exactly the
`HEIGHT_AGL_NDSM` meaning the pipeline calibrates to. Dataset
documentation below is drawn from the repository's research audit
(recorded read-only; no research code copied).

## Identity

- Dataset: GAMUS — Geometry-aware Multi-modal Semantic Segmentation
  Benchmark (Xiong et al., arXiv 2305.14914).
- Distribution: Hugging Face `earthflow/GAMUS`
  (`https://huggingface.co/datasets/earthflow/GAMUS`).
- License: CC-BY-4.0 (dataset card; attribution required). The upstream
  code repository declares no license — code license and data license
  are not the same; no upstream code is vendored here.
- Release used: current HF distribution (post OMA/JAX removal).

## Content

- RGB orthophoto, 0.33 m, uint8, 1024×1024 tiles (`images/<split>/*_RGB.h5`, H5 key `image`).
- Height/nDSM (AGL, LiDAR-derived), float32 metres (`heights/<split>/*_AGL.h5`).
- Semantic labels (unused by this harness).
- Tiles carry no CRS/transform: evaluation uses the `native-pixel`
  alignment (exact shape match, no resampling).
- Reference semantic: nDSM/AGL — never treated as absolute elevation or DSM.

## Splits

Upstream test split used for held-out scoring (`manifests/gamus-tiny-smoke.json`
pins 2 DC tiles for the smoke). Calibration always uses deterministic
control pixels disjoint from scoring pixels (see protocol doc).

## Preparation (data stays outside git)

```bash
pip install huggingface_hub h5py
# download chosen tiles, e.g. via hf_hub_download("earthflow/GAMUS", ...)
# layout: <GAMUS_ROOT>/images/test/*_RGB.h5 + heights/test/*_AGL.h5
set GAMUS_ROOT=<dir>   # or pass --gamus-root
python scripts/evaluate.py --dataset gamus \
    --manifest manifests/gamus-tiny-smoke.json --split test \
    --backend depth-anything-v2-small --gamus-root <dir> \
    --output results.json
```

Only manifests/metadata are version-controlled; tiles, checkpoints,
and prediction dumps never enter git.
