# /team:preflight

Verify the operator's starting state before any DepthWizard work.
Respect `AGENTS.md`. Never invent evidence.

1. Run: `git status --short --branch`, `git log --oneline -5`,
   `git branch -vv` (read-only; never destructive commands).
2. Confirm current branch matches your owner prefix
   (`feat/shivam-*`, `feat/shravan-*`, `feat/aryan-*`) or is a shared
   branch you were explicitly asked to use.
3. Read `docs/project/PROJECT_STATUS.md` for the current evidence-based
   state.
4. If the GitHub Project is reachable, check your Owner view for items
   in `In Progress` / `Blocked` before starting new work.
5. Report: branch, working-tree state, your open items, and the gate
   your next work serves. Stop if the tree is dirty — ask, don't stash
   blindly.
