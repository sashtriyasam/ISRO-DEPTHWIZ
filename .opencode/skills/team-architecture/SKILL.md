# Team Architecture (DepthWizard)

- Authority: `docs/sih-architecture.md`; mirror:
  `docs/project/MASTER_PLAN.md`.
- Two paths only: Path A (PNG/JPG → rDSM → mesh → viewer, relative,
  no CRS) and Path B (GeoTIFF → calibration → metric DSM → mesh →
  viewer, CRS preserved).
- `DepthBackend.estimate_depth` shape is frozen; M14 informs fields
  only. Target semantics stay an explicit `ElevationSemantics`, never
  inferred.
- Boundary crossings go through `docs/project/INTEGRATION_CONTRACT.md`
  with producer + consumer + tests updated together.
