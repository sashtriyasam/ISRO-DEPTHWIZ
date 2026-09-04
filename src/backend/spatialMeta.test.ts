import { describe, it, expect } from "vitest";
import { adaptBackendResult, adaptCalibratedResult } from "./adapter";
import { adaptTerrainProduct } from "./meshAdapter";
import { mapSpatialDetails, applyProvenance } from "./spatialMeta";
import {
  BACKEND_TEST_FIXTURE,
  BACKEND_CALIBRATION_FIXTURE,
  BACKEND_METRIC_FIXTURE,
} from "./fixtures";
import type { BackendDepthResult } from "./types";

describe("mapSpatialDetails", () => {
  it("returns undefined without details", () => {
    expect(mapSpatialDetails(undefined)).toBeUndefined();
    expect(mapSpatialDetails(null)).toBeUndefined();
    expect(mapSpatialDetails({})).toBeUndefined();
  });

  it("maps every authoritative field verbatim", () => {
    const mapped = mapSpatialDetails({
      crs: "EPSG:32643",
      transform: { a: 100, b: 0.5, c: 0, d: 200, e: 0, f: -0.5 },
      bounds: { min_x: 100, min_y: 198, max_x: 102.5, max_y: 200 },
      resolution_gsd: 0.5,
      nodata: 0,
      raster_width: 5,
      raster_height: 4,
      units: "meters",
      source: "geotiff-header",
    })!;
    expect(mapped.gsd).toBe(0.5);
    expect(mapped.nodata).toBe(0);
    expect(mapped.rasterWidth).toBe(5);
    expect(mapped.rasterHeight).toBe(4);
    expect(mapped.spatialUnits).toBe("meters");
    expect(mapped.source).toBe("geotiff-header");
    expect(mapped.affine).toEqual([100, 0.5, 0, 200, 0, -0.5]);
    expect(mapped.spatialBounds).toEqual({ minX: 100, minY: 198, maxX: 102.5, maxY: 200 });
  });

  it("keeps an explicit zero nodata distinct from absent", () => {
    expect(mapSpatialDetails({ nodata: 0 })?.nodata).toBe(0);
    expect(mapSpatialDetails({})).toBeUndefined();
  });
});

describe("applyProvenance", () => {
  it("copies only present provenance facts", () => {
    const backend: NonNullable<ReturnType<typeof adaptBackendResult>["artifact"]>["metadata"]["backend"] = {
      model_name: "m",
      depth_scale: "relative",
      elevation_semantics: "relative_depth",
      georeferencing: "non_georeferenced",
    };
    applyProvenance(backend, {
      source_input_id: "tile.png",
      input_checksum: "abc",
      software_version: "0.1.0",
      semantic_meaning: "relative_depth",
    });
    expect(backend.input_id).toBe("tile.png");
    expect(backend.input_checksum).toBe("abc");
    expect(backend.software_version).toBe("0.1.0");
    expect(backend.semantic_meaning).toBe("relative_depth");
  });

  it("ignores absent provenance", () => {
    const backend = {
      model_name: "m",
      depth_scale: "relative" as const,
      elevation_semantics: "relative_depth",
      georeferencing: "non_georeferenced",
    };
    applyProvenance(backend, undefined);
    applyProvenance(backend, null);
    expect(backend).toEqual({
      model_name: "m",
      depth_scale: "relative",
      elevation_semantics: "relative_depth",
      georeferencing: "non_georeferenced",
    });
  });
});

describe("adapter provenance and spatial preservation", () => {
  it("preserves backend provenance on depth results", () => {
    const result = adaptBackendResult(BACKEND_TEST_FIXTURE);
    const backend = result.artifact!.metadata.backend!;
    expect(backend.input_id).toBe("test-input.png");
    expect(backend.input_checksum).toBe("a".repeat(64));
    expect(backend.software_version).toBe("0.1.0");
    expect(backend.semantic_meaning).toBe("relative_depth from synthetic development backend");
  });

  it("preserves spatial details on metric results", () => {
    const result = adaptBackendResult(BACKEND_METRIC_FIXTURE);
    const details = result.artifact!.metadata.spatialDetails!;
    expect(result.artifact!.metadata.CRS).toBe("EPSG:4326");
    expect(details.rasterWidth).toBe(4);
    expect(details.rasterHeight).toBe(4);
    expect(details.spatialUnits).toBe("meters");
    expect(details.affine).toEqual([0, 1, 0, 0, 0, 1]);
    expect(details.spatialBounds).toEqual({ minX: 0, minY: 0, maxX: 3, maxY: 3 });
  });

  it("records calibration scale and offset", () => {
    const result = adaptCalibratedResult(BACKEND_TEST_FIXTURE, BACKEND_CALIBRATION_FIXTURE);
    const backend = result.artifact!.metadata.backend!;
    expect(backend.calibration_method).toBe("scale_offset");
    expect(backend.calibration_reference).toBe("test-dem");
    expect(backend.calibration_scale).toBe(100);
    expect(backend.calibration_offset).toBe(0);
  });

  it("leaves spatial details absent when the backend provides none", () => {
    const bare: BackendDepthResult = {
      ...BACKEND_TEST_FIXTURE,
      provenance: undefined,
      spatial: { kind: "not_applicable" },
    };
    const result = adaptBackendResult(bare);
    expect(result.artifact!.metadata.spatialDetails).toBeUndefined();
    expect(result.artifact!.metadata.backend?.input_checksum).toBeUndefined();
  });
});

describe("terrain adapter preservation", () => {
  async function realTerrain() {
    const { BackendBridge } = await import("./bridge");
    const bridge = new BackendBridge({ bridgeScript: "scripts/backend_bridge.py" });
    const staged = await bridge.stageInputBytes(
      (await import("../input/testFixtures")).makeTestPng(4, 4),
      "tile.png"
    );
    try {
      return await bridge.fetchTerrainPayload(staged.path);
    } finally {
      await staged.cleanup();
    }
  }

  it("preserves calibration, provenance, and spatial facts", async () => {
    const product = await realTerrain();
    const result = adaptTerrainProduct(product);
    const backend = result.artifact!.metadata.backend!;
    expect(backend.calibration_scale).toBe(2.5);
    expect(backend.calibration_offset).toBe(10);
    expect(backend.calibration_reference).toBe("synthetic-dev-ref");
    expect(backend.input_checksum).toMatch(/^[0-9a-f]{64}$/);
    expect(backend.software_version).toBe("0.1.0");
    expect(result.artifact!.metadata.spatialDetails).toBeUndefined();
  });
});
