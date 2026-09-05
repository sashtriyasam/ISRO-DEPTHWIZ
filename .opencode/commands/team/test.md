# /team:test

Run the checks for your track and report honestly.
Respect `AGENTS.md`.

- Python track: `python -m pytest`, `python -m ruff check src tests`,
  `python -m ruff format --check src tests`, `python -m mypy src tests`.
- Frontend track: `npm run typecheck`, `npm run test`, `npm run build`.
- Heavy-model / GAMUS tests are opt-in only — never pull large models
  or datasets as part of a routine check.
- Report pass/fail per command with the failing output quoted. A red
  suite is a finding, not a cue to weaken the test.
