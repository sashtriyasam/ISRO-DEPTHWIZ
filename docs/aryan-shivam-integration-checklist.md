# Aryan–Shivam Integration Checklist

Execute after `git merge feat/aryan-integration-ready` into the Shivam target branch.

## Repository

- [ ] Branch is clean: `git status --short` shows nothing
- [ ] Merge commit exists: `git log --oneline -3`
- [ ] Diff is correct: `git diff HEAD~1 --stat` shows expected files

## Frontend

```bash
npm install
npx tsc --noEmit
npx vitest run
npm run build
```

- [ ] `npm install` completes without errors
- [ ] `npx tsc --noEmit` passes (zero errors)
- [ ] `npx vitest run` shows 585+ tests passing
- [ ] `npm run build` produces `dist/` successfully

## Backend

```bash
python -m pytest tests/
python -m ruff check
python -m ruff format --check
```

- [ ] `python -m pytest tests/` shows 307+ passing (52 affine failures are pre-existing)
- [ ] `python -m ruff check` passes
- [ ] `python -m ruff format --check` passes

## Runtime

```bash
npm run dev
# Open browser to localhost:5173
```

- [ ] Application loads without console errors
- [ ] "Use development fixture" button works
- [ ] Terrain mesh renders in viewer
- [ ] Camera orbit works (drag to rotate)
- [ ] Camera zoom works (scroll)
- [ ] Layer switching works (DSM/AGL tabs)
- [ ] Height exaggeration slider works
- [ ] Rendering mode toggle works (shaded/wireframe/combined)

## Cross-Boundary

- [ ] Backend capabilities load (Supported formats shown)
- [ ] File validation works (drop a .tif file)
- [ ] "Generate terrain" button enables when input validated
- [ ] Processing stages display correctly
- [ ] Backend metadata appears in MetadataPanel
- [ ] Checksum linkage is verified (no transport errors)

## UX

- [ ] Input workspace shows host detection ("Desktop" or "Browser")
- [ ] Processing panel shows stages and progress
- [ ] Camera controls show mode buttons (Orbit/First-Person/Aerial)
- [ ] Flythrough panel shows waypoint list
- [ ] Measurement tool activates (click two points)
- [ ] Profile tool activates (click two points)
- [ ] Inspector shows point metadata on click
- [ ] Session status shows phase ("Ready" when artifact loaded)
- [ ] "Reset Workspace" button clears all state
- [ ] "modified" badge appears when waypoints/measurement/profile exist

## Known Issues

- [ ] 52 backend tests fail due to `affine 2.4.0` environment incompatibility (NOT a code defect)
- [ ] Build produces ~831KB bundle (code splitting recommended for future optimization)

## If Something Fails

1. Check if the failure exists on `feat/aryan-integration-ready` before the merge
2. Check if the failure exists on `origin/main` before the merge
3. If it exists on neither, it's a merge interaction — report with exact error
4. If it exists on Aryan's branch, it's a pre-existing issue — classify accordingly
