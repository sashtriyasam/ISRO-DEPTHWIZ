# Team Testing (DepthWizard)

- Python: `python -m pytest`; `python -m ruff check src tests`;
  `python -m ruff format --check src tests`; `python -m mypy src tests`
  (strict; third-party stubs already handled in `pyproject.toml`).
- Frontend: `npm run typecheck`, `npm run test`, `npm run build`.
- Heavy-model tests are opt-in (env-gated); ordinary CI never downloads
  GAMUS, checkpoints, or HF caches.
- Failing tests are findings. Never weaken a test to make a suite pass;
  fix the code or record the blocker on the owning issue.
