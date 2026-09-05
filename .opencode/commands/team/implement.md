# /team:implement

Implement an accepted plan. Respect `AGENTS.md`.

1. Work on the agreed branch only (`feat/<owner>-<topic>`).
2. Follow the locked ownership map — do not drift into another
   workstream's segment except through the canonical contracts.
3. Keep the integration adapter transparent (no silent recalibration /
   resampling / reprojection / unit changes).
4. Add or update tests for the claimed behavior in the same change.
5. Never commit datasets, checkpoints, caches, huge generated files,
   secrets, or local env paths.
6. End with: files changed, tests run + result, and which acceptance
   criterion each change satisfies.
