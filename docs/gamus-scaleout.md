# GAMUS Scale-Out Evidence (S19.1)

Same protocol as S19 (`control-stride-8`, `native-pixel`, held-out
scoring, pooled aggregation); only the subset grew. Selection rule for
both manifests: first N sorted RGB stems with paired AGL (no score
knowledge). All tiles are Washington DC: geographic diversity remains
unverified. Evaluator code was the uncommitted S19.1 working tree at
main HEAD `6ed623e` (recorded repo SHA alone does not capture that;
reproduce from branch `feat/shivam-benchmark-scaleout`).

## 8-tile run (`manifests/gamus-eval-8.json`)

Requested/completed/failed: 8 / 8 / 0. Valid held-out pixels:
7,340,032, coverage 0.875.

| Metric   | Pooled | Macro  |
| -------- | ------ | ------ |
| MAE (m)  | 6.5096 | 6.5096 |
| RMSE (m) | 8.2713 | 7.8830 |
| R²       | 0.1603 | 0.0746 |

Macro median absolute error 6.49 m, macro max 27.79 m. Timing
(engineering observations): model load 8.8 s, total 16.3 s,
≈ 2.0 s/sample CPU. Per-sample MAE ranges 3.10–9.74 m; one tile
(DC_09_29) reaches R² 0.47, the rest ≤ 0.05 — reported, not selected.

## 16-tile run (`manifests/gamus-eval-16.json`)

Requested/completed/failed: 16 / 16 / 0. Valid held-out pixels:
14,680,064, coverage 0.875.

| Metric   | Pooled | Macro  |
| -------- | ------ | ------ |
| MAE (m)  | 6.0529 | 6.0529 |
| RMSE (m) | 7.6039 | 7.3351 |
| R²       | 0.1379 | 0.0542 |

Macro median 6.03 m, macro max 26.99 m. Timing: model load 9.2 s,
total 37.3 s, ≈ 2.3 s/sample CPU. Resume rerun reproduced identical
pooled metrics without re-inference.

## Interpretation

The 2-tile smoke (MAE 7.16 / RMSE 8.87 / R² 0.08), 8-tile, and 16-tile
results occupy the same error ballpark: model error dominates
(calibration residuals track held-out errors per sample), and R² stays
near zero. The larger sample confirms the smoke's suggestion instead
of overturning it — that stability is the finding. No tuning was
performed; per-tile variance (including the DC_09_29 outlier) is
reported as-is for Shravan's research track.

Macro-vs-pooled RMSE differs (7.34 vs 7.60 at 16 tiles), confirming
pooled-pixelwise as the primary headline. Memory stays O(1) in pixels
(scalar accumulators); one model load serves the whole run.

## Limitations

DC-only geography; 16 tiles are stronger evidence than 2 but not an
SIH-wide accuracy claim; AGL negatives treated as finite; no GPU;
no cross-dataset comparison.
