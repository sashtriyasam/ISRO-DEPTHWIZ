# Data directory

Local GAMUS tiles are **not committed**. Expected on-disk layout after manual acquisition ( HF `earthflow/GAMUS` or legacy `GAMUS.zip`):

```
<GAMUS_ROOT>/
  images/
    train/  DC_*.RGB.h5  (or *_IMG.h5 legacy)
    val/    DC_*.RGB.h5
    test/   DC_*.RGB.h5
  heights/
    train/  DC_*.AGL.h5
    val/    ...
    test/   ...
  classes/
    train/  DC_*.CLS.h5
    val/    ...
    test/   ...
```

Configure the root via:

- env `GAMUS_ROOT`, or
- `configs/gamus.json` (`{"root": "...", "split": "train", ...}`), or
- `GamusConfig(root=Path(...))` in code.

See `src/depthwizard/data/config.py:1` and `docs/research/dataset-foundation-repro.md:1`.

Manifests (JSON) live in `manifests/` and are the only version-controlled dataset artifact.
