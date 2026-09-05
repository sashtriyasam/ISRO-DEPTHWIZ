# /team:review

Review a change or branch before merge. Respect `AGENTS.md`.

1. Diff against `main`. Check ownership: does the change stay inside
   the author's workstream or correctly use the integration contract?
2. Check for forbidden content: datasets, checkpoints, caches, huge
   generated files, secrets, dev-only paths.
3. Verify tests exist for claimed behavior and actually cover it.
4. Apply the scientific/geospatial checks: any metric/geospatial claim
   must point at evidence in the change.
5. Verdict: approve / request changes (with file:line pointers) /
   escalate to Shivam for semantic disputes. Never auto-merge a
   teammate's branch.
