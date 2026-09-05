# Evaluation Significance Methodology (S21)

## Unit of resampling

The tile/sample — never the pixel. Correlated pixels are not
independent observations, so pixel-level resampling is refused by
design. Uncertainty statements describe generalization across images,
not measurement precision within them.

## Method

Deterministic percentile bootstrap (NumPy only, no scipy):
`--seed` (default 26175), `--resamples` (default 2000), `--confidence`
(default 0.95). Single-group mean intervals (`sample-bootstrap`) and
unpaired two-group mean differences (`two-sample-bootstrap`) over
per-sample MAE. Every output records method, seed, resample count,
confidence, exact group counts, and a power flag.

## Power rule

Groups below 10 samples are labelled `descriptive only
(underpowered for robust inference)`; at or above, `inferential
interval`. No p-values are produced. Pairwise city comparisons at
current breadth need no multiplicity treatment (one pre-declared
comparison); revisit if groups multiply.

## Reading the S21 output

DC−PHL MAE delta 3.31, 95% CI [2.36, 4.40], n=16/16: the gap is
descriptively robust at this sample size — it excludes zero under the
documented resampling. It is not a generalization proof, not a causal
claim, and not a significance star: two cities, tile-level
resampling only.

## Limitations

Small-n intervals are wide by construction; bootstrap assumes the
sample represents the population (two cities cannot); calibration
controls are never resampled as evaluation observations; intervals
describe the observed population, not future geographies.
