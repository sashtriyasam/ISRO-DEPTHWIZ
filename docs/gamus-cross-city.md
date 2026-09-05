# GAMUS Cross-City Evidence (S20)

Identical protocol to S19/S19.1 (`control-stride-8`, `native-pixel`,
held-out scoring, pooled primary). Only geography changed. City codes
follow the dataset's documented tile prefixes: DC = Washington DC,
PHL = Philadelphia (M9 research composition tables). The test split
contains no other city (OMA/JAX removed upstream; NYC exists only in
train, not used — split discipline preserved).

## Design

`manifests/gamus-cross-city.json`: 8 DC stems reused from
`gamus-eval-8` + first 8 sorted PHL stems with paired AGL (score-blind
selection). Requested/completed/failed: 16 / 16 / 0. Valid held-out
pixels: 14,680,064, coverage 0.875. Evaluator code was the uncommitted
S20 working tree at main HEAD `6ed623e`.

## Comparison

| Group          | Samples | Valid px   | Coverage | MAE (m) | RMSE (m) | R²     |
| -------------- | ------- | ---------- | -------- | ------- | -------- | ------ |
| Overall pooled | 16      | 14,680,064 | 0.875    | 4.7880  | 6.3896   | 0.2204 |
| DC pooled      | 8       | 7,340,032  | 0.875    | 6.5096  | 8.2713   | 0.1603 |
| PHL pooled     | 8       | 7,340,032  | 0.875    | 3.0665  | 3.6387   | 0.1462 |

Overall macro: MAE 4.79 / RMSE 5.76 / R² 0.10; median 4.66 m, max
24.93 m. Timing: model load 9.2 s, total 34.5 s, ≈ 2.2 s/sample CPU.

## Calibration transfer

| Group | Mean scale | Mean offset | Mean residual RMSE |
| ----- | ---------- | ----------- | ------------------ |
| DC    | −0.52      | 7.97        | 7.89               |
| PHL   | 3.89       | −1.35       | 3.63               |

DC fits include negative scales on several tiles (inverse
depth↔height mapping under an unconstrained affine fit); PHL fits are
uniformly positive. Calibration varies strongly by geography while
held-out errors track residuals within each city — the instability is
in the mapping, consistent with monocular scale ambiguity rather than
a calibration-procedure defect. No causality asserted.

## Interpretation

No degradation outside DC was observed — Philadelphia scores better
on every headline metric. That is a two-group observation, not a
robustness proof: R² stays low in both groups, per-tile variance is
large (DC 3.10–9.74 m MAE; PHL 2.51–3.30 m), and only two cities are
represented. DC_09_29 (R² 0.47) remains an unexplained favorable
outlier, reported as-is. The DC-8 subset reproduces the S19.1 8-tile
numbers exactly (MAE 6.5096 / RMSE 8.2713 / R² 0.1603), confirming
rerun reproducibility.

No model, checkpoint, preprocessing, calibration, or selection change
was made on the basis of these results.

## Limitations

Two cities only; NYC-train tiles deliberately unused; AGL negatives
treated finite; no statistical significance testing; no GPU; evaluator
working tree uncommitted at run time (reproduce from branch
`feat/shivam-cross-city-benchmark`).
