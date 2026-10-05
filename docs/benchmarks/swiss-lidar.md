# DSM accuracy benchmark: swisstopo LiDAR

Reproducible accuracy evidence for PS 26175's 50% "DSM estimation" criterion
(RMSE, MAE, correlation; stability across urban, sparse, hilly, forested).

## Data (open, no key)

| Role | Product | Resolution |
| :--- | :--- | :--- |
| Input imagery | SWISSIMAGE orthophoto, average-resampled | 0.6 m (Cartosat-2S-like) and 2 m |
| Ground truth | swissSURFACE3D LiDAR DSM | 0.5 m |
| Reference DEM used by the app | Copernicus GLO-30 (fetched automatically) | 30 m |

8 benchmark sites (1 km tiles), 2 per class: urban (Zurich, Bern), sparse
(Avenches, Seeland), hilly (Lauterbrunnen, Appenzell), forested (Sihlwald,
Jura). They are excluded, with a 2-3 km guard, from every training set.

Reproduce: `python scripts/benchmark_swiss.py --gsd 0.6 2.0 --tiled [--ndsm cuda]`.

## Products compared

* **copernicus** — the reference DEM alone, bilinearly resampled (no model).
* **affine** — the legacy method: one scale+offset fit of relative depth to the DEM.
* **fusion** — DEM-anchored fusion, detail scale fitted at the structure scale.
* **fusion_oracle** — fusion with the detail scale fitted to the LiDAR (upper bound; not deployable).
* **fusion_ndsm** — DEM + structure from the LiDAR-trained height model (`depthwizard-ndsm-vits`).

Metrics are computed against the LiDAR DSM at image resolution, and at the
DEM's 30 m scale. Values below are means over the sites of each class
(DA-V2 Small, tiled inference).

## Baseline results (before the learned height model)

| class | GSD | copernicus RMSE | fusion RMSE | affine RMSE | oracle RMSE | copernicus r |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| urban | 0.6 m | 8.38 | 8.38 | 31.24 | 7.48 | 0.968 |
| urban | 2 m | 8.22 | 8.21 | 23.49 | 8.20 | 0.970 |
| sparse | 0.6 m | 2.00 | 1.98 | 6.24 | 1.81 | 0.910 |
| sparse | 2 m | 1.96 | 1.95 | 6.40 | 1.89 | 0.913 |
| forested | 0.6 m | 7.39 | 7.36 | 33.09 | 7.07 | 0.976 |
| forested | 2 m | 7.22 | 7.19 | 21.46 | 7.06 | 0.977 |
| hilly (Lauterbrunnen) | 0.6 m | 20.73 | 20.63 | — | — | 0.993 |

Findings:

1. The legacy affine calibration was 3-4x worse than simply using the DEM:
   monocular depth on nadir imagery does not see terrain, so a single
   global fit cannot follow hills.
2. DEM-anchored fusion is never worse than the DEM and matches it at 30 m
   by construction; that is the property the PS evaluation (scored against
   SRTM/Copernicus) rewards.
3. Relative-depth detail carries real structure (oracle: -11% RMSE urban at
   0.6 m), but its scale cannot be recovered from a 30 m DEM. The learned
   height model supplies that scale (metres above ground) directly.

Known caveats: Swiss heights are LN02/LHN95 while Copernicus uses EGM2008
(a few metres of datum bias appear as `bias`); steep Alpine relief exceeds
what any 30 m DEM can represent.
