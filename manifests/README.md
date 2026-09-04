# Manifests

Deterministic JSON manifests identifying GAMUS samples without embedding raw data.

Each entry (see `src/depthwizard/data/schemas.py:1`):

```json
{
  "sample_id": "DC_03_26",
  "image_path": "images/train/DC_03_26_RGB.h5",
  "height_path": "heights/train/DC_03_26_AGL.h5",
  "label_path": "classes/train/DC_03_26_CLS.h5",
  "split": "train",
  "source": "gamus",
  "checksum": "sha256:... (optional, file content if available)"
}
```

Generation: `python -m depthwizard.data.manifest --root <GAMUS_ROOT> --output manifests/gamus.manifest.json`

Ordering is deterministic (sorted by `sample_id`), independent of filesystem traversal order. See `docs/research/dataset-foundation-repro.md:1`.
