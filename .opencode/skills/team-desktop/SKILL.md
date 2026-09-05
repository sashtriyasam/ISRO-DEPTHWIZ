# Team Desktop (DepthWizard)

- Stack: React/TypeScript + Three.js (`src/`). Consume
  `SceneArtifact` through the transport client only.
- Owns: project/input workflow, session lifecycle, scene creation,
  camera system (orbit/FP/aerial), waypoint flythrough, height/slope/
  measurement/profile tools, layers, rendering modes, metadata display,
  native host + installer.
- UI must show metric-vs-relative status (units or explicit relative
  labeling + model identity + provenance).
- Validate against known geometry; record visual + runtime evidence.
