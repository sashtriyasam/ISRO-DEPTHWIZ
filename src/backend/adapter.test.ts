import { describe, it, expect } from "vitest";
import { adaptBackendResult, adaptCalibratedResult } from "./adapter";
import type { BackendDepthResult } from "./types";
import { BACKEND_TEST_FIXTURE, BACKEND_CALIBRATION_FIXTURE, BACKEND_METRIC_FIXTURE } from "./fixtures";

function createMinimalBackendResult(overrides: Partial<BackendDepthResult> = {}): BackendDepthResult {
  return {
    model_name: "test-model",
    input_resolution: { width: 2, height: 2 },
    output_resolution: { width: 2, height: 2 },
    depth_scale: "relative",
    elevation_semantics: "relative_depth",
    georeferencing: "non_georeferenced",
    depth_values: [0.1, 0.2, 0.3, 0.4],
    spatial: { kind: "not_applicable" },
    ...overrides,
  };
}

describe("adaptBackendResult", () => {
  describe("valid backend result → SceneArtifact", () => {
    it("converts a valid relative backend result", () => {
      const result = adaptBackendResult(BACKEND_TEST_FIXTURE);
      expect(result.success).toBe(true);
      expect(result.artifact).toBeDefined();
      expect(result.artifact!.id).toBe("backend-synthetic-depth");
      expect(result.artifact!.label).toBe("synthetic-depth v0.1.0");
      expect(result.artifact!.metadata.source).toBe("backend");
    });

    it("converts a valid metric backend result", () => {
      const result = adaptBackendResult(BACKEND_METRIC_FIXTURE);
      expect(result.success).toBe(true);
      expect(result.artifact).toBeDefined();
      expect(result.artifact!.metadata.backend?.depth_scale).toBe("metric");
    });

    it("creates elevation data from depth_values", () => {
      const result = adaptBackendResult(BACKEND_TEST_FIXTURE);
      expect(result.artifact!.elevation).toBeDefined();
      expect(result.artifact!.elevation!.width).toBe(4);
      expect(result.artifact!.elevation!.height).toBe(4);
      expect(result.artifact!.elevation!.grid.length).toBe(16);
    });

    it("preserves depth_values in elevation grid", () => {
      const result = adaptBackendResult(BACKEND_TEST_FIXTURE);
      const grid = result.artifact!.elevation!.grid;
      for (let i = 0; i < 16; i++) {
        expect(grid[i]).toBeCloseTo(BACKEND_TEST_FIXTURE.depth_values[i]);
      }
    });

    it("sets units to meters", () => {
      const result = adaptBackendResult(BACKEND_TEST_FIXTURE);
      expect(result.artifact!.metadata.units.spatial).toBe("meters");
      expect(result.artifact!.metadata.units.elevation).toBe("meters");
    });

    it("includes backend origin metadata", () => {
      const result = adaptBackendResult(BACKEND_TEST_FIXTURE);
      expect(result.artifact!.metadata.backend).toBeDefined();
      expect(result.artifact!.metadata.backend!.model_name).toBe("synthetic-depth");
      expect(result.artifact!.metadata.backend!.depth_scale).toBe("relative");
      expect(result.artifact!.metadata.backend!.elevation_semantics).toBe("relative_depth");
    });

    it("creates empty mesh for backend artifacts", () => {
      const result = adaptBackendResult(BACKEND_TEST_FIXTURE);
      expect(result.artifact!.mesh.vertexCount).toBe(0);
      expect(result.artifact!.mesh.indexCount).toBe(0);
    });
  });

  describe("missing required field", () => {
    it("rejects missing model_name", () => {
      const result = adaptBackendResult(createMinimalBackendResult({ model_name: "" }));
      expect(result.success).toBe(false);
      expect(result.errors.some(e => e.code === "MISSING_MODEL_NAME")).toBe(true);
    });

    it("rejects missing output_resolution", () => {
      const result = adaptBackendResult(createMinimalBackendResult({ output_resolution: undefined as any }));
      expect(result.success).toBe(false);
      expect(result.errors.some(e => e.code === "MISSING_OUTPUT_RESOLUTION")).toBe(true);
    });

    it("rejects missing depth_values", () => {
      const result = adaptBackendResult(createMinimalBackendResult({ depth_values: undefined as any }));
      expect(result.success).toBe(false);
      expect(result.errors.some(e => e.code === "MISSING_DEPTH_VALUES")).toBe(true);
    });

    it("rejects missing depth_scale", () => {
      const result = adaptBackendResult(createMinimalBackendResult({ depth_scale: undefined as any }));
      expect(result.success).toBe(false);
      expect(result.errors.some(e => e.code === "MISSING_DEPTH_SCALE")).toBe(true);
    });

    it("rejects missing spatial", () => {
      const result = adaptBackendResult(createMinimalBackendResult({ spatial: undefined as any }));
      expect(result.success).toBe(false);
      expect(result.errors.some(e => e.code === "MISSING_SPATIAL")).toBe(true);
    });
  });

  describe("invalid dimensions", () => {
    it("rejects zero width", () => {
      const result = adaptBackendResult(createMinimalBackendResult({
        output_resolution: { width: 0, height: 2 },
      }));
      expect(result.success).toBe(false);
      expect(result.errors.some(e => e.code === "INVALID_WIDTH")).toBe(true);
    });

    it("rejects zero height", () => {
      const result = adaptBackendResult(createMinimalBackendResult({
        output_resolution: { width: 2, height: 0 },
      }));
      expect(result.success).toBe(false);
      expect(result.errors.some(e => e.code === "INVALID_HEIGHT")).toBe(true);
    });
  });

  describe("invalid array length", () => {
    it("rejects depth_values length mismatch", () => {
      const result = adaptBackendResult(createMinimalBackendResult({
        depth_values: [0.1, 0.2],
      }));
      expect(result.success).toBe(false);
      expect(result.errors.some(e => e.code === "DEPTH_VALUES_LENGTH_MISMATCH")).toBe(true);
    });

    it("rejects confidence_values length mismatch", () => {
      const result = adaptBackendResult(createMinimalBackendResult({
        confidence_values: [0.1, 0.2],
      }));
      expect(result.success).toBe(false);
      expect(result.errors.some(e => e.code === "CONFIDENCE_VALUES_LENGTH_MISMATCH")).toBe(true);
    });

    it("rejects valid_mask length mismatch", () => {
      const result = adaptBackendResult(createMinimalBackendResult({
        valid_mask: [true, false],
      }));
      expect(result.success).toBe(false);
      expect(result.errors.some(e => e.code === "VALID_MASK_LENGTH_MISMATCH")).toBe(true);
    });
  });

  describe("optional DSM/rDSM/AGL", () => {
    it("handles optional confidence_values", () => {
      const result = adaptBackendResult(createMinimalBackendResult({
        confidence_values: [0.9, 0.8, 0.7, 0.6],
      }));
      expect(result.success).toBe(true);
    });

    it("handles optional valid_mask", () => {
      const result = adaptBackendResult(createMinimalBackendResult({
        valid_mask: [true, true, false, true],
      }));
      expect(result.success).toBe(true);
    });

    it("handles null confidence_values", () => {
      const result = adaptBackendResult(createMinimalBackendResult({
        confidence_values: null,
      }));
      expect(result.success).toBe(true);
    });
  });

  describe("optional CRS and transform", () => {
    it("preserves CRS when present", () => {
      const result = adaptBackendResult(BACKEND_METRIC_FIXTURE);
      expect(result.artifact!.metadata.CRS).toBe("EPSG:4326");
    });

    it("preserves transform when present", () => {
      const result = adaptBackendResult(BACKEND_METRIC_FIXTURE);
      expect(result.artifact!.metadata.transform).toBeDefined();
      expect(result.artifact!.metadata.transform!.originX).toBe(0);
      expect(result.artifact!.metadata.transform!.pixelWidth).toBe(1);
    });

    it("preserves bounds when present", () => {
      const result = adaptBackendResult(BACKEND_METRIC_FIXTURE);
      expect(result.artifact!.metadata.bounds).toBeDefined();
      expect(result.artifact!.metadata.bounds!.minX).toBe(0);
      expect(result.artifact!.metadata.bounds!.maxX).toBe(3);
    });

    it("handles missing CRS gracefully", () => {
      const result = adaptBackendResult(BACKEND_TEST_FIXTURE);
      expect(result.artifact!.metadata.CRS).toBeUndefined();
    });
  });

  describe("units preservation", () => {
    it("preserves metric units", () => {
      const result = adaptBackendResult(BACKEND_METRIC_FIXTURE);
      expect(result.artifact!.metadata.backend?.depth_scale).toBe("metric");
    });

    it("preserves relative scale", () => {
      const result = adaptBackendResult(BACKEND_TEST_FIXTURE);
      expect(result.artifact!.metadata.backend?.depth_scale).toBe("relative");
    });
  });

  describe("layer mapping", () => {
    it("maps depth_values to elevation layer", () => {
      const result = adaptBackendResult(BACKEND_TEST_FIXTURE);
      expect(result.artifact!.elevation).toBeDefined();
      expect(result.artifact!.elevation!.grid.length).toBe(16);
    });

    it("does not create rdsm or agl layers from depth_values alone", () => {
      const result = adaptBackendResult(BACKEND_TEST_FIXTURE);
      expect(result.artifact!.layers).toBeUndefined();
    });
  });

  describe("backend object immutability", () => {
    it("does not mutate backend result", () => {
      const original = { ...BACKEND_TEST_FIXTURE };
      const originalValues = [...BACKEND_TEST_FIXTURE.depth_values];
      adaptBackendResult(BACKEND_TEST_FIXTURE);
      expect(BACKEND_TEST_FIXTURE.model_name).toBe(original.model_name);
      expect(BACKEND_TEST_FIXTURE.depth_values).toEqual(originalValues);
    });

    it("creates independent SceneArtifact", () => {
      const result1 = adaptBackendResult(BACKEND_TEST_FIXTURE);
      const result2 = adaptBackendResult(BACKEND_TEST_FIXTURE);
      expect(result1.artifact).not.toBe(result2.artifact);
      expect(result1.artifact!.elevation!.grid).not.toBe(result2.artifact!.elevation!.grid);
    });
  });

  describe("malformed artifact error messages", () => {
    it("provides actionable error for metric without meters", () => {
      const result = adaptBackendResult(createMinimalBackendResult({
        depth_scale: "metric",
        units: null,
      }));
      expect(result.success).toBe(false);
      expect(result.errors.some(e => e.code === "METRIC_UNITS_MISMATCH")).toBe(true);
    });

    it("provides actionable error for relative with meters", () => {
      const result = adaptBackendResult(createMinimalBackendResult({
        depth_scale: "relative",
        units: "meters",
      }));
      expect(result.success).toBe(false);
      expect(result.errors.some(e => e.code === "RELATIVE_UNITS_MISMATCH")).toBe(true);
    });
  });

  describe("warnings for relative data", () => {
    it("warns about relative depth scale", () => {
      const result = adaptBackendResult(BACKEND_TEST_FIXTURE);
      expect(result.warnings.some(w => w.includes("RELATIVE"))).toBe(true);
    });

    it("warns about relative_depth semantics", () => {
      const result = adaptBackendResult(BACKEND_TEST_FIXTURE);
      expect(result.warnings.some(w => w.includes("relative_depth"))).toBe(true);
    });
  });
});

describe("adaptCalibratedResult", () => {
  it("applies calibration to depth values", () => {
    const result = adaptCalibratedResult(BACKEND_TEST_FIXTURE, BACKEND_CALIBRATION_FIXTURE);
    expect(result.success).toBe(true);
    expect(result.artifact).toBeDefined();
    const grid = result.artifact!.elevation!.grid;
    for (let i = 0; i < 16; i++) {
      expect(grid[i]).toBeCloseTo(
        BACKEND_CALIBRATION_FIXTURE.scale * BACKEND_TEST_FIXTURE.depth_values[i] + BACKEND_CALIBRATION_FIXTURE.offset
      );
    }
  });

  it("creates calibrated artifact with different id", () => {
    const result = adaptCalibratedResult(BACKEND_TEST_FIXTURE, BACKEND_CALIBRATION_FIXTURE);
    expect(result.artifact!.id).toContain("calibrated");
  });

  it("includes calibration info in backend metadata", () => {
    const result = adaptCalibratedResult(BACKEND_TEST_FIXTURE, BACKEND_CALIBRATION_FIXTURE);
    expect(result.artifact!.metadata.backend?.calibration_method).toBe("scale_offset");
    expect(result.artifact!.metadata.backend?.calibration_reference).toBe("test-dem");
  });

  it("does not mutate backend result", () => {
    const originalValues = [...BACKEND_TEST_FIXTURE.depth_values];
    adaptCalibratedResult(BACKEND_TEST_FIXTURE, BACKEND_CALIBRATION_FIXTURE);
    expect(BACKEND_TEST_FIXTURE.depth_values).toEqual(originalValues);
  });

  it("rejects invalid backend result", () => {
    const result = adaptCalibratedResult(
      createMinimalBackendResult({ model_name: "" }),
      BACKEND_CALIBRATION_FIXTURE
    );
    expect(result.success).toBe(false);
  });
});
