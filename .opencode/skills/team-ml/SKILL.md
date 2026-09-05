# Team ML (DepthWizard)

- Backends implement `DepthBackend.estimate_depth(inspection) →
DepthResult`: relative values, validity, optional confidence,
  preprocessing record, model identity, spatial passthrough,
  provenance. `metric=false`, units None — always.
- Deterministic behavior; robust model loading; checkpoint hash +
  upstream revision + license recorded and separated from the runtime
  record.
- No metric leakage: no metres, CRS, or elevation semantics inside the
  adapter.
- Experiments (GAMUS, adaptation, DA-V3, benchmarks) are
  `type:research`/`type:experiment` under Shravan and conclude with
  evidence notes.
