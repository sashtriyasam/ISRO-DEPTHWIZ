# DepthWizard — Integration Contract

Boundary: Python scientific backend ↔ desktop frontend.
Details: `docs/canonical-integration.md`,
`docs/artifact-transport.md`, `docs/service-client.md`,
`docs/production-backend-readiness.md`.

## Data flow

```text
depthwizard.pipeline (PipelineRunner / run_relative_path)
  → depthwizard.integration (canonical adapter)
  → transport (artifact transport / local service)
  → SceneArtifact (elevation grid + mesh + metadata/provenance)
  → Three.js viewer (src/viewer, src/scene via transport client)
```

## Artifact rules

1. **Metric-only terrain validation at the transport boundary.**
   Relative depth is validated separately and never passes metric
   validation by relabeling.
2. **Adapter transparency.** The canonical adapter must not
   recalibrate, rerasterize, resample, reproject, remesh, reinterpret
   semantics, or change units. Any such change requires an explicitly
   accepted architectural amendment to `docs/sih-architecture.md`.
3. **Source linkage is checksum-enforced** (pipeline → calibration →
   product), so provenance survives the boundary.
4. **Scene generation inputs:** elevation grid + mesh + metadata /
   provenance; viewer must surface model identity and metric-vs-relative
   status to the user (see `docs/metadata.md`).

## Ownership at the boundary

| Segment                                          | Owner   |
| ------------------------------------------------ | ------- |
| Pipeline output shape                            | Shivam  |
| Canonical adapter + transport + local service    | Shivam  |
| Transport consumption, scene creation, rendering | Aryan   |
| `DepthBackend` plug-in behind the pipeline       | Shravan |

## Change protocol

1. Propose contract change as an issue (`type:integration`) citing
   the exact section of this contract.
2. Update contract doc + both sides (producer/consumer) + tests in the
   same change or in explicitly linked issues.
3. No consumer-side silent compensation for producer changes.
