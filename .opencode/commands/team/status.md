# /team:status

Report true project status from evidence, not from plans.
Respect `AGENTS.md`.

1. Read `docs/project/PROJECT_STATUS.md` and the gate relevant to the
   asker's track in `docs/project/RELEASE_GATES.md`.
2. Inspect the actual repo: changed files, recent commits on the work
   branch, test results if available.
3. If the GitHub Project is reachable, reconcile item statuses for the
   asker's Owner view against repo evidence.
4. Output: per-area status (Done / Integration / Review / In Progress /
   Blocked / Backlog) with one evidence pointer each. Mark uncertainty
   explicitly. Never inflate completion.
