# /team:release-check

Evaluate a release gate. Respect `AGENTS.md` +
`docs/project/RELEASE_GATES.md`.

1. State the gate and its prerequisites verbatim from RELEASE_GATES.md.
2. For each prerequisite, cite evidence (test suite, run log, doc,
   commit) or mark it missing.
3. Apply the verification type the gate demands (unit / integration /
   scientific / runtime / visual / end-to-end).
4. Verdict: PASS (all prerequisites evidenced) or BLOCKED (list exactly
   what is missing and who owns it). Partial passes are not a thing —
   record the gap.
