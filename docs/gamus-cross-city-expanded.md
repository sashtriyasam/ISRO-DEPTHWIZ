# GAMUS Cross-City Expanded Evidence (S21)

Same protocol throughout (`control-stride-8`, `native-pixel`,
held-out scoring, pooled primary). Selection: first 16 sorted DC
stems + first 16 sorted PHL stems with paired AGL (score-blind);
`manifests/gamus-cross-city-expanded.json`. S19.1-16 confirmed equal
to first-16-sorted DC. Evaluator code was the uncommitted S21 working
tree at main HEAD `6ed623e` (reproduce from branch
`feat/shivam-benchmark-expansion`).

## 32-tile run (16 DC + 16 PHL)

Requested/completed/failed: 32 / 32 / 0. Valid held-out pixels:
29,360,128, coverage 0.875.

| Group          | Samples | Valid px   | MAE (m) | RMSE (m) | R²     |
| -------------- | ------- | ---------- | ------- | -------- | ------ |
| Overall pooled | 32      | 29,360,128 | 4.3970  | 5.8630   | 0.2323 |
| DC pooled      | 16      | 14,680,064 | 6.0529  | 7.6039   | 0.1379 |
| PHL pooled     | 16      | 14,680,064 | 2.7411  | 3.3061   | 0.1973 |

Overall macro: MAE 4.40 / RMSE 5.29 / R² 0.09; median 4.27 m, max
28.40 m. Timing: model load 8.5 s, total ≈ 37 s + bootstrap, ≈ 2.2 s
per sample CPU (observations, not benchmarks).

## Calibration transfer

| Group | Mean scale | Mean offset | Mean residual RMSE |
| ----- | ---------- | ----------- | ------------------ |
| DC    | 0.72       | 6.78        | 7.34               |
| PHL   | 3.89       | −2.13       | 3.25               |

DC fits include negative scales; PHL fits are uniformly positive.
Same pattern as S20 at larger n — the instability persists, still
without causal claim.

## Sample-level bootstrap (MAE, seed 26175, 2000 resamples, 95%)

DC mean MAE 6.05, CI [5.11, 7.05]; PHL mean MAE 2.74, CI [2.38, 3.04];
DC−PHL delta 3.31, CI [2.36, 4.40]. With n=16 per group the method
labels these inferential — the interval excludes zero, so the MAE gap
is descriptively robust at this sample size. This is not a
generalization proof (two cities, tile-level resampling only, no
p-values produced).

## Interpretation

The 2/8/16/32 progression occupies one error family (MAE ≈ 4–7 m,
R² ≈ 0.1–0.2): Philadelphia scores better everywhere measured, and
the gap survives a larger sample. Geographic robustness remains
unproven (two cities, DC_09_29-class outliers unexplained). No model,
checkpoint, preprocessing, calibration, or selection change was made
on these results.

## Limitations

DC+PHL only; NYC-train unused by split discipline; AGL negatives
treated finite; per-sample run-doc timing reflects the resume pass
(original inference timings live in per-sample records); no GPU.
