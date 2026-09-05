# DepthWizard — Research vs Product

## Rule

Research results must **not** automatically become product claims.
Promotion requires passing through the product integration path with
acceptance evidence.

## RESEARCH (`type:research`, `type:experiment`)

- GAMUS experiments, cross-city robustness, scaleout runs
- Benchmark comparisons, model adaptation, loss experiments
- Alternative model evaluation ( incl. DA-V3 decision ), M14
  target-semantics audit
- Remote-sensing robustness studies, significance designs

Research issues live under Shravan's track (`ml`), record dataset
manifest + checkpoint hash + config, and conclude with an evidence
note — never with a product status flip.

## PRODUCT (`type:feature`, `type:integration`, `type:test`)

- Model **runtime** integration behind the frozen `DepthBackend`
- Calibration, DSM/rDSM, mesh, export
- Desktop integration, 3D, UX, deployment
- Regression tests guarding promoted behavior

## Promotion protocol (research → product)

1. Research issue closes with evidence (numbers + config + provenance).
2. A separate product issue adopts the result, naming the exact
   integration point (backend adapter, calibration, eval gate…).
3. Product tests + verification recorded; only then does any Project
   item move toward Done.
4. The Project `Track`/`SIH Area` on the product item reflects where
   the behavior now lives, not where it was discovered.

## Current applications

- S19/S19.1/S20/S21 GAMUS findings: **research signal**, not SIH
  validation. They do not satisfy R12 or GATE 8.
- DA-V2 Small **runtime** (loads, runs deterministically, provenance
  recorded): legitimately product-side (GATE 3), because the claim is
  "it runs", not "it is accurate".
- Any future accuracy claim (DA-V3, adaptation, tuning) starts as
  research and must re-earn product status via this protocol.
