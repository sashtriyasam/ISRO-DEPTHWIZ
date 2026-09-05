# Scientific Evaluation Protocol (S19)

## Principle

Raw relative depth is never compared to metric elevation. The valid
path is relative prediction + explicit metric controls → calibrated
metric product → metric evaluation. Engineering pipeline validity
(tests pass, stages complete) is distinct from scientific accuracy
(held-out metres); this harness measures the latter.

## Calibration / evaluation separation

`control-stride`: every 8th valid pixel (deterministic, never chosen
by test error) fits the affine map; only the remaining pixels score.
Control pixels are excluded from evaluation by construction. Using the
same reference set for fit and score is therefore labelled a
calibration/evaluation protocol — not independent generalization
evidence. Cross-sample (`sample-split`) evaluation is supported by
running the CLI per sample with disjoint roles.

## Metrics (metres, held-out pixels only)

MAE, RMSE, pooled R² (with the constant-reference 1.0/0.0 convention),
median and max absolute error. Valid pixel = predicted finite AND
reference finite AND reference valid; NaN/nodata/inf are excluded and
counted, never zeroed. Each result reports valid/invalid counts and
coverage (coverage describes coverage, not accuracy).

## Aggregation

Primary: pooled scoring over concatenated held-out pixels. Macro
(per-sample means) is reported alongside as the typical-sample view.
Per-image RMSE values are never blindly averaged as the headline.

## Alignment

GAMUS tiles are pixel-native (no CRS): prediction and reference shapes
must match exactly (`native-pixel`, no resampling). CRS-backed rasters
must share CRS and shape (`compatible`); anything else is refused
(`GRID_MISMATCH`) unless an explicitly declared reprojection step is
added later. Interpolated values are never called ground truth.

## Reproducibility

Every result records repository SHA, dataset release, manifest
checksum, input/reference checksums, model + checkpoint SHA-256 +
upstream revision, device, Python/dependency versions, calibration
method/params, alignment method, and metric protocol. Summaries are
JSON-safe (no arrays, no prediction dumps).

## Leakage, units, semantics

No silent DSM↔nDSM/AGL conversion (target must equal the reference
meaning). Metric evaluation requires metres. CRS/transform/units
mismatches are refused, not converted.

## Observed field evidence (2 GAMUS test tiles, DC, real DA-V2 Small)

Pooled held-out: MAE 7.16 m, RMSE 8.87 m, R² 0.08, coverage 0.875
(1,835,008 valid pixels; control-stride-8; CPU). Per-sample: DC_03_26
MAE 9.32 / RMSE 10.85 / R² 0.01; DC_05_28 MAE 5.01 / RMSE 6.29 /
R² 0.01. Calibration residuals match held-out errors, so model error
dominates. Recorded honestly per research-result policy: no tuning,
no model changes. This is a two-tile smoke, not a benchmark claim —
see limitations below.

## Scale-out (S19.1, same protocol)

Deterministic first-N selection (`--max-samples`/`--sample-offset`
over manifest order), one model load per run, scalar-accumulator
pooling (O(1) memory), per-sample resume records with exact identity
gates, strict-by-default failure accounting
(requested/completed/failed), per-phase timing observations, city
grouping from manifest labels. Results: `docs/gamus-scaleout.md`
(8 tiles: MAE 6.51 / RMSE 8.27 / R² 0.16; 16 tiles: MAE 6.05 /
RMSE 7.60 / R² 0.14) — same error ballpark as the smoke, DC-only.

## Cross-city grouping (S20, reporting only)

Runs may carry per-city pooled metrics (`by_city_pooled`, exact
accumulator math per manifest city label) and per-city calibration
summaries (mean scale/offset/residual, control counts) alongside the
overall pooled headline. Grouping never changes scoring, selection,
or aggregation rules; labels come from manifest source metadata, never
inferred geography.

## Significance and batch execution (S21)

Sample-level percentile bootstrap over per-sample MAE (deterministic
seed, default 2000 resamples, 95% confidence; NumPy only, no p-values;
groups below 10 samples labelled descriptive-only). Batch runs share
one model load, fold scalar accumulators (O(1) memory), write
per-sample resume records under exact identity gates, and aggregate
shards via `--aggregate-resume` without re-inference. See
`docs/evaluation-significance.md`.

## Limitations

Two tiles cannot represent geographic robustness; no GPU measurement;
no labelled-benchmark comparison (protocols would differ); AGL
negatives treated as finite (no documented nodata marker); 1024² CPU
inference is slow (~1 min/tile), so large splits need batch planning.
