# /team:integration-check

Gate backend↔desktop boundary work.
Respect `AGENTS.md` + `docs/project/INTEGRATION_CONTRACT.md`.

1. Name the exact contract section being exercised or changed.
2. Adapter transparency: no recalibration, rerasterization,
   resampling, reprojection, remeshing, semantic reinterpretation, or
   unit change. Any exception needs an accepted architectural
   amendment first.
3. Metric-only terrain validation at the boundary; relative depth
   validated separately.
4. Both sides updated together (producer + consumer + tests) or linked
   issues exist for the follow-up.
5. Evidence: end-to-end run (Path A and/or Path B) recorded, plus
   integration tests green.
