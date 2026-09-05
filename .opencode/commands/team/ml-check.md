# /team:ml-check

Gate ML/model work. Respect `AGENTS.md`. Owner: Shravan's track.

1. Contract: does the backend implement `DepthBackend.estimate_depth`
   with relative-only output (`metric=false`, units None), validity,
   optional confidence, preprocessing record, model identity, spatial
   passthrough, provenance?
2. Determinism: fixed config → fixed output? Model loading robust?
3. Provenance: checkpoint hash + upstream revision + license recorded,
   separated from the runtime record?
4. No metric leakage: no metres, no CRS, no elevation semantics inside
   the adapter (target semantics stay an explicit `ElevationSemantics`,
   never inferred).
5. Research vs product: experiments conclude with evidence notes, not
   product status flips (`docs/project/RESEARCH_VS_PRODUCT.md`).
