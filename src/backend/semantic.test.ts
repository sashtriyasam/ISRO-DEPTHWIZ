import { describe, it, expect } from "vitest";
import { BackendBridge } from "./bridge";
import { adaptBackendResult } from "./adapter";
import { createLayerState } from "../layers/LayerRegistry";

describe("end-to-end semantic identity", () => {
  const bridge = new BackendBridge({
    bridgeScript: "scripts/backend_bridge.py",
  });

  it("backend output preserves semantic identity through the full pipeline", async () => {
    const result = await bridge.executeSynthetic(8, 8);
    expect(result.success).toBe(true);

    const artifact = result.artifact!;
    expect(artifact.metadata.backend).toBeDefined();
    expect(artifact.metadata.backend!.depth_scale).toBe("relative");
    expect(artifact.metadata.backend!.elevation_semantics).toBe("relative_depth");
    expect(artifact.metadata.backend!.model_name).toBe("synthetic-depth");
    expect(artifact.elevation!.unit).toBe("relative");
  });

  it("layer labels reflect backend semantics", async () => {
    const result = await bridge.executeSynthetic(8, 8);
    const artifact = result.artifact!;
    const layerState = createLayerState(artifact);

    const dsmLayer = layerState.layers.find((l) => l.id === "dsm");
    expect(dsmLayer).toBeDefined();
    expect(dsmLayer!.label).toBe("Relative Depth");
    expect(dsmLayer!.description).toContain("relative depth");
    expect(dsmLayer!.description).toContain("not metric");
  });

  it("no duplicate backend formula exists in TypeScript", () => {
    const fs = require("fs");
    const path = require("path");

    const srcDir = path.resolve(__dirname, "..");
    const files = [
      "backend/bridge.ts",
      "backend/source.ts",
      "backend/adapter.ts",
      "fixtures/deterministicFixture.ts",
    ];

    for (const file of files) {
      const content = fs.readFileSync(path.join(srcDir, file), "utf-8");
      expect(content).not.toContain("0.5 * (1 + Math.sin");
      expect(content).not.toContain("sin(2 * Math.PI");
      expect(content).not.toContain("cos(2 * Math.PI");
    }
  });

  it("relative depth never displays as meters", () => {
    const result = adaptBackendResult({
      model_name: "synthetic-depth",
      input_resolution: { width: 2, height: 2 },
      output_resolution: { width: 2, height: 2 },
      depth_scale: "relative",
      elevation_semantics: "relative_depth",
      georeferencing: "non_georeferenced",
      depth_values: [0.1, 0.2, 0.3, 0.4],
      spatial: { kind: "not_applicable" },
    });

    expect(result.success).toBe(true);
    expect(result.artifact!.elevation!.unit).toBe("relative");
    expect(result.warnings.some((w) => w.includes("RELATIVE"))).toBe(true);
  });

  it("metric depth displays as meters", () => {
    const result = adaptBackendResult({
      model_name: "metric-model",
      input_resolution: { width: 2, height: 2 },
      output_resolution: { width: 2, height: 2 },
      depth_scale: "metric",
      elevation_semantics: "absolute_elevation_dsm",
      georeferencing: "georeferenced_with_dem",
      depth_values: [100, 200, 300, 400],
      units: "meters",
      spatial: { kind: "not_applicable" },
    });

    expect(result.success).toBe(true);
    expect(result.artifact!.elevation!.unit).toBe("meters");
  });

  it("synthetic results are clearly identified as synthetic", async () => {
    const result = await bridge.executeSynthetic(8, 8);
    const artifact = result.artifact!;

    expect(artifact.metadata.backend!.model_name).toBe("synthetic-depth");
    expect(artifact.metadata.backend!.model_version).toBe("0.1.0");
    expect(artifact.label).toContain("synthetic-depth");
  });
});
