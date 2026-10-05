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

## Learned height model (`depthwizard-ndsm-vits`, height-model-v1)

DA-V2 Small fine-tuned to predict nDSM (metres above ground) by
`scripts/train_ndsm.py`: 3,213 training / 357 validation crops of 392 px
from 32 Swiss LiDAR sites (none within ~2 km of a benchmark site) at GSDs
0.35 / 0.6 / 1 / 2 m; 12 epochs, L1 + gradient loss, RTX 3050 4 GB.
Best epoch 11: held-out validation MAE 1.18 m, RMSE 3.07 m (nDSM).
Checkpoint sha256 `80903694b6039058808b47887bb45b07579a5528fbef0e27e36f74df47cdd2a4`.

In the app it runs inside DEM-anchored fusion with a fixed scale of 1:
DSM = Copernicus DEM (upsampled) + predicted structure - its low-pass at
the DEM footprint. Results (8 sites, all completed; RMSE/MAE in metres vs
the LiDAR DSM at image resolution; "30 m" = block means at the DEM scale):

| class | GSD | copernicus RMSE | fusion (DA-V2) RMSE | **fusion_ndsm RMSE** | change | copernicus MAE | **fusion_ndsm MAE** | copernicus r | **fusion_ndsm r** | copernicus 30 m RMSE | **fusion_ndsm 30 m RMSE** |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| urban | 0.6 m | 8.41 | 8.41 | **6.13** | -27% | 6.57 | **4.27** | 0.945 | **0.973** | 4.49 | **3.98** |
| urban | 2 m | 8.24 | 8.22 | **6.85** | -17% | 6.38 | **4.95** | 0.947 | **0.965** | 4.51 | **4.12** |
| sparse | 0.6 m | 2.00 | 1.98 | **1.64** | -18% | 0.82 | **0.74** | 0.910 | **0.940** | 1.18 | **1.07** |
| sparse | 2 m | 1.96 | 1.95 | **1.81** | -8% | 0.81 | **0.78** | 0.913 | **0.931** | 1.23 | **1.17** |
| forested | 0.6 m | 7.39 | 7.36 | **6.09** | -18% | 5.38 | **4.43** | 0.976 | **0.986** | 4.28 | **3.83** |
| forested | 2 m | 7.22 | 7.19 | **6.63** | -8% | 5.27 | **4.87** | 0.977 | **0.983** | 4.29 | **3.99** |
| hilly | 0.6 m | 18.07 | 17.96 | **17.41** | -4% | 9.49 | **8.81** | 0.992 | **0.993** | 16.35 | **16.18** |
| hilly | 2 m | 17.97 | 17.93 | **17.64** | -2% | 9.40 | **9.11** | 0.992 | **0.993** | 16.31 | **16.19** |

Findings:

1. The learned model improves on the DEM in every class and at both GSDs,
   most where structure dominates (urban -27% RMSE, -35% MAE at 0.6 m), and
   it beats the not-deployable LiDAR-fitted oracle for DA-V2 relative depth.
2. Gains hold at the 30 m DEM scale, so the fusion adds no low-frequency
   error against the DEM that the PS evaluation uses.
3. Hilly errors are dominated by Alpine relief a 30 m DEM cannot represent
   (and the LN02/EGM2008 datum offset); the height model cannot fix terrain.
4. Not yet covered: GSDs coarser than 2 m (the PS range goes to 10 m) and
   non-Swiss scenes. GAMUS urban crops (US cities, 1,797 prepared) are the
   next training addition; Cartosat-2S imagery has not been tested.

Known caveats: Swiss heights are LN02/LHN95 while Copernicus uses EGM2008
(a few metres of datum bias appear as `bias`); steep Alpine relief exceeds
what any 30 m DEM can represent.
