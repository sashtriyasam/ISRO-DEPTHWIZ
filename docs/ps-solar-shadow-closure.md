# PS Closure — Solar-Shadow Geometry / Trigonometry (SIH 26175)

**Date:** 2026-09-06
**Author:** Shivam (Architecture + Scientific Acceptance Authority)
**Main audited:** `809801d45ac7f3be857b284539e4d9028e914e09`
**Status:** REQUIREMENT ANALYSIS + MINIMUM-SCOPE DESIGN. No implementation performed.

---

## 1. What the SIH PS Requires (established, not assumed)

The externally supplied PS description references height estimation aided by **solar shadow geometry / trigonometry** on a single optical monocular satellite image. Taken literally, the requirement is:

> From one sun-lit optical image, recover structure heights from the geometry of cast shadows using known solar position — i.e. `height = shadow_length × tan(solar_elevation)`, with shadows correctly attributed to their casting structures.

"Shadow support" as a vague term is rejected. The requirement decomposes below; every element must be satisfied for an honest compliance claim.

## 2. Required Inputs

| Input                       | Source                                                                   | Units         | Mandatory?     |
| --------------------------- | ------------------------------------------------------------------------ | ------------- | -------------- |
| RGB scene                   | `InputInspection` (existing)                                             | uint8 HWC     | Yes            |
| Solar elevation angle       | image metadata, else acquisition time + lat/lon via solar-position model | degrees       | Yes            |
| Solar azimuth angle         | image metadata, else time + lat/lon model                                | degrees       | Yes            |
| Ground sampling distance    | GeoTIFF transform (Path B) or explicit scale reference                   | m/px          | Yes for metres |
| Shadow mask                 | new segmentation step                                                    | boolean grid  | Yes            |
| Building↔shadow association | new association rule                                                     | index mapping | Yes            |

## 3. Required Outputs

`SolarShadowHeightSamples`: per-structure height estimates + validity flags + full provenance (sun-angle source, segmentation method/version, association rule, GSD source). Consumable as one more reference type into the existing `CalibrationSamples` path — never a direct DSM overwrite.

## 4. Sun-Position Requirements

Elevation + azimuth per scene, with recorded source (metadata vs computed). Computed positions additionally require acquisition timestamp + scene lat/lon; if none of {metadata angles, timestamp + location} exist, the method is **inapplicable — refuse, never assume angles**.

## 5. Geometry Requirements

Association runs along the solar azimuth axis; each shadow must be linked to its casting structure; ambiguous links are rejected, not guessed. Flat local ground is assumed only after a DEM check (or explicit refusal on terrain).

## 6. Time/Date Requirements

Needed if and only if sun angles are computed rather than read from metadata (see §4). Timestamp must be acquisition time (not processing time), with timezone handling recorded.

## 7. Camera/Image Requirements

Single optical monocular view (satisfied by existing ingestion). Off-nadir viewing geometry, if significant, must enter the projection (shadow offset direction ≠ pure solar azimuth otherwise) or be bounded as an error term.

## 8. Coordinate Requirements

Pixel grid aligned to image axes; uniform GSD (checked, not assumed); association distances measured in pixels then converted via GSD. Non-georeferenced PNG/JPG without GSD can yield **at most a dimensionless shadow-ratio diagnostic — never metres**.

## 9. Trigonometric Computation Required

Per associated pair: `height_m = shadow_length_px × GSD_m_per_px × tan(solar_elevation)`. One formula, exact on synthetic fixtures; every other component is about earning the right to apply it (valid shadow, valid association, valid GSD, valid angles).

## 10. Is Geometric Shadow Estimation Alone Enough?

**No.** A bare shadow-length estimator without segmentation validation, association discipline, GSD grounding, and calibration integration produces numbers without meaning — precisely the fabrication AGENTS.md forbids. Segmentation + association + calibration-reference treatment are all required before any height claim.

## 11. Relation to Single-View Height Estimation

Solar-shadow heights are an **independent reference leg**, parallel to DA-V2 relative depth: both are non-metric until the existing calibration layer maps them to metres. They strengthen (never bypass) the calibration gate.

## 12. Relation to Final 3D Reconstruction

Solar heights enter only via `CalibrationSamples` → metric DSM → mesh. They change no mesh, texture, or renderer code.

## 13. Classification

**C — MAJOR NEW SUBSYSTEM.** Zero implementation exists in `src/` (verified search); sun-metadata sourcing, validated segmentation, association logic, and calibration integration jointly constitute new R&D, not a patch.

## 14. Minimum Viable Compliance Design

New `depthwizard.solar` package (Shivam-owned): sun-resolution → shadow segmentation → azimuth association → `SolarShadowHeightSamples` → existing `CalibrationSamples` reference type. Tests: almanac vectors (exact), segmentation precision/recall on labeled fixtures, association refusal on ambiguity, trig identity on synthetic shadows, refusal without angles/GSD, no-metric-without-calibration invariant preserved. Estimated shape: one focused phase, not a milestone arc — but it is a subsystem build, and it starts only after explicit acceptance of this classification.

---

**End of closure analysis.** Classification recorded; implementation explicitly not started.
