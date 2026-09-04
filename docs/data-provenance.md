# Data Provenance & License

**DepthWizard — GAMUS foundation — 2026-09-04 (re-verified; original 2026-09-03)**

## Dataset: GAMUS

| Item | Value |
|---|---|
| Dataset name | GAMUS — Geometry-aware Multi-modal Semantic Segmentation Benchmark for Remote Sensing Data |
| Source paper | Xiong et al., arXiv 2305.14914 — https://arxiv.org/pdf/2305.14914.pdf |
| Dataset source (current) | Hugging Face `earthflow/GAMUS` — https://huggingface.co/datasets/earthflow/GAMUS |
| Dataset SHA (HF) | `a3c0e2511f06d909612406f436cf8abb4da805f5` (api `sha`), `lastModified` 2024-09-18T07:17:11Z |
| Legacy dataset URL | `https://syncandshare.lrz.de/dl/fiBpfqvv7QE3MxRC18Uocq/GAMUS.zip` (DFC 2019-derived, includes OMA/JAX, now removed) — referenced in upstream README prior to 2024-08-12 |
| Dataset license | **CC-BY-4.0** (HF `cardData.license = "cc-by-4.0"`, `.gitattributes` + API `tags: ["license:cc-by-4.0"]`). Also visible on dataset viewer header. |
| Redistribution | Permitted with attribution under CC-BY-4.0 (requires credit, license link, indication of changes). Full tiles (≈80 GB) must not be committed to this repo — only manifests/metadata. |
| Attribution | Cite Xiong et al. 2023 (see below) + link to HF dataset + CC-BY-4.0 notice. |
| Citation | See `docs/research/gamus-audit.md: citation` (BibTeX). |
| Modalities | RGB (0.33 m orthophoto), height/nDSM (AGL), semantic label (6+1 classes). See `docs/research/gamus-audit.md: modalities`. |

**Verification:** HF API at `https://huggingface.co/api/datasets/earthflow/GAMUS` returns `cardData.license == "cc-by-4.0"` (checked 2026-09-03 via `python -c urllib`). `XShadow/GAMUS` resolves to same `earthflow/GAMUS` id via API (checked). Siblings listing confirms file structure and counts.

## Code: RSI-MMSegmentation

| Item | Value |
|---|---|
| Repository | `https://github.com/EarthNets/RSI-MMSegmentation` |
| Inspected revision | `6ed44ba87b59911144430ebc0ca02c1f7a1c62b4` — `refs/heads/main`, date 2024-08-12T07:16:44Z |
| License (code) | **None declared.** GitHub API `license == null`, and `LICENSE`/`LICENSE.md`/`LICENSE.txt` absent at HEAD (404). Do **not** infer dataset license = code license. |
| Code license implication | No explicit permission grant found; treat as "all rights reserved" by default. This milestone therefore **prefers an adapter** (no upstream code copied) — only dataloader logic was studied, not vendored. |
| Data-loader file | `gamus_dataset.py` at HEAD (≈70 lines, class `GamusDataset`) — MIT-like informal usage implied but not legally licensed; we do not copy. |

**Inspection method:** `git ls-remote`, GitHub API (`/repos/EarthNets/RSI-MMSegmentation`, `/commits?per_page=...`), and raw fetch of `gamus_dataset.py` (verified key transition `data` → `image` between commits `5d04b4d` and `6ed44ba`).

## Alternate distribution: earthflow/GAMUS (HF)

- Same provenance as above (CC-BY-4.0). The HF distribution is the "new version" per upstream README ("The new version of the GAMUS dataset can be downloaded from ... [XShadow/GAMUS](https://huggingface.co/datasets/XShadow/GAMUS)"). The org-rename `XShadow` → `earthflow` is reflected in HF API (both resolve to `earthflow/GAMUS` record).

## Code reuse from upstream

- **None copied.** The adapter (`src/depthwizard/data/adapter.py:1`) implements the same directory conventions (`images/<split>/*RGB.h5`, `heights/<split>/*AGL.h5`, `classes/<split>/*CLS.h5`) and suffix stripping observed in `gamus_dataset.py`, but is re-implemented from specification, not verbatim copy. No upstream ` .git ` directory vendored, no full repo cloned into `src/`.

## What is committed

- Manifests (`manifests/*.manifest.json`) containing relative paths, sample_ids, checksums — **no raw .h5** (≈80 GB), no `.git/lfs`, no HF cache.
- Schemas, adapter, validation, tests — all fixture-based.

## Action items for future milestones

- Before redistributing any derived dataset artifact, include CC-BY-4.0 attribution block.
- Before copying any upstream code snippet, confirm a LICENSE appears in the repo or obtain permission.
- Keep HF SHA and upstream commit pinned in `docs/research/gamus-audit.md` and update if a new HF commit appears.

## Contacts

- GAMUS authors: Zhitong Xiong et al. (emails via paper).
- Upstream maintainer: `xiongzhitong@gmail.com` (commit author).
