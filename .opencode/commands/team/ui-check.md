# /team:ui-check

Gate desktop/3D/UX work. Respect `AGENTS.md`. Owner: Aryan's track.

1. Contract: scene built only from `SceneArtifact` via the transport
   client — no side-channel data, no dev-only paths.
2. Metric-vs-relative honesty: does the UI show which one the user is
   looking at (model identity, provenance, units or explicit relative
   labeling)?
3. Interaction: orbit / FP / aerial, waypoint flythrough, height /
   slope / measurement / profile tools behave against known geometry.
4. Session lifecycle: project open → process → inspect → close is
   correct; no stale state across sessions.
5. Evidence: visual (screenshot/run) + runtime (tests green,
   `npm run build` clean).
