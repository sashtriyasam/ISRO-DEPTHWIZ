# Team Git (DepthWizard)

- Branch from `main` as `feat/<owner>-<topic>`, one concern per branch.
- Never `git reset --hard`, `git clean -fd`, `git checkout -- .`,
  force push, history rewrites, or teammate-branch deletion.
- Push normally; open a PR; never auto-merge a teammate's branch.
- Commit style: conventional (`feat(core): …`, `fix(app): …`,
  `test(…)`, `docs(…)`, `chore(governance): …`).
- Governance-only branches contain only governance files.
