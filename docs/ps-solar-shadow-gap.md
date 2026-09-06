# PS Gap — Solar-Shadow Geometry / Trigonometry (SIH 26175)

**Date:** 2026-09-06
**Auditor:** Shivam (Architecture Authority)
**Main:** `809801d45ac7f3be857b284539e4d9028e914e09`
**Status:** CONFIRMED GAP — no implementation exists. No code changes in this document.

---

## 1. Exact Requirement

SIH PS 26175 references height estimation aided by **solar shadow geometry / trigonometry**: building height derived from shadow length together with solar elevation/azimuth angles (single optical monocular satellite image).

## 2. Why the Current System Does Not Satisfy It

Repository-wide search (`*.py` under `src/`, plus `*.ts/*.tsx`) for `shadow|solar|azimuth|trigonometr|sun_angle` returns **zero implementation matches**. The only mentions are gap-analysis prose in `docs/sih-compliance-matrix.md` and this file.

Current height path is exclusively:

```
DA-V2 relative depth → explicit DEM/GCP calibration → metric DSM
```

No module:

- detects shadows,
- reads or computes solar angles,
- converts shadow length → height,
- records sun-angle provenance.

Terrain mesh therefore never encodes solar-shadow geometry. **Do not equate terrain mesh with solar-shadow geometry.**

## 3. Minimum Scientifically Valid Implementation

A defensible (non-fabricated) solar-shadow height leg requires all of:

1. **Sun geometry source** — solar elevation + azimuth per scene from image metadata (preferred) or from acquisition time + lat/lon + scene center via an astronomical solar-position model. If neither exists, the method is inapplicable — refuse, never assume angles.
2. **Shadow segmentation** — building-shadow mask from the RGB input with a documented, deterministic rule; validated against labeled shadows (precision/recall reported, not eyeballed).
3. **Shadow-to-building association** — each shadow linked to its casting structure along the solar azimuth direction; ambiguous associations rejected, not guessed.
4. **Ground sampling** — shadow length in metres requires the image GSD (GeoTIFF transform) or an explicit scale reference. Non-georeferenced PNG/JPG without GSD cannot yield metric shadow heights.
5. **Trigonometry** — `height = shadow_length_m × tan(solar_elevation)` per associated pair; flat-ground assumption stated and checked (slope correction or refusal on terrain).
6. **Provenance** — sun angles + source, segmentation method + version, association rule, GSD source, per-sample validity, all recorded on the product.

## 4. Required Inputs

| Input           | Source                                | Units        |
| --------------- | ------------------------------------- | ------------ |
| RGB scene       | `InputInspection` (existing)          | uint8 HWC    |
| Solar elevation | image metadata, or time+lat/lon model | degrees      |
| Solar azimuth   | image metadata, or time+lat/lon model | degrees      |
| GSD / transform | GeoTIFF transform (Path B only)       | m/px         |
| Shadow mask     | new segmentation step                 | boolean grid |

## 5. Units

Metres for heights/lengths; degrees for angles. Relative-only inputs (Path A without GSD) can produce at most a dimensionless shadow-ratio diagnostic — never metres.

## 6. Coordinate Assumptions

- Shadows fall on locally flat ground unless a DEM proves otherwise.
- Solar azimuth defines the shadow direction axis; association runs along it.
- Pixel grid aligned to image axes; GSD assumed uniform (checked, not assumed silently).

## 7. Expected Output

`SolarShadowHeightSamples`: per-building height estimates + validity + full provenance (sun source, segmentation version, GSD source). Consumable as an additional reference input to the existing `CalibrationSamples` path — never a direct DSM overwrite.

## 8. Integration Point

New `depthwizard.solar` package (Shivam-owned) feeding `depthwizard.controls` / `CalibrationSamples` as one more reference type. The `DepthBackend` contract and calibration engine stay unchanged; the adapter stays transparent.

## 9. Tests Required

- solar-position vs published almanac vectors (exact),
- shadow segmentation precision/recall on labeled fixtures,
- association rejection on ambiguous scenes,
- trig identity on synthetic shadows (exact),
- refusal when sun angles or GSD absent,
- no-metric-without-calibration invariant preserved.

## 10. Essential for Final Demo?

**Yes** — if SIH judges require the solar-shadow leg. The current system demonstrably covers depth → calibration → DSM → mesh → flythrough, but cannot claim the solar-shadow requirement.

## 11. Small Focused Implementation Sufficient?

**No — classification C (MAJOR GAP).** Sun metadata sourcing, shadow segmentation with validation, association logic, and calibration integration constitute a new R&D subsystem, not a patch. Do not start implementation until separately scoped and accepted.

---

**End of gap analysis.** No implementation performed; no evidence fabricated.
