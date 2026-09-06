# Final Branch Inventory — DepthWizard (SIH 26175)

**Audit Date:** 2026-09-06  
**Auditor:** Shivam (Release Authority)  
**Source of Truth:** `git branch -a`, `git log`, `git for-each-ref`

---

## Classification Legend

| Classification      | Meaning                                            |
| ------------------- | -------------------------------------------------- |
| **HISTORICAL**      | Merged into main, work complete, ready for archive |
| **ACTIVE RESEARCH** | Ongoing ML/experimental work, not for release      |
| **RELEASE WORK**    | Active release-related work on main or near-main   |
| **STALE**           | Inactive, superseded, or superseded by main        |
| **ACTIVE FEATURE**  | Active UI/UX development, not blocking release     |
| **UNKNOWN**         | Unclear purpose, needs investigation               |

---

## Branch Inventory

| Branch                                      | Owner   | Purpose                   | Latest SHA | Relationship to Main                                                                  | Classification          | Recommended Action                   |
| ------------------------------------------- | ------- | ------------------------- | ---------- | ------------------------------------------------------------------------------------- | ----------------------- | ------------------------------------ |
| `main`                                      | Shivam  | Release baseline          | `809801d`  | HEAD                                                                                  | **RELEASE**             | —                                    |
| `feat/aryan-native-host-installer`          | Aryan   | Native host + installer   | `d87db7b`  | Merged via PR #2                                                                      | **HISTORICAL**          | Archive after confirmation           |
| `feat/shivam-runtime-release-integration`   | Shivam  | S17/S18 integration       | `dddae24`  | Merged via PR #1                                                                      | **HISTORICAL**          | Archive after confirmation           |
| `feat/shivam-native-runtime-packaging`      | Shivam  | S17 packaging             | `31389f3`  | Merged into integration branch                                                        | **HISTORICAL**          | Archive                              |
| `feat/shivam-runtime-provisioning`          | Shivam  | S18 provisioning          | `daf3482`  | Merged into integration branch                                                        | **HISTORICAL**          | Archive                              |
| `feat/shivam-repo-governance`               | Shivam  | Governance                | `8f00586`  | Behind main                                                                           | **STALE**               | Archive                              |
| `feat/shivam-relative-desktop-boundary`     | Shivam  | S23 boundary              | `6ed623e`  | Behind main                                                                           | **ACTIVE RELEASE WORK** | Keep                                 |
| `feat/shivam-aryan-integration-readiness`   | Shivam  | Integration readiness     | `56d27dd`  | Merged into main                                                                      | **HISTORICAL**          | Archive                              |
| `feat/shivam-shravan-dav2-integration`      | Shivam  | S16 DA-V2 adapter         | `1a04c4b`  | Merged into main                                                                      | **HISTORICAL**          | Archive                              |
| `feat/shivam-dav2-runtime-verification`     | Shivam  | S16R runtime verification | `efe38fa`  | Merged into main                                                                      | **HISTORICAL**          | Archive                              |
| `feat/shivam-sih-architecture-contract`     | Shivam  | S22 SIH architecture      | `875484a`  | Merged into main                                                                      | **HISTORICAL**          | Archive                              |
| `feat/shivam-dsm-engine`                    | Shivam  | S11 DSM engine            | `379a36b`  | Merged into main                                                                      | **HISTORICAL**          | Archive                              |
| `feat/shivam-mesh-engine`                   | Shivam  | S13 Mesh engine           | `1c762f6`  | Merged into main                                                                      | **HISTORICAL**          | Archive                              |
| `feat/shivam-geospatial`                    | Shivam  | S7 Geospatial             | `62ee1b4`  | Merged into main                                                                      | **HISTORICAL**          | Archive                              |
| `feat/shivam-dem-reference`                 | Shivam  | S8 DEM reference          | `e876d78`  | Merged into main                                                                      | **HISTORICAL**          | Archive                              |
| `feat/shivam-reference-controls`            | Shivam  | S8.x Reference controls   | `6648602`  | Merged into main                                                                      | **HISTORICAL**          | Archive                              |
| `feat/shivam-height-semantics`              | Shivam  | S10 Height semantics      | `b095510`  | Merged into main                                                                      | **HISTORICAL**          | Archive                              |
| `feat/shivam-calibration`                   | Shivam  | S9 Calibration            | `1ce6e32`  | Merged into main                                                                      | **HISTORICAL**          | Archive                              |
| `feat/shivam-geotiff-export`                | Shivam  | S12 GeoTIFF export        | `f3db71c`  | Merged into main                                                                      | **HISTORICAL**          | Archive                              |
| `feat/shivam-pipeline-orchestration`        | Shivam  | S14 Pipeline              | `1304676`  | Merged into main                                                                      | **HISTORICAL**          | Archive                              |
| `feat/shivam-local-service`                 | Shivam  | S15 Local service         | `072f9bf`  | Merged into main                                                                      | **HISTORICAL**          | Archive                              |
| `feat/shivam-ingestion`                     | Shivam  | S2/S3 Ingestion           | `cb53513`  | Merged into main                                                                      | **HISTORICAL**          | Archive                              |
| `feat/shivam-depth-backend`                 | Shivam  | S5 Backend boundary       | `133ba5f`  | Merged into main                                                                      | **HISTORICAL**          | Archive                              |
| `feat/shivam-foundation`                    | Shivam  | S1 Foundation             | `8b6e1dd`  | Merged into main                                                                      | **HISTORICAL**          | Archive                              |
| `feat/shivam-geotiff-export`                | Shivam  | S12 GeoTIFF export        | `f3db71c`  | Merged into main                                                                      | **HISTORICAL**          | Archive                              |
| `feat/shivam-benchmark-expansion`           | Shivam  | S21 Significance          | `3cd7d70`  | Behind main                                                                           | **ACTIVE RESEARCH**     | Keep                                 |
| `feat/shivam-benchmark-scaleout`            | Shivam  | S21 Scale-out             | `e4d9f9c`  | Behind main                                                                           | **ACTIVE RESEARCH**     | Keep                                 |
| `feat/shivam-cross-city-benchmark`          | Shivam  | S20 Cross-city            | `166b1cd`  | Behind main                                                                           | **ACTIVE RESEARCH**     | Keep                                 |
| `feat/shivam-field-benchmark`               | Shivam  | S19 Benchmark harness     | `7d26e14`  | Behind main                                                                           | **ACTIVE RESEARCH**     | Keep                                 |
| `feat/shivam-dav2-runtime-verification`     | Shivam  | S16R                      | `efe38fa`  | Merged                                                                                | **HISTORICAL**          | Archive                              |
| `feat/shivam-relative-desktop-boundary`     | Shivam  | S23 boundary              | `6ed623e`  | Behind main                                                                           | **ACTIVE RELEASE WORK** | Keep                                 |
| `feat/shivam-repo-governance`               | Shivam  | Governance                | `8f00586`  | Behind main                                                                           | **STALE**               | Archive                              |
| `feat/shivam-runtime-provisioning`          | Shivam  | S18 Provisioning          | `daf3482`  | Merged via integration                                                                | **HISTORICAL**          | Archive                              |
| `feat/shivam-runtime-release-integration`   | Shivam  | S17/S18 integration       | `dddae24`  | Merged via PR #1                                                                      | **HISTORICAL**          | Archive                              |
| `feat/shivam-native-runtime-packaging`      | Shivam  | S17 Packaging             | `31389f3`  | Merged via integration                                                                | **HISTORICAL**          | Archive                              |
| `feat/shivam-shravan-dav2-integration`      | Shivam  | S16 DA-V2                 | `1a04c4b`  | Merged                                                                                | **HISTORICAL**          | Archive                              |
| `feat/shivam-sih-architecture-contract`     | Shivam  | S22 Architecture          | `875484a`  | Merged                                                                                | **HISTORICAL**          | Archive                              |
| `feat/shravan-final-ml-freeze`              | Shravan | ML candidate              | `25a91f1`  | Behind main                                                                           | **ACTIVE RESEARCH**     | Keep                                 |
| `feat/shravan-final-ml-release`             | Shravan | ML release evidence (M17) | `b920772`  | Disjoint history (no merge-base with main); docs-only release commit on top of freeze | **ACTIVE RESEARCH**     | Keep — do not merge (research track) |
| `feat/shravan-m17-structural-adapt`         | Shravan | M17 research              | `b6b3696`  | Behind main                                                                           | **ACTIVE RESEARCH**     | Keep                                 |
| `feat/shravan-m16-geonrw-adapt`             | Shravan | M16 research              | `2475537`  | Behind main                                                                           | **ACTIVE RESEARCH**     | Keep                                 |
| `feat/shravan-m14-external-readiness`       | Shravan | M14 research              | `668bc37`  | Behind main                                                                           | **ACTIVE RESEARCH**     | Keep                                 |
| `feat/shravan-m13-extended-training`        | Shravan | M13 research              | `e7ae33f`  | Behind main                                                                           | **ACTIVE RESEARCH**     | Keep                                 |
| `feat/shravan-m10-lowheight-loss`           | Shravan | M10 research              | `369608b`  | Behind main                                                                           | **ACTIVE RESEARCH**     | Keep                                 |
| `feat/shravan-m10-seed-repeat`              | Shravan | M10 research              | `5701d4c`  | Behind main                                                                           | **ACTIVE RESEARCH**     | Keep                                 |
| `feat/shravan-dav2-geographic-diversity`    | Shravan | M8 research               | `e8ce6ad`  | Behind main                                                                           | **ACTIVE RESEARCH**     | Keep                                 |
| `feat/shravan-dav2-geographic-rebalancing`  | Shravan | M9 research               | `0601c89`  | Behind main                                                                           | **ACTIVE RESEARCH**     | Keep                                 |
| `feat/shravan-dav2-target-normalization`    | Shravan | M9 research               | `5a6164b`  | Behind main                                                                           | **ACTIVE RESEARCH**     | Keep                                 |
| `feat/shravan-dav2-target-normalization-m9` | Shravan | M9 research               | `3bcf99b`  | Behind main                                                                           | **ACTIVE RESEARCH**     | Keep                                 |
| `feat/aryan-camera-system`                  | Aryan   | Camera UI                 | `27ec398`  | Behind main                                                                           | **ACTIVE FEATURE**      | Keep                                 |
| `feat/aryan-native-host-installer-sync`     | Aryan   | Host/installer sync       | `2ccb996`  | Ahead of installer branch                                                             | **HISTORICAL**          | Archive                              |
| `feat/aryan-native-host-installer`          | Aryan   | Host + installer          | `d87db7b`  | Merged via PR #2                                                                      | **HISTORICAL**          | Archive                              |
| `feat/aryan-...` (other)                    | Aryan   | UI/UX features            | Various    | Behind main                                                                           | **ACTIVE FEATURE**      | Keep                                 |

---

## Summary Statistics

| Classification                    | Count | Branches                                |
| --------------------------------- | ----- | --------------------------------------- |
| **HISTORICAL**                    | 22    | Merged via PR #1, #2, or direct to main |
| **ACTIVE RESEARCH**               | 11    | Shravan M10-M17, Shivam benchmarks      |
| **ACTIVE RELEASE WORK**           | 2     | S23 boundary, S24 acceptance            |
| **ACTIVE FEATURE**                | 5+    | Aryan UI/UX, camera, rendering          |
| **STALE**                         | 2     | Repo governance, Aryan sync branch      |
| **HISTORICAL (ready to archive)** | 22    | PR #1, #2 merged branches               |

---

## Archive Recommendation

### Immediate Archive (Safe — work fully on main)

These branches have been merged and their work is fully represented on `main`:

```bash
# Shivam release integration
feat/shivam-runtime-release-integration
feat/shivam-native-runtime-packaging
feat/shivam-runtime-provisioning
feat/shivam-repo-governance

# Aryan host/installer
feat/aryan-native-host-installer
feat/aryan-native-host-installer-sync

# S16/S16R/S22/S16R already on main via PR #1/#2
feat/shivam-dav2-runtime-verification
feat/shivam-shravan-dav2-integration
feat/shivam-sih-architecture-contract
feat/shivam-project-governance
```

### DO NOT ARCHIVE (Active Work)

| Branch                                  | Reason                     |
| --------------------------------------- | -------------------------- |
| `feat/shivam-relative-desktop-boundary` | S23 boundary work          |
| `feat/shivam-relative-desktop-boundary` | S24 acceptance (gated)     |
| `feat/shivam-benchmark-*`               | Active evaluation research |
| `feat/shravan-*`                        | All Shravan ML research    |
| `feat/aryan-camera-system`              | Active UI feature          |
| Other Aryan UI branches                 | Active UI development      |

---

## Archive Procedure

```bash
# For each branch to archive:
git push origin --delete <branch-name>
git branch -d <branch-name>

# Or create archive tag:
git tag archive/<branch-name> <branch-sha>
git push origin archive/<branch-name>
git push origin --delete <branch-name>
git branch -d <branch-name>
```

**Do NOT delete** without Shivam's explicit confirmation that work is fully on main.

---

**End of Branch Inventory.** This reflects actual Git state at `809801d45ac7f3be857b284539e4d9028e914e09`.
