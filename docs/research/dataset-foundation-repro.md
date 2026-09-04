# Dataset Foundation — Reproducibility

**Version:** M1 (Shravan)
**Date:** 2026-09-04 (re-verified; original audit 2026-09-03)
**Branch:** `feat/shravan-gamus-audit`

This document explains exactly how another developer can reproduce the deterministic dataset foundation (manifest, dev subset, validation, tests) without requiring the full GAMUS dataset.

---

## 1. Dataset source

- **Upstream repo:** `https://github.com/EarthNets/RSI-MMSegmentation` @ `6ed44ba87b59911144430ebc0ca02c1f7a1c62b4` (see `docs/research/gamus-audit.md:1`)
- **Dataset distribution (current):** HF `earthflow/GAMUS` (`sha a3c0e251...`, CC-BY-4.0) — https://huggingface.co/datasets/earthflow/GAMUS
- **Legacy zip:** `https://syncandshare.lrz.de/dl/fiBpfqvv7QE3MxRC18Uocq/GAMUS.zip` (DFC 2019-derived, includes OMA/JAX — now removed in HF)
- **Paper:** arXiv 2305.14914

## 2. Dataset revision / version

- **Upstream code revision:** `6ed44ba87b599...` (inspected 2026-09-03, HEAD of `main`)
- **Dataset revision:** HF `sha a3c0e2511f06d909612406f436cf8abb4da805f5`, lastModified 2024-09-18 (verified via `https://huggingface.co/api/datasets/earthflow/GAMUS`)
- **Manifest version:** `1.0` (field `version` in `manifests/*.manifest.json`) — see `src/depthwizard/data/manifest.py:1`

## 3. License / provenance

See `docs/data-provenance.md:1`.

- Dataset: CC-BY-4.0 — redistribution permitted with attribution; do **not** commit raw `.h5`.
- Code (RSI-MMSegmentation): no LICENSE file — do **not** copy upstream code; adapter preferred.
- Citation: Xiong et al. 2023 (BibTeX in audit doc).

## 4. Expected directory structure

Local dataset root (`GamusConfig.root`, env `GAMUS_ROOT` or `configs/gamus.json`):

```
<GAMUS_ROOT>/
  images/
    train/  DC_*.RGB.h5
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

See `data/README.md:1` and `src/depthwizard/data/schemas.py:1` (file conventions). Legacy `*_IMG.h5` images are also accepted on read (via `_strip_image_suffix`).

## 5. Configuration

Single source of truth: `src/depthwizard/data/config.py:1` (`GamusConfig`).

| Source | Example |
|---|---|
| Env | `GAMUS_ROOT=/mnt/data/gamus` , `GAMUS_MANIFEST=manifests/gamus.manifest.json` |
| JSON | `configs/gamus.example.json` / `configs/gamus.json` (see `configs/README` and `src/depthwizard/data/config.py:12`) |
| Code | `GamusConfig(root=Path("data/gamus"), manifest=Path("manifests/..."), dev_subset_size=20, dev_seed="depthwizard-m1")` |

No hardcoded `C:\...` / `/home/...` paths — `GamusConfig.resolve_root()` resolves relative to project root (`src/` parent).

## 6. Manifest generation

Deterministic: `same input → same manifest`, stable ordering (sorted by `sample_id` then split, no filesystem-order dependence).

```bash
# Without probing (no h5py needed, no dataset required for fixture tests)
python -m depthwizard.data.manifest --root data/gamus --output manifests/gamus.manifest.json

# With probing + checksum (requires local dataset + h5py)
python -m depthwizard.data.manifest --root /mnt/data/gamus --output manifests/gamus.manifest.json --probe --checksum

# Python API
from depthwizard.data.manifest import build_manifest
build_manifest(root="data/gamus", output_path="manifests/gamus.manifest.json", probe=False)
```

Output is deterministic JSON (`indent=2`, `sort_keys=True`, records sorted by `(split_order, sample_id)`). Each record (see `src/depthwizard/data/schemas.py:GamusRecord`) contains `sample_id`, `image_path`, `height_path`, `label_path`, `split`, `source`, optional `checksum`/`dtype`/`width`/`height`.

**Without dataset:** `discover_records` skips missing `images/<split>` directories; tests use fixtures and build manifests purely in-memory (see `tests/test_manifest.py`).

## 7. Development subset generation

Deterministic dev subset — **not a benchmark**, small for CI/local.

```bash
python -m depthwizard.data.subset --manifest manifests/gamus.manifest.json --output manifests/gamus.dev.manifest.json --size 20 --seed depthwizard-m1 --split-source train
```

```python
from depthwizard.data.subset import select_development_subset
from depthwizard.data.manifest import load_manifest
from depthwizard.data.schemas import GamusRecord
recs = [GamusRecord.from_dict(d) for d in load_manifest("manifests/gamus.manifest.json")["records"]]
dev = select_development_subset(recs, size=20, seed="depthwizard-m1", split_source="train")
```

Properties (see `src/depthwizard/data/subset.py:1`):

- **Algorithm:** SHA256(`f"{seed}:{sample_id}"`) → sort by hex digest → take first `size`. No `random` module, no filesystem order. Pre-sort by `sample_id` before hashing eliminates input-order dependence.
- **Seed:** `dev_seed` in `GamusConfig` (default `"depthwizard-m1"`). Change seed for a different deterministic subset.
- **Source split:** `dev_split_source` (default `train`). Filters before hashing.
- **Size:** `dev_subset_size` (default 20, configurable 0..N). `size >= N` returns all, sorted by hash rank.
- **Reproducibility guarantee:** `select_development_subset` is pure: same `(records, size, seed, split_source)` → same IDs.

Documented size is **not** claimed representative. For CI, the repo ships a tiny fixture manifest (see tests) and a dev subset of ≤32 samples.

## 8. Validation

```python
from depthwizard.data.validation import validate_records, validate_manifest_file
from depthwizard.data.schemas import GamusRecord

report = validate_records(records, root="data/gamus", probe_arrays=False)  # no H5 read
report = validate_records(records, root="data/gamus", probe_arrays=True)   # opens H5 via h5py, checks shape/class/height
report.raise_if_errors()  # raises ValueError with actionable messages
```

Checks (see `src/depthwizard/data/validation.py:1`):

- Pairing (image/height/label suffix vs `sample_id`)
- Shape spatial compatibility (when `probe_arrays=True` and files exist)
- Dtype warnings (image expected `uint8`)
- Missing files (exists under `root`)
- Invalid class values (must be 0..6)
- Duplicate `sample_id` within split, empty `sample_id`, split canonicalization
- Height non-finite (NaN/Inf) warning

**Without dataset:** pass `root=None` or a non-existent root — filesystem checks are skipped or report `missing_file` errors without actually opening H5, so `pytest` still passes.

## 9. Tests

Fixture-based, no dataset download:

```bash
pip install -e ".[dev]"
pytest -q
pytest tests/test_manifest.py -v
pytest tests/test_subset.py -v
```

Coverage (see `tests/test_*.py`):

1. manifest determinism
2. stable ordering
3. dev-subset determinism
4. record validation
5. image/height/label pairing
6. missing-file detection
7. shape mismatch detection
8. invalid schema detection
9. adapter sample contract
10. behavior when real GAMUS dataset unavailable

Tests also verify: filesystem-order independence, seed sensitivity, split filtering, duplicate detection, invalid class detection, adapter lazy loading without H5.

## 10. Known limitations

- Height nodata sentinel unknown (no `-9999` documented) — validation only flags non-finite.
- City-to-split stratification unknown — cannot verify leakage risk without full download (see audit §6).
- Tile counts differ paper vs HF due to post-paper OMA/JAX removal — HF count is current.
- H5 internal key evolved `data` → `image` — adapter probes both.
- Dimensions outside `1024×1024` advisory are not enforced without probing.

---

## 11. One-command verification

```bash
pytest -q && python -m depthwizard.data.manifest --help && python -m depthwizard.data.subset --help
```

### Distinguishing verified facts / assumptions / unverified

- **Verified facts:** file suffixes, directory layout, class encoding, license, split names, tile size 1024, HF counts — all pinned to inspected revision/API (see audit).
- **Assumptions:** RGB `uint8`, height `float32` meters, 3-channel image — inferred from code + file sizes, flagged as probes.
- **Could not be verified without full download:** city split stratification, overlapping-tile leakage, exact height value range, per-tile CRS. See `docs/research/gamus-audit.md:8`.

Do **not** invent dataset statistics — use manifest after local acquisition.
