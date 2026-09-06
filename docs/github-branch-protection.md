# Branch Protection Configuration

**Repository:** sashtriyasam/ISRO-DEPTHWIZ
**Branch:** main
**Date:** 2026-09-06

## Current Status (verified live 2026-09-06 via API)

**Branch Protection:** ✅ CONFIGURED on `main`
**GitHub Actions CI:** ✅ Present (`.github/workflows/ci.yml`)

## Required Branch Protection Rules

The following rules should be configured on the `main` branch through GitHub Settings → Branches → Branch protection rules:

### Required Settings

| Setting                                                    | Value                                                                      | Rationale                 |
| ---------------------------------------------------------- | -------------------------------------------------------------------------- | ------------------------- |
| **Require a pull request before merging**                  | ✅ Enabled                                                                 | Enforces code review      |
| **Required approving reviews**                             | 1                                                                          | At least one reviewer     |
| **Dismiss stale PR approvals when new commits are pushed** | ✅ Enabled                                                                 | Prevents stale approvals  |
| **Require review from code owners**                        | ✅ Enabled                                                                 | CODEOWNERS file present   |
| **Require status checks to pass before merging**           | ✅ Enabled                                                                 | Enforces CI               |
| **Required status checks**                                 | `python`, `frontend`, `electron-config`, `scientific-contracts`, `hygiene` | All CI jobs must pass     |
| **Require branches to be up to date before merging**       | ✅ Enabled                                                                 | Prevents stale merges     |
| **Require linear history**                                 | ✅ Enabled                                                                 | No merge commits on main  |
| **Include administrators**                                 | ✅ Enforced                                                                | No bypass for admins      |
| **Allow force pushes**                                     | ❌ Disabled                                                                | Prevents history rewrites |
| **Allow deletions**                                        | ❌ Disabled                                                                | Prevents branch deletion  |

### Required Status Checks (Exact Names)

The CI workflow defines these job names that must be used as required status checks:

1. `python` — Python tests, lint, typecheck
2. `frontend` — TypeScript typecheck, tests, build
3. `electron-config` — Electron TypeScript/build validation
4. `scientific-contracts` — Contract regression check
5. `hygiene` — Release artifact hygiene

### CODEOWNERS File

A `.github/CODEOWNERS` file exists with:

```
# Shivam: Architecture, Python core, geospatial, calibration, DSM, pipeline, integration, release, scientific acceptance, final merge authority
* @sashtriyasam

# Aryan: Desktop app (React/TS/Three.js), rendering, navigation, measurement, UX, packaging
/src/ @sashtriyasam
/electron/ @sashtriyasam

# Shravan: ML, datasets, depth models, experiments, benchmarks
/tests/ @sashtriyasam
/docs/ @sashtriyasam
```

### Verified Live Configuration (2026-09-06, via API)

| Setting                               | Actual value         | Matches recommendation?                                                                 |
| ------------------------------------- | -------------------- | --------------------------------------------------------------------------------------- |
| Require a pull request before merging | ✅ Enabled           | Yes                                                                                     |
| Required approving reviews            | 0 (none required)    | Deviates (recommended 1) — correct for solo repo: GitHub authors cannot approve own PRs |
| Dismiss stale approvals               | ❌ Disabled          | Deviates — moot with 0 required reviews                                                 |
| Require code-owner review             | ❌ Disabled          | Deviates — moot solo; CODEOWNERS file still present as documentation                    |
| Require status checks                 | ✅ All 6 CI contexts | Yes (superset: includes `Required CI Checks`)                                           |
| Strict (branches up to date)          | ❌ Disabled          | Deviates — merges allowed without rebase; acceptable                                    |
| Enforce admins                        | ✅ Enabled           | Yes                                                                                     |
| Linear history                        | ❌ Disabled          | Deviates — correct: repo merges with `--no-ff` (PR #1–#4)                               |
| Force pushes                          | ❌ Disabled          | Yes                                                                                     |
| Deletions                             | ❌ Disabled          | Yes                                                                                     |
| Conversation resolution               | ✅ Required          | Yes                                                                                     |
| Signatures / lock branch              | ❌ Disabled          | Yes (unsigned test builds)                                                              |

### Manual Configuration Steps (for reference / re-application)

1. Go to: `https://github.com/sashtriyasam/ISRO-DEPTHWIZ/settings/branches`
2. Edit the `main` rule to match the table above
3. Search for and require the 6 CI contexts by exact name

---

**Status:** CONFIGURED and VERIFIED live via API
**Authority:** Shivam (final merge authority per AGENTS.md)
