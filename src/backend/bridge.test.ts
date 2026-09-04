import { describe, it, expect } from "vitest";
import { BackendBridge } from "./bridge";

describe("BackendBridge", () => {
  const bridge = new BackendBridge({
    bridgeScript: "scripts/backend_bridge.py",
  });

  describe("executeSynthetic", () => {
    it("executes the Python backend and returns a valid artifact", async () => {
      const result = await bridge.executeSynthetic(8, 8);
      expect(result.success).toBe(true);
      expect(result.artifact).toBeDefined();
      expect(result.artifact!.id).toBe("backend-synthetic-depth");
      expect(result.artifact!.elevation).toBeDefined();
      expect(result.artifact!.elevation!.width).toBe(8);
      expect(result.artifact!.elevation!.height).toBe(8);
    });

    it("preserves relative depth semantics", async () => {
      const result = await bridge.executeSynthetic(4, 4);
      expect(result.success).toBe(true);
      expect(result.artifact!.metadata.backend?.depth_scale).toBe("relative");
      expect(result.artifact!.metadata.backend?.elevation_semantics).toBe("relative_depth");
    });

    it("generates deterministic output", async () => {
      const result1 = await bridge.executeSynthetic(8, 8);
      const result2 = await bridge.executeSynthetic(8, 8);
      expect(result1.success).toBe(true);
      expect(result2.success).toBe(true);
      const grid1 = result1.artifact!.elevation!.grid;
      const grid2 = result2.artifact!.elevation!.grid;
      expect(grid1.length).toBe(grid2.length);
      for (let i = 0; i < grid1.length; i++) {
        expect(grid1[i]).toBeCloseTo(grid2[i]);
      }
    });

    it("does not fabricate metric units", async () => {
      const result = await bridge.executeSynthetic(8, 8);
      expect(result.success).toBe(true);
      expect(result.warnings.some((w) => w.includes("RELATIVE"))).toBe(true);
    });

    it("marks result as synthetic", async () => {
      const result = await bridge.executeSynthetic(8, 8);
      expect(result.success).toBe(true);
      expect(result.artifact!.metadata.source).toBe("backend");
      expect(result.artifact!.metadata.backend?.model_name).toBe("synthetic-depth");
    });

    it("includes warnings for relative data", async () => {
      const result = await bridge.executeSynthetic(8, 8);
      expect(result.success).toBe(true);
      expect(result.warnings.length).toBeGreaterThan(0);
    });

    it("creates artifact with empty mesh (depth only)", async () => {
      const result = await bridge.executeSynthetic(8, 8);
      expect(result.success).toBe(true);
      expect(result.artifact!.mesh.vertexCount).toBe(0);
      expect(result.artifact!.mesh.indexCount).toBe(0);
    });
  });

  describe("executeWithInput", () => {
    it("rejects non-existent file", async () => {
      const result = await bridge.executeWithInput("nonexistent.png");
      expect(result.success).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });
  });

  describe("error handling", () => {
    it("handles invalid bridge script path", async () => {
      const badBridge = new BackendBridge({
        bridgeScript: "nonexistent_script.py",
      });
      const result = await badBridge.executeSynthetic();
      expect(result.success).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });
  });
});
