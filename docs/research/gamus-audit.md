# GAMUS Dataset Audit — DepthWizard Milestone 1

**Inspected:** 2026-09-03; re-verified 2026-09-04 (HEAD unchanged)
**Auditor:** Shravan (ML/data)
**Upstream repository:** `https://github.com/EarthNets/RSI-MMSegmentation`
**Inspected revision:** `6ed44ba87b59911144430ebc0ca02c1f7a1c62b4` (commit date 2024-08-12T07:16:44Z, `HEAD` of `main`, via `git ls-remote` and GitHub API)
**Dataset distribution inspected:** Hugging Face `earthflow/GAMUS` (SHA `a3c0e2511f06d909612406f436cf8abb4da805f5`, lastModified 2024-09-18T07:17:11Z) — current canonical distribution. Legacy reference `XShadow/GAMUS` (mentioned in upstream README prior to 2024-08-12) now resolves to identical `earthflow/GAMUS` id via HF API. Legacy zip `https://syncandshare.lrz.de/dl/fiBpfqvv7QE3MxRC18Uocq/GAMUS.zip` (DFC 2019-derived) is listed but not inspected beyond metadata.
**Paper:** Xiong et al., *GAMUS: A Geometry-aware Multi-modal Semantic Segmentation Benchmark for Remote Sensing Data*, arXiv 2305.14914 (Table 1, §3).
**Code inspected:** `gamus_dataset.py` at HEAD (uses key `'image'`) and at `5d04b4d43c6f3d10c23708c0456acbca3232f5a5` ("add dataloader" 2024-08-11) which used key `'data'`.

---

## 1. Dataset identity

| Field | Value |
|---|---|
| Full name | **GAMUS** — *Geometry-aware Multi-modal Semantic Segmentation Benchmark for Remote Sensing Data* |
| Source paper | https://arxiv.org/pdf/2305.14914.pdf |
| Upstream code | `EarthNets/RSI-MMSegmentation` — official GAMUS dataloader + experiments |
| Distribution (current) | HF `earthflow/GAMUS` — https://huggingface.co/datasets/earthflow/GAMUS |
| Legacy distribution | LRZ syncandshare `GAMUS.zip` (contains DFC 2019 OMA/JAX cities, now removed in current HF release) |
| Cities | 5: Washington DC, Philadelphia, Oklahoma, Jacksonville, New York City (per paper §3.2). Upstream README now states "Remove the cities (OMA and JAX) from the DFC 2019 dataset to ensure the label quality" — current HF release excludes OMA/JAX, explaining smaller split counts vs paper. |
| Tiles (paper-reported) | 11,507 tiles total (6304 train / 1059 val / 4144 test) at `1024×1024` |
| Tiles (HF siblings count verified via `api/datasets/earthflow/GAMUS`) | 8,724 tiles total: 5004 train + 859 val + 2861 test, across three modalities each → 26,172 H5 files + 2 metadata (total siblings 26,174). This post-filter count (after OMA/JAX removal) differs from paper. Both are documented; HF count is authoritative for code. |
| Inspected revision pin | `6ed44ba87b...` — `LICENSE` file absent at this revision (checked `LICENSE`, `LICENSE.md`, `LICENSE.txt` → 404). Repo `license` field via GitHub API is `null`. |

**Citation requirement (from paper):**
```bibtex
@article{xiong2023gamus,
  title={GAMUS: A Geometry-aware Multi-modal Semantic Segmentation Benchmark for Remote Sensing Data},
  author={Xiong, Zhitong and Chen, Sining and Wang, Yi and Mou, Lichao and Zhu, Xiao Xiang},
  journal={arXiv preprint arXiv:2305.14914},
  year={2023}
}
```

---

## 2. Modalities

| Modality | Description | Source terminology | Stored as |
|---|---|---|---|
| **RGB / image** | High-resolution orthophoto (0.33 m) | "RGB" / `images/<split>/*_RGB.h5` | H5 dataset key `image` (current) or `data` (legacy) — `uint8` RGB |
| **height / nDSM** | Normalized DSM (DSM − DTM from LiDAR point clouds) | "height" / "nDSM" / "AGL" (above ground level) — upstream uses `heights/<split>/*_AGL.h5` | H5 dataset key `image`/`data` — floating-point AGL in meters |
| **semantic / class** | Pixel-level land-cover label | "classes" / "CLS" | H5 dataset key `image`/`data` — integer 0..6 |
| Metadata (derived) | Sample identity, split, source | — | Manifest fields only |

**Important semantics (DepthWizard contract):**
- Height is **nDSM/AGL ground truth**, not absolute elevation (ellipsoidal/geoid) and not DSM.
- Semantic labels are labels, not depth.
- Height ground truth must not be silently treated as model-predicted metric elevation downstream.

---

## 3. Data representation

### File format
- **Format:** HDF5 (`.h5`), each tile one file per modality (no TIF/GeoTIFF in HF release; TIFF path mentioned in docs for raw collection).
- **H5 key:** Upstream `gamus_dataset.py` HEAD reads `f['image'][()]`; earlier revision `5d04b4d` read `f['data'][()]`. Both keys occur in the wild — adapter probes `image` then `data` then first dataset.
- **Git LFS:** HF `.gitattributes` marks `*.h5` as LFS (`filter=lfs`), so direct `raw/main/...h5` HTTP fetch returns 404 (verified); XET pointer is served instead. Full download requires `huggingface_hub`/`git lfs`.

### Channel counts / dimensions / dtype

| Modality | Verified | Assumed (needs download to confirm) |
|---|---|---|
| RGB | Channel count 3 implied by `Image.fromarray(image.astype(np.uint8))` and `ToTensor`+ImageNet normalization (transforms in dataloader). Spatial size 1024×1024 reported in paper Table 1 & §3.2 and HF sibling size (4.2 MB per AGL H5). | dtype `uint8` for RGB (verified via code comment "stored as numpy array" + uint8 cast). |
| height (AGL) | Key name & single-band nature; H5 file size 4.2 MB matches float32 1024×1024 (≈4 MB). Paper describes long-tailed height distribution (Fig 3). | dtype likely `float32` (float meters); could be `float64` if derived differently. Value range not documented beyond histogram. |
| class (CLS) | Integer 0..6 (verified via README & paper). | dtype likely `uint8` or `int64`; range 0..6 exact. |

**What could NOT be verified without downloading the complete dataset (documented as assumptions):**
- Exact value range of height (meters) and any nodata/invalid sentinel (e.g., -9999). No sentinel documented in code or paper; adapter validation only flags non-finite (NaN/Inf) as warning.
- Exact normalization/preprocessing stats beyond dataloader example: `Resize((224,224))`, `Normalize(mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225])` are example transforms, not dataset-intrinsic.
- Coordinate/geospatial metadata (CRS, bounds) — not present in dataloader; paper describes derivation from DC/Philly open data but no per-tile GeoTIFF tags exposed in H5.

### Value domains

- **RGB:** 0–255 per channel `uint8`.
- **Height (nDSM):** ≥0 typical (above-ground), long-tailed distribution (Fig 3 in paper). Invalid values: undocumented — handled as missing file or non-finite warning.
- **Class:** 0=others/background, 1=ground, 2=low vegetation, 3=buildings, 4=water, 5=road, 6=tree.

### Alignment / co-registration
- Paper §3.1: "All the processed data are aligned and cropped into patches". Upstream loader assumes one-to-one alignment via shared `base_name` (`DC_03_26` etc) across `images/`, `heights/`, `classes/`. Manifest enforces this pairing.
- Expected spatial compatibility: per-sample `H×W` identical across modalities (validation checks when files probed).

---

## 4. Dataset organization

### Directory structure (verified via HF siblings listing and `gamus_dataset.py`)
```
<GAMUS_ROOT>/
  images/
    train/  DC_*.RGB.h5   (legacy: *_IMG.h5 at commit 5d04b4d used '*IMG.h5' filter)
    val/    ...
    test/   ...
  heights/
    train/  DC_*.AGL.h5
    val/
    test/
  classes/
    train/  DC_*.CLS.h5
    val/
    test/
```

### Filename patterns (verified via siblings API sample)
- Image: `DC_03_26_RGB.h5` style — `<city>_<id>_<tile>_RGB.h5` (city prefix `DC`, `PHL`, `...` seen). Legacy filter `*IMG.h5` accepted.
- Height: `<base>_AGL.h5` e.g., `DC_03_26_AGL.h5`
- Label: `<base>_CLS.h5` e.g., `DC_03_26_CLS.h5`
- Base / `sample_id`: strip `_RGB.h5` (or `_IMG.h5` / `_CLS.h5` / `_AGL.h5`) → `DC_03_26`. Adapter strips longest suffix first to handle `_RGB.h5` (7 chars) vs `RGB.h5` (6 chars) robustly.
- Pairing logic (upstream): `base_name = img_file[:-6]` (removes `RGB.h5` including dot) → `cls_file = base_name+"CLS.h5"` etc. Implementation mirrors but via `_strip_image_suffix` for robustness.

### Split organization
- Canonical splits: `train`, `val`, `test`. Upstream code accepts `split='train'|'val'|'test'` and sorts `os.listdir(image_dir)` then filters `*.h5`. `val` is the paper's "validation" split; adapter canonicalises aliases `valid`/`validation`/`eval` → `val`.
- Per-split counts (HF verified): train 5004, val 859, test 2861. Paper (pre-filter) counts larger: 6304/1059/4144.

### Sample identity
- Identity is `sample_id` derived from image filename without modality suffix (e.g., `DC_03_26`). This is stable across modalities and filesystem order. Duplicate `sample_id` within same split is an error (validation).

---

## 5. Preprocessing

| Operation | Documented where | Assumption? |
|---|---|---|
| Rasterize LiDAR point clouds → DSM (all points) and DTM (ground points) → nDSM = DSM − DTM | Paper §3.1, Fig 2 | Verified from paper |
| Remove LiDAR noise before rasterization | Paper §3.1 | Verified |
| Rasterize classified point clouds → semantic maps (when land-cover maps unavailable) | Paper §3.1 | Verified |
| Align and crop into `1024×1024` patches | Paper §3.1-§3.2 | Verified |
| Normalization (`Normalize(mean=ImageNet, std=ImageNet)`) | `gamus_dataset.py` example transform for training, not dataset-intrinsic | Example only — not assumed as mandatory preprocessing |
| Resizing to `224×224` | Example transform in `if __name__=="__main__"` | Example only |
| Datatype conversion `Image.fromarray(image.astype(np.uint8))` | `gamus_dataset.py` | Verified |
| Invalid-value handling | No explicit nodata handling in dataloader (no `if height == -9999`); only file-existence check via list of image files | Verified absence; adapter warns on non-finite height |

**Determinism of transforms:** Dataloader example uses `shuffle=True` for train loader (non-deterministic order) but manifest/subset generation is deterministic and independent of that. Resizes/normalizes are deterministic given same input.

---

## 6. Leakage risks

Explicitly investigated (per task §5 requirement):

| Risk | What was checked | Finding |
|---|---|---|
| Duplicate scenes | Searched HF siblings for identical `sample_id` across splits vs within split; siblings listing shows no obvious duplicate filenames across splits (prefix `DC_`, `PL`, etc unique per split counts, but exhaustive cross-split duplicate scan would require full manifest scan — not downloadable at audit time). | **No evidence found** in sampled siblings; manifest validation includes `duplicate_sample_id` error for within-split duplicates. Cross-split leakage cannot be fully verified without full download; adapter validation can be run post-download to detect. |
| Overlapping tiles / scene-level correlation | Paper §3.1: tiles cropped from larger 10,000×10,000 tiles (Zeebruges style) → potential spatial adjacency correlation. Paper §3.2 says tiles collected from 5 cities and split into train/val/test, but split strategy (random vs city-stratified vs spatial) is **not documented** in code or paper excerpt. Upstream dataloader simply reads pre-split directories. | **Could not verify** split stratification. Could not rule out geographic leakage if split is random across cities. Documented as unknown; future validation should check city prefix distribution per split. |
| Geographic leakage | Checked paper for city-wise split: not detailed in accessible excerpt; README does not specify city-to-split mapping. HF siblings show `DC_...` pattern dominates but small samples prevent conclusion. | **Unknown — flagged as limitation**. Recommend post-download analysis: count city prefixes per split. |
| Train/validation leakage | `gamus_dataset.py` sorts image files and does not shuffle before split (splits are pre-materialized directories). | No filename leakage due to sorted deterministic listing, but content leakage (same geographic tile in both splits) **cannot be verified** without full metadata. |
| Filename leakage | Examined suffix patterns; no split leak via filename (no split token inside sample_id). Paths encode split via directory, not filename. | No evidence. |
| Deterministic split risks | Deterministic manifest generation (sorted) eliminates filesystem-order leakage. Dev subset uses hash of `sample_id`, not split order. | Controlled. |

**Overall:** No concrete leakage evidence found in audited artifacts. Two risks **could not be verified** without downloading full dataset: (a) whether train/val/test are city-stratified vs random, (b) whether overlapping tiles from same parent scene were assigned to different splits. Both are documented as assumptions and should be validated once data is acquired (e.g., by checking geo-metadata or city distribution).

---

## 7. Provenance & version pinning

- Do not clone upstream inside DepthWizard tree. Audit used `git ls-remote` + GitHub API + HF API only.
- If a local clone is needed later, clone outside the tracked source tree (e.g. system temp directory), pinned to `6ed44ba87b59911144430ebc0ca02c1f7a1c62b4`, and preserve provenance (do not copy `.git` into DepthWizard).
- Current manifest version: `1.0` (see `src/depthwizard/data/manifest.py:1`).

---

## 8. Known limitations & unverified items

1. Height value range, nodata sentinel, and CRS per tile — undocumented; validation treats missing/invalid via existence + non-finite checks only.
2. Full split stratification by city — undocumented; needs download.
3. Exact file counts differ between paper (11507) and HF distribution (8724) due to post-paper removal of OMA/JAX cities — HF is current truth.
4. H5 internal key (`image` vs `data`) evolved — adapter probes both.
5. Image dtype/dimensions beyond code hints require per-file probing after download.
6. Test split label existence — paper says all tiles annotated, HF shows `classes/test` exists (2861 files), so labels present for test too; but some releases might withhold test labels — manifest keeps `label_path` nullable to handle either.
