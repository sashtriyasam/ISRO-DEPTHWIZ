# Release (DepthWizard)

You evaluate release readiness for DepthWizard.

1. Read `AGENTS.md`, `docs/project/RELEASE_GATES.md`, and
   `docs/project/PROJECT_STATUS.md`.
2. For the gate in question, check every prerequisite against repo
   evidence (tests, run logs, docs, commits).
3. Run the applicable checks (Python suite / frontend suite / build)
   where the environment allows; quote results.
4. Output: per-prerequisite PASS/MISSING with evidence pointers, then
   an overall PASS or BLOCKED verdict. No partial passes.
