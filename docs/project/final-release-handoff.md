# Final Release Handoff — DepthWizard (SIH 26175)

**Date:** 2026-09-06  
**Canonical Main SHA:** `809801d45ac7f3be857b284539e4d9028e914e09`  
**Release Control Branch:** `feat/shivam-final-release-control` (to be created)  
**Release Authority:** Shivam (final merge authority)

---

## Repository State

### Current Main

- **HEAD:** `809801d45ac7f3be857b284539e4d9028e914e09`
- **origin/main:** `809801d45ac7f3be857b284539e4d9028e914e09` ✅ Synced
- **Working Tree:** Clean (modified docs only)

### Open PRs / Issues

| Item        | Count                |
| ----------- | -------------------- |
| Open PRs    | 0 (PR #1, #2 merged) |
| Open Issues | 0                    |

### Tags / Releases

| Item                     | Status                                           |
| ------------------------ | ------------------------------------------------ |
| Release Tags             | 0 (none created)                                 |
| Pre-release Tag Prepared | `v0.1.0-sih-26175-rc1` (documented, not created) |

---

## CI / Build System

### GitHub Actions CI

- **Status:** ✅ **CREATED** — `.github/workflows/ci.yml`
- **Jobs:** `python`, `frontend`, `electron-config`, `scientific-contracts`, `hygiene`
- **Required Status Checks:** `python`, `frontend`, `electron-config`, `scientific-contracts`, `hygiene`
- **Triggers:** Push to main, PR to main

### Build Validation (Latest Run)

| Check                | Result                                                                            |
| -------------------- | --------------------------------------------------------------------------------- |
| Python pytest        | 503 passed, 4 skipped                                                             |
| Ruff check           | All passed                                                                        |
| Ruff format          | 173 files formatted                                                               |
| Mypy                 | 11 pre-existing test-file errors (source clean)                                   |
| TypeScript typecheck | Passed                                                                            |
| Frontend build       | Passed (842.11 kB)                                                                |
| Electron build       | Passed                                                                            |
| Electron build:win   | Passed — 115 MB NSIS installer                                                    |
| Installer SHA256     | `1310ca16350605077df39c4ee6feb27fef1d620845e469c9ee82479d456b8383` (latest build) |

---

## Branch Protection

| Item                    | Status            | Notes                                                                      |
| ----------------------- | ----------------- | -------------------------------------------------------------------------- |
| Branch Protection Rules | 📋 **DOCUMENTED** | `docs/github-branch-protection.md` — manual GitHub UI config required      |
| Required Status Checks  | 📋 DOCUMENTED     | `python`, `frontend`, `electron-config`, `scientific-contracts`, `hygiene` |
| CODEOWNERS              | ✅ Present        | Shivam (all), Aryan (src/, electron/), Shravan (tests/, docs/)             |
| Force Push Protection   | 📋 REQUIRED       | Documented in branch protection doc                                        |
| Linear History          | 📋 REQUIRED       | Documented                                                                 |

---

## Scientific Status

### Core Contracts

| Contract                           | Status       | Evidence                                   |
| ---------------------------------- | ------------ | ------------------------------------------ |
| Relative depth ≠ metric DSM        | ✅ ENFORCED  | `DepthScale.RELATIVE`, `units=None`        |
| PNG/JPG: relative only             | ✅ ENFORCED  | `NON_GEOREFERENCED` path                   |
| GeoTIFF: CRS/transform preserved   | ✅ ENFORCED  | `InputInspection`                          |
| Metric requires calibration        | ✅ ENFORCED  | `CalibrationSamples` + `CalibrationResult` |
| DEM ≠ DSM ≠ AGL                    | ✅ ENFORCED  | `ElevationSemantics` enum                  |
| Height exaggeration = display-only | ✅ ENFORCED  | `applyHeightExaggeration`                  |
| No CRS invention                   | ✅ ENFORCED  | Contracts forbid                           |
| Provenance chain intact            | ✅ PRESERVED | Full pipeline                              |

### Contract Regression Check

```bash
git diff origin/main...HEAD -- src/depthwizard/contracts/ src/depthwizard/calibration/ src/depthwizard/dsm/ src/depthwizard/height/ src/depthwizard/mesh/ src/depthwizard/geospatial/ src/depthwizard/rdsm/ src/depthwizard/backends/
# → NO OUTPUT (zero changes)
```

---

## DA-V2 Status

| Item                        | Status                                                             | Details                            |
| --------------------------- | ------------------------------------------------------------------ | ---------------------------------- |
| Model                       | Depth Anything V2 Small                                            | Frozen                             |
| Upstream Repo               | `DepthAnything/Depth-Anything-V2`                                  | Pinned                             |
| Upstream Revision           | `a561b849ebae10a6f5ef49e26c83cbbcd36c71bf`                         | Git HEAD verified                  |
| Checkpoint                  | `depth_anything_v2_vits.pth`                                       | Git-ignored, SHA256 verified       |
| Checkpoint SHA256           | `715fade13be8f229f8a70cc02066f656f2423a59effd0579197bbf57860e1378` | Verified                           |
| Output Semantics            | RELATIVE (`units=None`)                                            | Contract-enforced                  |
| DA-V2 Adapter               | `src/depthwizard/backends/depth_anything_v2.py`                    | Implements `DepthBackend` protocol |
| Runtime Verification (S16R) | ✅ ON MAIN                                                         | Commit `6ed623e` / `07bc635`       |

---

## Runtime Status

| Component              | Status        | Evidence                                                           |
| ---------------------- | ------------- | ------------------------------------------------------------------ |
| `runtime_check.py`     | ✅ ON MAIN    | Interpreter, deps, checkpoint SHA, upstream rev                    |
| `provision_runtime.py` | ✅ ON MAIN    | Core/DA-V2 modes, venv, pip, git, checkpoint                       |
| Core Provisioning      | ✅ VERIFIED   | `ready: true`, `service_launch_ready: true`, `offline_ready: true` |
| Idempotent Re-run      | ✅ VERIFIED   | `venv.reused: true`                                                |
| DA-V2 Provisioning     | ✅ STRUCTURED | Fails correctly when assets missing                                |
| Checkpoint SHA256      | ✅ ENFORCED   | `715fade13be8f229f8a70cc02066f656f2423a59effd0579197bbf57860e1378` |
| Upstream Revision      | ✅ ENFORCED   | Git HEAD check against `a561b849...`                               |
| Offline Execution      | ✅ VERIFIED   | `HF_HUB_OFFLINE=1`, no network imports                             |
| No Silent Fallback     | ✅ ENFORCED   | Explicit DA-V2 request + unavailable → ERROR                       |

---

## Installer Status

| Component                   | Status                                                             | Evidence                                                   |
| --------------------------- | ------------------------------------------------------------------ | ---------------------------------------------------------- |
| NSIS Installer Build        | ✅ PASS                                                            | Exit 0, 115 MB                                             |
| Installer SHA256 (latest)   | `1310ca16350605077df39c4ee6feb27fef1d620845e469c9ee82479d456b8383` |                                                            |
| Portable Build              | ✅ PASS                                                            | 334 MB, clean                                              |
| Installer Contents          | ✅ CLEAN                                                           | No .git, node_modules, src, .venv, checkpoints, .pth, .env |
| Extra Resources             | ✅ CORRECT                                                         | `depthwiz_service.py`, `backend_bridge.py` (asarUnpack)    |
| Code Signing                | ❌ UNSIGNED                                                        | Test build only                                            |
| Physical Windows Acceptance | ⚠️ NOT VERIFIED                                                    | Requires clean VM + display + checkpoint                   |

---

## Shravan ML Status

| Branch                                | Status         | Notes                                      |
| ------------------------------------- | -------------- | ------------------------------------------ |
| `feat/shravan-final-ml-freeze`        | Research       | "Lock final ML candidate selection (M17)"  |
| `feat/shravan-m14-external-readiness` | Research       | GAMUS alignment audit                      |
| `feat/shravan-m17-structural-adapt`   | Research       | Scale-decoupled GeoNRW probe               |
| `feat/shravan-m14-external-readiness` | Research       | GAMUS alignment audit                      |
| `feat/shravan-m13-extended-training`  | Research       | Report finalized                           |
| **Final ML Candidate**                | ❌ **BLOCKED** | No frozen checkpoint with verified metrics |

---

## Release Gate Matrix (Current)

Canonical matrix: `docs/final-release-gate.md` (G1–G19). Summary:

| Gate group                                               | Status                                                | Blocker            |
| -------------------------------------------------------- | ----------------------------------------------------- | ------------------ |
| G1 Scientific contracts, G4–G7 Calibration/DSM/rDSM/Mesh | **PASS**                                              | —                  |
| G2 Final ML candidate                                    | **PARTIAL** (M17 locked in research, not promoted)    | **Yes**            |
| G3 Real DA-V2 runtime                                    | **NOT VERIFIED** (assets-gated)                       | **Yes** (physical) |
| G8–G10 Native host / runtime / provisioning              | **PASS**                                              | —                  |
| G11 Installer (build)                                    | **PASS** (build)                                      | **Yes** (physical) |
| G12–G13 Offline / failure handling / reproducibility     | **PASS**                                              | —                  |
| G14 Physical Windows witness                             | **NOT VERIFIED**                                      | **Yes**            |
| G15 PS compliance                                        | **PARTIAL** (solar MISSING, neural rendering PARTIAL) | **Yes**            |
| G16 Scientific evidence                                  | **PARTIAL** (honest caveats)                          | **Yes**            |
| G18 Documentation                                        | **PARTIAL** (this branch updates stale docs)          | —                  |
| G19 Governance                                           | **PARTIAL** (CI + CODEOWNERS created; BP manual)      | —                  |

**Current Decision:** **RELEASE CANDIDATE — PHYSICAL WITNESS REQUIRED** (with scientific-candidate requirement noted)

---

## Confirmed Blockers

| Blocker                     | Gate(s)          | Owner        | Resolution                                                |
| --------------------------- | ---------------- | ------------ | --------------------------------------------------------- |
| Physical Windows acceptance | G2, G10, G14     | Aryan        | Clean Windows VM + display + checkpoint                   |
| Real DA-V2 inference        | G2               | Aryan/Shivam | Checkpoint + display + upstream source                    |
| Shravan final ML candidate  | G15              | Shravan      | Frozen checkpoint + SHA256 + upstream rev + eval evidence |
| Code signing                | G10 (production) | Shivam/Aryan | Obtain EV certificate                                     |

---

## Exact Next Actions

### ARYAN (Exact Action)

> **Run physical Windows acceptance on clean Windows VM:**
>
> ```bash
> # On clean Windows VM with display:
> # 1. Copy installer + checkpoint
> # 2. Run installer → launch → verify runtime resolution
> # 3. Verify service capabilities → real DA-V2 (with checkpoint)
> # 4. Execute calibration → metric DSM → mesh → renderer
> # 5. Fill PASS/FAIL table in docs/windows-release-acceptance.md
> ```

### SHRAVAN (Exact Action)

> **Complete final ML candidate evidence (M17 locked in research):**
>
> 1. Formal duesseldorf/herne/neuss verification rerun is BLOCKED on data access — record unblock requirements
> 2. Deliver frozen M17 evidence pack: checkpoint `experiments/m17-geonrw-struct-e01/checkpoints/best.pt` (SHA256 `D7C0BE91…EDAC`) + upstream revision + protocol + metrics + limitations
> 3. Propose product-path promotion (Shivam must accept; no silent model swap)
> 4. Update `docs/final-release-gate.md` G2 only with real evidence

### SHIVAM (Exact Action)

> **Complete release control plane:**
>
> 1. **CI:** ✅ Created (`.github/workflows/ci.yml`)
> 2. **Branch Protection:** 📋 Documented (`docs/github-branch-protection.md`) — apply via GitHub UI
> 3. **Code Signing:** 📋 Documented (`docs/windows-code-signing.md`) — obtain EV certificate
> 4. **Physical Acceptance:** Coordinate Aryan's witness
> 5. **Final Tag:** After all gates PASS → `git tag v0.1.0-sih-26175-rc1` (explicit authorization only)

---

## Repository Hygiene

| Item                           | Status                           |
| ------------------------------ | -------------------------------- |
| Model weights committed        | ❌ NO (gitignored)               |
| Checkpoints committed          | ❌ NO (gitignored)               |
| Secrets committed              | ❌ NO (gitignored)               |
| Release artifacts committed    | ❌ NO (gitignored)               |
| Developer paths embedded       | ❌ NO (location labels only)     |
| Large files (>50MB) tracked    | ❌ NO                            |
| Installer deterministic        | ✅ (fixed config, no timestamps) |
| Offline execution reproducible | ✅ (`HF_HUB_OFFLINE=1`)          |

---

## Final Release Decision

**RELEASE CANDIDATE — PHYSICAL WITNESS REQUIRED**

All automated gates PASS. Requires:

1. **Physical Windows acceptance** (Aryan) — clean VM + display + checkpoint
2. **Final ML candidate frozen** (Shravan) — checkpoint + SHA256 + upstream rev + eval
3. **Code signing** (Shivam/Aryan) — EV certificate for production

**Do NOT declare SIH release-ready until:**

- Physical Windows acceptance actually witnessed
- Final ML candidate frozen with evidence
- Remaining P1 blockers resolved

---

**End of Handoff.** This reflects actual state of `main` at `809801d45ac7f3be857b284539e4d9028e914e09`.
