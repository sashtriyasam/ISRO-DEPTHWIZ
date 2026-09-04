# Aryan Branch Inventory

Generated: 2026-09-04

## Branch Lineage

All Aryan branches form a **linear chain** — each branch is a strict ancestor of the next. There is no branching, no parallel work, and no redundancy. The current HEAD (`feat/aryan-session-correctness` at `d781621`) contains every commit from every Aryan branch.

```
85c7d9f  desktop-foundation (M01–M08)
  └─ 27ec398  camera-system (M02)
       └─ 9bef851  artifact-pipeline (M03)
            └─ fb7bfa3  layer-system (M04)
                 └─ 5101aac  height-exaggeration (M05)
                      └─ b5acc81  point-inspector (M06)
                           └─ 62d1a41  measurement-tools (M07)
                                └─ c515aa6  elevation-profile (M08)
                                     └─ 0a5f25b  backend-artifact-adapter (M09)
                                          └─ 9caf754  real-backend-integration (M10)
                                               └─ bf6f8eb  semantic-hardening (M11)
                                                    └─ f857f47  real-dsm-mesh-viewer (M12)
                                                         └─ f46ccc0  processing-workflow (M13)
                                                              └─ fb77952  input-workflow (M14)
                                                                   └─ 5c35f09  localservice-client (M15)
                                                                        └─ 91eea4d  artifact-transport (M16)
                                                                             └─ 24c3452  scientific-metadata (M17)
                                                                                  └─ 3b86ac2  advanced-camera (M18)
                                                                                       └─ 0529af9  production-backend (M19)
                                                                                            └─ 6b96e78  rendering-modes (M20)
                                                                                                 └─ 448ea52  flythrough (M21)
                                                                                                      └─ 1bf18e1  canonical-integration (M22)
                                                                                                           └─ c28af61  production-backend-hardening (M23)
                                                                                                                └─ 1dac740  flythrough-ux (M24)
                                                                                                                     └─ af6d416  flythrough-visual-validation (M25)
                                                                                                                          └─ 3e5be28  desktop-host (M26)
                                                                                                                               └─ dd1eb0b  project-session (M27)
                                                                                                                                    └─ d781621  session-correctness (M28) ← HEAD
```

## Branch Table

| BRANCH | SHA | ANCESTRAL OF | UNIQUE COMMITS | UNIQUE FILES | STATUS | RECOMMENDED ACTION |
|--------|-----|-------------|----------------|-------------|--------|-------------------|
| feat/aryan-desktop-foundation | 85c7d9f | all Aryan branches | 0 (base) | foundation only | HISTORICAL | No action — ancestor |
| feat/aryan-camera-system | 27ec398 | all post-M02 branches | 1 | camera/ | HISTORICAL | No action — ancestor |
| feat/aryan-artifact-pipeline | 9bef851 | all post-M03 branches | 1 | artifact/ | HISTORICAL | No action — ancestor |
| feat/aryan-layer-system | fb7bfa3 | all post-M04 branches | 1 | layers/ | HISTORICAL | No action — ancestor |
| feat/aryan-height-exaggeration | 5101aac | all post-M05 branches | 1 | display/ | HISTORICAL | No action — ancestor |
| feat/aryan-point-inspector | b5acc81 | all post-M06 branches | 1 | inspection/ | HISTORICAL | No action — ancestor |
| feat/aryan-measurement-tools | 62d1a41 | all post-M07 branches | 1 | measurement/ | HISTORICAL | No action — ancestor |
| feat/aryan-elevation-profile | c515aa6 | all post-M08 branches | 1 | profile/ | HISTORICAL | No action — ancestor |
| feat/aryan-backend-artifact-adapter | 0a5f25b | all post-M09 branches | 1 | backend/types.ts | HISTORICAL | No action — ancestor |
| feat/aryan-real-backend-integration | 9caf754 | all post-M10 branches | 1 | backend/bridge.ts | HISTORICAL | No action — ancestor |
| feat/aryan-semantic-hardening | bf6f8eb | all post-M11 branches | 1 | semantic fixes | HISTORICAL | No action — ancestor |
| feat/aryan-real-dsm-mesh-viewer | f857f47 | all post-M12 branches | 1 | meshAdapter | HISTORICAL | No action — ancestor |
| feat/aryan-processing-workflow | f46ccc0 | all post-M13 branches | 1 | processing/ | HISTORICAL | No action — ancestor |
| feat/aryan-input-workflow | fb77952 | all post-M14 branches | 1 | input/ | HISTORICAL | No action — ancestor |
| feat/aryan-localservice-client | 5c35f09 | all post-M15 branches | 1 | service/ | HISTORICAL | No action — ancestor |
| feat/aryan-artifact-transport | 91eea4d | all post-M16 branches | 1 | transport/ | HISTORICAL | No action — ancestor |
| feat/aryan-scientific-metadata | 24c3452 | all post-M17 branches | 1 | metadata/ | HISTORICAL | No action — ancestor |
| feat/aryan-advanced-camera | 3b86ac2 | all post-M18 branches | 1 | camera modes | HISTORICAL | No action — ancestor |
| feat/aryan-production-backend | 0529af9 | all post-M19 branches | 1 | applicationSource | HISTORICAL | No action — ancestor |
| feat/aryan-rendering-modes | 6b96e78 | all post-M20 branches | 1 | RenderingControls | HISTORICAL | No action — ancestor |
| feat/aryan-flythrough | 448ea52 | all post-M21 branches | 1 | flythrough/ | HISTORICAL | No action — ancestor |
| feat/aryan-canonical-integration | 1bf18e1 | all post-M22 branches | 1 | dw_serialize removed | HISTORICAL | No action — ancestor |
| feat/aryan-production-backend-hardening | c28af61 | all post-M23 branches | 1 | sourceDescriptor | HISTORICAL | No action — ancestor |
| feat/aryan-flythrough-ux | 1dac740 | all post-M24 branches | 1 | FlythroughPanel | HISTORICAL | No action — ancestor |
| feat/aryan-flythrough-visual-validation | af6d416 | all post-M25 branches | 1 | CDP tests | HISTORICAL | No action — ancestor |
| feat/aryan-desktop-host | 3e5be28 | all post-M26 branches | 1 | host/ | HISTORICAL | No action — ancestor |
| feat/aryan-project-session | dd1eb0b | M28 only | 1 | session/ | HISTORICAL | No action — ancestor |
| feat/aryan-session-correctness | d781621 | none (HEAD) | 0 (tip) | session fixes | CURRENT | Integration source |

## Key Finding

**Every Aryan branch is an ancestor of the current HEAD.** There are zero redundant, experimental, or orphaned branches. The entire Aryan development history is a single linear chain culminating at `d781621`.
