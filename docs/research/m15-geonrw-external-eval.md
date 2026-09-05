# M15 — GeoNRW Target-Alignment + Frozen M10 External Evaluation

**Date:** 2026-09-05
**Author:** Shravan (ML/data)
**Branch:** `feat/shravan-m15-external-readiness` (separate M15 work; M14 branch untouched)
**Experiment:** `experiments/m15-geonrw-eval` (979 triplets, set sha `012c318944ef205f`)
**Frozen model:** M10 seed-0 `best.pt` (epoch 22, val MAE 5.8204; 98,161 B; head-only state, never modified)
**Outcome: B — external generalization reveals adaptation need.**

---

## Why This Method Was Selected

Evidence, not the M14 suggestion, drove every choice: (1) the probe proved RGB/DEM grids identical (1000×1000 @1 m, same transform/bounds) → **no resampling** of either side; the model emits `out_hw=(1000,1000)` (same weights/preprocessing, interpolation follows source size as in all prior runs) so predictions land exactly on target pixels. (2) The DEM reads 76–136 m absolute (DHHN92) vs M10's nDSM-scale output → direct MAE is datum-offset-dominated (confirmed: diagnostic 97.0 m), so the **established per-image affine research protocol** (M3/M6 `eval/alignment.py`) is the only honest scorer — it measures structural transfer, never metric-nDSM performance. (3) No DTM exists → no DSM−DTM derivation (would fabricate reference). (4) Full 32 GB download exceeded session bandwidth (3.8 GB retrieved); the frozen set = **all 979 complete triplets recoverable**, enumerated sorted with SHA — every tile is out-of-distribution for the GAMUS-only M10 regardless of GeoNRW's train/test split. Formal test-city scoring stays future work.

## 1. Objective

Answer how well the frozen GAMUS-adapted M10 transfers to independent remote-sensing data with a DSM/height target, and what alignment is legitimately required — tied to PS 26175's RGB→DSM/rDSM→3D pipeline, not to MAE-chasing.

## 2. PS Alignment

PS 26175 needs rDSM (PNG/JPG) and metric DSM (GeoTIFF + calibration), weighted 50% DSM accuracy across urban/sparse/hilly/forested scenes. M15 tests the elevation-extraction leg on taf: does M10's structure survive outside GAMUS? A transfer failure here propagates to every downstream stage (calibration cannot fix uncorrelated structure; visualization would render wrong terrain).

## 3. Pre-Implementation Study

PS text (SIH-DepthWizard-2026 README); repo architecture (`adapt/`, `depth/base.py` Rules A/B, `eval/alignment.py`, manifest schema); M14 audit; GeoNRW docs (IEEE DataPort DOI 10.21227/s5xq-b822, `gbaier/geonrw` build scripts, Dataset4EO `collect_data.py`, torchgeo docs); DA-V2 pin currency (upstream HEAD still `a561b84`); CPU-only + 27 GB-free-C constraints. New facts vs M14: RGB JP2 is **4-channel RGBI** (first-3 slicing required); DEM CRS is compound-like (UTM32N + DHHN92); seg taxonomy is 11-class (no crosswalk attempted); torchgeo split `test` = 485 samples = the 3 M14 test cities.

## 4. GeoNRW Source Verification

`torchgeo/geonrw` @ `eeb5fc3e7ea78dc69299658491419212546fd4dd` (`nrw_dataset.tar.gz`, ~32.4 GB; partial stream retrieved to ignored `D:/geonrw_data/`, dl-de/by-2.0, cite Baier et al. + NRW open-data program). Triplet layout `<city>/<E>_<N>_{rgb.jp2,dem.tif,seg.tif}` confirmed on real bytes; filenames encode UTM32N coordinates (e.g. `368_5702` = 368000E/5702000N).

## 5. Target-Semantics Verification

**GeoNRW target = absolute DSM** (first-return LiDAR surface elevation, meters, DHHN92 vertical datum — compound CRS on real files). NOT nDSM/AGL. GAMUS = nDSM/AGL. DA-V2 = relative camera depth. Absolute terrain (DTM) appears nowhere in the triplet. Unflagged-fill check: exact-0.0 pixels are 1.3e-8 of 979M valid — negligible. Per-city target means 80–160 m vs M10 prediction means ~0–45 m scale: the quantities differ by construction.

## 6. Sample/GeoTIFF Probe (`bochum/368_5702`)

RGB 1000×1000×4 uint8 / DEM 1000×1000 float32 (nodata −9999, 100% finite here, 76.78–135.84 m, mean 101.73) / seg 1000×1000 uint8 (classes {1,3,4,5,7,9,10}). All three share CRS family (EPSG:25832; DEM adds DHHN92 height), identical 1 m transform/bounds. Correspondence exact; no resampling justified.

## 7. Alignment Method

Grids already coincide → no resampling. Model output pinned to source grid (`out_hw=(1000,1000)`; infrastructure-only, same weights). Scoring = per-image least-squares `target ≈ a·pred + b` + Pearson/Spearman on finite∩valid pixels (established protocol); nodata→NaN excluded; negatives kept. Direct MAE reported once as a datum-offset diagnostic.

## 8. M10 Frozen Configuration

DA-V2-Small pin 03876f86 (upstream `a561b84`), tap `output_conv1`, 23,201-param head from `best.pt` (`extra: {epoch: 22, mae: 5.8204}`, 98,161 B, unmodified), TargetScale zscore mu=8.037330237035235/sigma=10.304011604437477, input_size 518, CPU. No retraining, no tuning, no checkpoint selection on GeoNRW (one-shot).

## 9. External Evaluation Protocol

Frozen set: all 979 complete (rgb, dem) triplets under `D:/geonrw_data/triplets`, sorted, SHA `012c318944ef205f` (bochum 184, coesfeld 177, gelsenkirchen 137, guetersloh 148, herford 111, paderborn 222). Per-triplet affine + correlations → per-city macro + pooled micro. Single frozen report.

## 10. Results

| City | n | Aligned MAE | Aligned RMSE | Pearson | Spearman | Direct MAE (diag) |
|------|---:|---:|---:|---:|---:|---:|
| bochum | 184 | 8.42 | 10.56 | 0.22 | 0.21 | 101.67 |
| coesfeld | 177 | 4.79 | 6.30 | 0.29 | 0.21 | 82.11 |
| gelsenkirchen | 137 | 5.66 | 7.29 | 0.24 | 0.22 | 51.37 |
| guetersloh | 148 | 3.74 | 5.21 | 0.38 | 0.32 | 78.61 |
| herford | 111 | 9.07 | 11.19 | 0.15 | 0.12 | 106.41 |
| paderborn | 222 | 7.41 | 9.34 | 0.23 | 0.20 | 161.84 |
| **macro** | **979** | **6.51** | **8.31** | **0.25** | **0.21** | **97.00** |
| micro aligned MAE | | **6.51** (979M valid px) | | | | |

Mean affine slopes 0.56–0.87 (all < 1): M10's relief is systematically over-amplified vs real DSM. Internal reference: M10 GAMUS-val Pearson 0.57 → external 0.25.

## 11. Height/Error Analysis

Aligned MAE (6.51) is not comparable to GAMUS MAE (different quantities — stated once, clearly). The informative contrasts: Pearson more than halves (0.57→0.25); slopes compress (~0.6); direct MAE (~97) is pure datum offset. Best city (guetersloh, 0.38) still trails M10's worst internal behavior; several tiles show near-zero/negative Pearson (structure not detected). No class analysis (no defensible GAMUS↔GeoNRW crosswalk — classes never equated).

## 12. Geographic Analysis

Spread across 6 unseen German cities (aligned MAE 3.7–9.1, Pearson 0.15–0.38) with no city approaching internal performance — a genuine domain gap, not a single-city artifact. Macro≈micro (6.51/6.51) → gap is systematic, not driven by outliers. Formal test-city (duesseldorf/herne/neuss) scoring still requires the full download.

## 13. Limitations / Comparability Caveats

Affine metrics measure structure, not metric performance; 6 train-split (not formal test-split) cities; `out_hw` operating-point shift (1000 vs 1024) is interpolation-only; CPU; M10 seed-0 only (three-seed external spread unknown); RGBI→RGB first-3 slicing assumes band order (verified means, documented); target extremes to 511 m accepted as-file.

## 14. PS Impact

**Decreases confidence** that GAMUS-only M10 directly supports DSM generation (structure transfer is weak: 0.25). **Increases confidence** in the Path-A/Path-B framing: relative output runs on any RGB (Path A viable now); metric DSM needs the calibration stage + adaptation, exactly as architected. Visualization track implication: meshes textured from M10 heights would inherit the compressed/offset relief — flythrough geometry needs the adapted+calibrated model, not this checkpoint.

## 15. Outcome

**Outcome B — external generalization reveals adaptation need.** M10 runs correctly end-to-end on real third-party data, but the domain gap is meaningful. The quantities differ (DSM vs nDSM), so this is not a "worse MAE" verdict — it is a transfer-structure verdict.

## 16. Recommended Next Milestone

Exactly ONE: **M16 = controlled GeoNRW adaptation probe** — freeze the M15 protocol + semantics, then test whether *small, fixed-budget* head adaptation on GeoNRW train cities (never test cities) recovers structural correlation, with the affine Pearson (not raw MAE) as the selection metric. Do NOT start it here.

---

## Artifacts

- `experiments/m15-geonrw-eval/` (config/results/README; per-triplet affine metrics, set SHA, checkpoint provenance)
- `src/depthwizard/experiments/m15_geonrw_eval.py` (loader + evaluator; no shared-interface changes)
- `tests/test_m15_geonrw_eval.py` (8 tests, passing)
- `docs/research/m15-geonrw-external-eval.md` (this document)

Reproducibility: triplet set SHA `012c318944ef205f` + commands above; `rasterio` (+ `pyproj` for the CRS check) required; data stays in ignored `D:/geonrw_data/` (dl-de/by-2.0; cite Baier et al.).

---

**Prepared by:** Shravan (ML) · **Date:** 2026-09-05 · **Branch:** `feat/shravan-m15-external-readiness`
