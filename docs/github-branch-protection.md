# Branch Protection Configuration

**Repository:** sashtriyasam/ISRO-DEPTHWIZ
**Branch:** main
**Date:** 2026-09-06

## Current Status

**Branch Protection:** ⚠️ NOT CONFIGURED
**GitHub Actions CI:** ⚠️ NOT CONFIGURED (created in this session)

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

### Manual Configuration Steps

Since GitHub App permissions may not allow automated configuration, apply manually:

1. Go to: `https://github.com/sashtriyasam/ISRO-DEPTHWIZ/settings/branches`
2. Click "Add branch protection rule"
3. Branch name pattern: `main`
4. Check all required settings above
5. Search for and add the 5 required status checks by exact name
6. Click "Create" or "Save changes"

### Verification

After configuration, test by:

1. Creating a test branch with a failing change
2. Opening a PR — should show status checks
3. Verify merge is blocked until all checks pass
4. Verify force push is rejected
5. Verify branch deletion is rejected

---

**Status:** DOCUMENTED — Manual configuration required through GitHub UI
**Authority:** Shivam (final merge authority per AGENTS.md)
