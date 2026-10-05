# DepthWizard documentation index

Many documents here were written as point-in-time records (milestones,
release gates, acceptance runs). When two documents disagree, the
**canonical** source below wins; everything listed as *historical*
describes the state at the time it was written and is not updated.

## Canonical (kept current)

| Topic | Source |
| :--- | :--- |
| Capabilities, PS 26175 matrix, known limitations | [../README.md](../README.md) |
| Project status and release state | [project/PROJECT_STATUS.md](project/PROJECT_STATUS.md) |
| Plan, ownership, release gates | [project/MASTER_PLAN.md](project/MASTER_PLAN.md), [project/TEAM_OWNERSHIP.md](project/TEAM_OWNERSHIP.md), [project/RELEASE_GATES.md](project/RELEASE_GATES.md) |
| Research vs product promotion | [project/RESEARCH_VS_PRODUCT.md](project/RESEARCH_VS_PRODUCT.md) |
| Calibration engine and calibration sources | [calibration.md](calibration.md) |
| Installer, managed runtime, checkpoint verification | [runtime-provisioning.md](runtime-provisioning.md) |
| Evaluation protocols (control-stride vs sparse-controls) | [evaluation-protocol.md](evaluation-protocol.md), [evaluation-significance.md](evaluation-significance.md) |
| Subsystem references | [ingestion.md](ingestion.md), [geospatial.md](geospatial.md), [dem-reference.md](dem-reference.md), [dsm-engine.md](dsm-engine.md), [mesh-engine.md](mesh-engine.md), [geotiff-export.md](geotiff-export.md), [pipeline.md](pipeline.md), [local-service.md](local-service.md), [service-client.md](service-client.md), [artifact-transport.md](artifact-transport.md), [desktop-host.md](desktop-host.md), [camera-modes.md](camera-modes.md), [flythrough.md](flythrough.md), [rendering-modes.md](rendering-modes.md) |

## Historical records (not updated)

Release and acceptance snapshots: `RELEASE_ARTIFACT_RECORD.md` (signed RC1
installer), `SCIENTIFIC_EVIDENCE_PACKAGE.md` (RC1), `final-release-gate.md`,
`final-release-status.md`, `final-sih-compliance.md`,
`final-system-acceptance.md`, `final-ml-candidate.md`, `release-witness.md`,
`release-blockers.md`, `release-sync.md`, `native-release-acceptance.md`,
`windows-release-acceptance.md`, `phase5-acceptance.md`, `milestone-01.md`,
`dav2-*-acceptance.md`, `dav2-level3-evidence.*`, `sih-compliance-matrix.md`,
`sih-authoritative-requirement-audit.md`.

Integration and planning notes: `aryan-*.md`, `shravan-dav2-integration.md`,
`upstream-audit-shivam.md`, `canonical-integration.md`, `project-session.md`,
`production-backend-readiness.md`, `installer-strategy.md`,
`native-host.md`, `native-runtime-packaging.md`, `windows-code-signing.md`,
`github-branch-protection.md`, `m17-product-promotion.md`,
`ps-*-gap.md` / `ps-*-closure.md`, `neural-rendering-decision.md`,
`gamus-*.md`, `FINAL_SIH_DEMO_GUIDE.md`, `SIH_SUBMISSION_PACKAGE.md`.

Several historical records predate fixes that changed behaviour (for
example, metric output now requires a DEM/GCP reference, and the RGB
texture, slope layer and DSM export are delivered); check the canonical
sources before quoting them.
