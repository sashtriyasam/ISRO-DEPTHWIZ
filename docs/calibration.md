# DepthWizard — Calibration Engine (Shivam S9)

Independent deterministic affine calibration: scale-ambiguous relative
values → metric reference via `reference = scale * predicted + offset`.
No rasters, models, services or desktop knowledge.

## Path

```text
relative values
      ↓ CalibrationSamples (paired, validated structure)
ScaleOffsetCalibrator  (Calibrator protocol)
      ↓ CalibrationResult (scale, offset + residual evidence)
apply_calibration(values, result)  →  metric-valued derived samples
```

## Method

Ordinary least squares, closed form (`a = Sxy/Sxx`, `b = ȳ − a·x̄`),
all sums via `math.fsum` (exactly-rounded, deterministic). NumPy
2.5.0 / SciPy 1.18.0 / scikit-learn 1.9.0 are present in the
environment but were evaluated and rejected: normal equations on
small sample sets need nothing beyond compensated sums, and a hard
numerical runtime dependency for `y = a·x + b` would violate the
dependency-light principle. No new runtime dependency was added;
no ML framework; nothing vendored.

`CalibrationMethod` exposes only `SCALE_OFFSET` — the one implemented
method. No Huber/RANSAC placeholders. `Calibrator` is a small protocol
(`method` + `calibrate`) so future robust variants substitute without
changing callers.

## Sample contract

`CalibrationSamples` (frozen, tuple-based): predicted/reference value
pairs of equal length, optional `valid_mask` (False = deliberately
excluded, counted in `total_samples` but not fitted), mandatory
`reference_id`, explicit `reference_units` (must be `"meters"`),
`target_semantics` restricted to the metric meanings
(`HEIGHT_AGL_NDSM`, `ABSOLUTE_ELEVATION_DSM`). Optional reference
checksum and source input id/checksum. Structural violations fail at
construction (`ValidationError`, same style as `DepthResult`).

Non-finite values are rejected at fit time (`CalibrationError`
naming index and role) — they signal data-integrity problems, not
things to average away. Points excluded via `valid_mask` are the
only silent-free exclusion path, and the result reports
`valid_samples` vs `total_samples`.

## Minimum-sample policy

`MIN_VALID_SAMPLES = 3`: two points determine a line but leave zero
residual degrees of freedom, making RMSE/MAE/max/R² vacuous. Three
gives one degree of freedom so the residual evidence means
something. No broader scientific-adequacy claim is made.

Degenerate predictors (zero variance among valid samples) raise
`CalibrationError` — scale is undefined, no division by zero, no
silent NaN. Fitted parameters are finiteness-checked and never
rounded.

## Result and residuals

`CalibrationResult` (frozen): method, scale, offset, reference
id/checksum/units, target semantics, total/valid counts, RMSE, MAE,
max absolute residual, R² (`1 − SSres/SStot`; constant reference →
1.0 if perfect else 0.0), engine version, source linkage.
`to_provenance()` builds the shared `ProductProvenance` record
(method, reference, `(scale, offset)` params, units, meaning,
engine, source) — reuse, not a second provenance system.
`generated_at` stays None: timestamps would break determinism.

Residual metrics are evidence of fit quality on the calibration
samples — not model confidence, not accuracy claims. No percentages
are invented.

## apply_calibration

Pure `scale * value + offset` over any sequence: deterministic, no
mutation (new tuple), cardinality preserving (empty → empty),
rejects non-finite inputs and non-finite outputs (overflow) with
index-naming `CalibrationError`. No raster/GeoTIFF writing; the
source `DepthResult` is never touched and never converted.

## Semantics (critical)

Calibration is NOT elevation semantics. Before: `RELATIVE`, no metre
claim. The result carries the metric _reference_ relationship plus
the caller-declared target meaning. The later S10 layer consumes a
validated `CalibrationResult` to construct AGL/nDSM/DSM products —
this task creates no `HeightProduct` and mutates no `DepthResult`.

The affine map is empirical (`predicted scalar → metric reference`);
no physical depth-vs-height interpretation is encoded. Reference
units must be explicit metres, or no metric calibration is produced.

## Errors

`CalibrationError` for: too few valid samples, non-finite values,
zero predictor variance, non-finite fit/output, non-numeric apply
input. `InsufficientGCPsError` is NOT used — these are generic
samples, not GCPs. Messages state counts, indices and causes.

## Future robust methods

Implement `Calibrator` (Huber/RANSAC/local correction) behind the
same `calibrate()` boundary; add the method enum member when the
implementation lands. No GCP extraction, DEM alignment/loading/
resampling, or terrain correction here — this engine receives
already-paired scalars.
