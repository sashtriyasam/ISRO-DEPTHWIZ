# /team:plan

Plan a unit of DepthWizard work against the control plane.
Respect `AGENTS.md`.

1. Identify the epic + SIH requirement row
   (`docs/project/SIH_REQUIREMENT_TRACEABILITY.md`) and the release
   gate (`docs/project/RELEASE_GATES.md`) the work serves.
2. State owner, track, SIH Area, verification type, dependencies, and
   acceptance criteria up front.
3. Check `docs/project/INTEGRATION_CONTRACT.md` if the work touches or
   crosses the backend↔desktop boundary.
4. If the work makes a scientific/metric/geospatial claim, name the
   evidence that will support it before writing code.
5. Output a short plan (scope, files, tests, evidence). Do not start
   implementing until the plan is accepted.
