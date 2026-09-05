import { describe, it, expect } from "vitest";
import { BackendBridge } from "../backend/bridge";
import { applyHeightExaggeration } from "../display/types";
import { createLayerState } from "../layers/LayerRegistry";
import { describeArtifact } from "../metadata/metadata";
import { validateInputFile } from "./validation";
import {
  ApplicationBackendSource,
  APPLICATION_BACKEND_LABEL,
  DEFAULT_TARGET_SEMANTICS,
} from "./applicationSource";
import { makeTestPng, makeClientFile } from "./testFixtures";

const SUFFIXES = [".jpeg", ".jpg", ".png", ".tif", ".tiff"];
const bridge = new BackendBridge({ bridgeScript: "scripts/backend_bridge.py" });

async function validatedTile() {
  return validateInputFile(
    makeClientFile("tile.png", makeTestPng(4, 4), "image/png"),
    {
      bridge,
      supportedSuffixes: SUFFIXES,
    },
  );
}

describe("ApplicationBackendSource", () => {
  it("unifies file intent behind one backend source", async () => {
    const validated = await validatedTile();
    try {
      const source = new ApplicationBackendSource({
        stagedPath: validated.stagedPath,
        metadata: validated.metadata,
      });
      expect(source.kind).toBe("file");
      expect(source.targetSemantics).toBe(DEFAULT_TARGET_SEMANTICS);
      expect(source.backendLabel).toBe(APPLICATION_BACKEND_LABEL);
      expect(source.id).toMatch(/^file-[0-9a-f]{16}$/);
      expect(source.label).toBe("tile.png");
      const artifact = await source.load();
      expect(artifact.metadata.backend?.elevation_semantics).toBe(
        "absolute_elevation_dsm",
      );
      expect(artifact.metadata.backend?.depth_scale).toBe("metric");
    } finally {
      await validated.cleanup();
    }
  });

  it("labels the synthetic backend explicitly as development", async () => {
    const validated = await validatedTile();
    try {
      const source = new ApplicationBackendSource({
        stagedPath: validated.stagedPath,
        metadata: validated.metadata,
      });
      expect(source.kind).toBe("file");
      expect(source.backendLabel).toBe("Synthetic Development Backend");
      expect(source.backendLabel).not.toContain("Production");
      expect(source.label).toBe("tile.png");
    } finally {
      await validated.cleanup();
    }
  });

  it("carries provenance to the metadata workspace without touching the artifact", async () => {
    const validated = await validatedTile();
    try {
      const source = new ApplicationBackendSource({
        stagedPath: validated.stagedPath,
        metadata: validated.metadata,
      });
      const artifact = await source.load();
      const before = JSON.stringify({
        grid: Array.from(artifact.elevation!.grid),
        backend: artifact.metadata.backend,
      });
      const sections = describeArtifact(artifact, "dsm");
      const provenance = sections.find((s) => s.id === "provenance")!;
      expect(
        provenance.rows.some((r) => r.value.includes("synthetic-depth")),
      ).toBe(true);
      const after = JSON.stringify({
        grid: Array.from(artifact.elevation!.grid),
        backend: artifact.metadata.backend,
      });
      expect(after).toBe(before);
    } finally {
      await validated.cleanup();
    }
  });

  it("leaves the source artifact unchanged by display exaggeration", async () => {
    const validated = await validatedTile();
    try {
      const source = new ApplicationBackendSource({
        stagedPath: validated.stagedPath,
        metadata: validated.metadata,
      });
      const artifact = await source.load();
      const gridBefore = Array.from(artifact.elevation!.grid);
      const verticesBefore = Array.from(artifact.mesh.vertices);
      const display = applyHeightExaggeration(artifact.mesh.vertices, 10);
      expect(Array.from(display)).not.toEqual(verticesBefore);
      expect(Array.from(artifact.elevation!.grid)).toEqual(gridBefore);
      expect(Array.from(artifact.mesh.vertices)).toEqual(verticesBefore);
    } finally {
      await validated.cleanup();
    }
  });

  it("propagates the requested target semantics end to end", async () => {
    const validated = await validatedTile();
    try {
      const source = new ApplicationBackendSource({
        stagedPath: validated.stagedPath,
        metadata: validated.metadata,
        targetSemantics: "height_agl_ndsm",
      });
      const artifact = await source.load();
      expect(artifact.metadata.backend?.elevation_semantics).toBe(
        "height_agl_ndsm",
      );
      expect(artifact.elevation!.unit).toBe("meters");
      const layers = createLayerState(artifact);
      const dsm = layers.layers.find((l) => l.id === "dsm");
      expect(dsm!.label).toBe("Height Above Ground (AGL)");
    } finally {
      await validated.cleanup();
    }
  });

  it("exposes the synthetic development path explicitly", async () => {
    const source = new ApplicationBackendSource({
      syntheticSize: { width: 4, height: 4 },
    });
    expect(source.kind).toBe("synthetic");
    expect(source.id).toBe("backend-synthetic");
    expect(source.label).toBe(APPLICATION_BACKEND_LABEL);
    const artifact = await source.load();
    expect(artifact.metadata.backend?.model_name).toBe("synthetic-depth");
  });

  it("reloads deterministically for retry without reselecting input", async () => {
    const validated = await validatedTile();
    try {
      const source = new ApplicationBackendSource({
        stagedPath: validated.stagedPath,
        metadata: validated.metadata,
      });
      const first = await source.load();
      const second = await source.load();
      expect(first.id).toBe(second.id);
      expect(Array.from(first.elevation!.grid)).toEqual(
        Array.from(second.elevation!.grid),
      );
      expect(Array.from(first.mesh.vertices)).toEqual(
        Array.from(second.mesh.vertices),
      );
    } finally {
      await validated.cleanup();
    }
  });

  it("labels a real backend by model instead of synthetic", () => {
    const source = new ApplicationBackendSource({
      backend: "depth-anything-v2-small",
    });
    expect(source.backendLabel).toBe("Backend model (depth-anything-v2-small)");
    expect(source.backendLabel).not.toBe("Synthetic Development Backend");
  });

  it("keeps the synthetic label when no backend is requested", () => {
    expect(new ApplicationBackendSource({}).backendLabel).toBe(
      APPLICATION_BACKEND_LABEL,
    );
  });
});
