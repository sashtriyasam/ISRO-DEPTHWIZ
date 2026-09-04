import { describe, it, expect } from "vitest";
import type { SceneArtifact } from "../types/scene";
import { createDeterministicFixture } from "../fixtures/deterministicFixture";
import {
  NOT_AVAILABLE,
  activeGrid,
  describeArtifact,
  formatAffine,
  formatChecksum,
  formatScalar,
  georeferencingLabel,
  semanticLabel,
  sourceStatusLabel,
  unitLabel,
} from "./metadata";

function metricArtifact(): SceneArtifact {
  return {
    id: "backend-synthetic-depth-terrain",
    label: "synthetic-depth terrain",
    mesh: { vertices: new Float32Array(0), indices: new Uint32Array(0), vertexCount: 0, indexCount: 0 },
    elevation: { grid: new Float32Array([10, 11, 12, 13]), width: 2, height: 2, cellSize: 1, unit: "meters" },
    metadata: {
      source: "backend",
      units: { spatial: "meters", elevation: "meters" },
      CRS: "EPSG:32643",
      transform: { originX: 100, originY: 200, pixelWidth: 0.5, pixelHeight: -0.5 },
      bounds: { minX: 0, minY: 10, minZ: 0, maxX: 1, maxY: 13, maxZ: 1 },
      backend: {
        model_name: "synthetic-depth",
        model_version: "0.1.0",
        depth_scale: "metric",
        elevation_semantics: "absolute_elevation_dsm",
        georeferencing: "georeferenced_no_elevation_reference",
        calibration_method: "scale_offset",
        calibration_reference: "synthetic-dev-ref",
        calibration_scale: 2.5,
        calibration_offset: 10.0,
        input_id: "tile.png",
        input_checksum: "a".repeat(64),
        software_version: "0.1.0",
        semantic_meaning: "absolute_elevation_dsm",
      },
      spatialDetails: {
        gsd: 0.5,
        nodata: 0,
        rasterWidth: 5,
        rasterHeight: 4,
        spatialUnits: "meters",
        source: "geotiff-header",
        affine: [100, 0.5, 0, 200, 0, -0.5],
        spatialBounds: { minX: 100, minY: 198, maxX: 102.5, maxY: 200 },
      },
    },
  };
}

function sectionOf(artifact: SceneArtifact, layer: "dsm" = "dsm", id: string) {
  const sections = describeArtifact(artifact, layer);
  return sections.find((s) => s.id === id)!;
}

function rowOf(artifact: SceneArtifact, section: string, label: string): string {
  const rows = sectionOf(artifact, "dsm", section).rows;
  return rows.find((r) => r.label === label)!.value;
}

describe("semantic and unit labels", () => {
  it("maps all backend semantics to human labels", () => {
    expect(semanticLabel("absolute_elevation_dsm")).toBe("Absolute elevation (DSM)");
    expect(semanticLabel("height_agl_ndsm")).toBe("Height above ground (AGL)");
    expect(semanticLabel("relative_surface_rdsm")).toBe("Relative surface (rDSM)");
    expect(semanticLabel("relative_depth")).toBe("Relative depth");
    expect(semanticLabel(undefined)).toBe(NOT_AVAILABLE);
    expect(semanticLabel("future_kind")).toBe("future_kind");
  });

  it("never invents units", () => {
    expect(unitLabel("meters")).toBe("meters");
    expect(unitLabel("relative")).toBe("relative");
    expect(unitLabel(undefined)).toBe(NOT_AVAILABLE);
    expect(unitLabel(null)).toBe(NOT_AVAILABLE);
    expect(unitLabel("")).toBe(NOT_AVAILABLE);
  });

  it("labels georeferencing levels without inference", () => {
    expect(georeferencingLabel("non_georeferenced")).toBe("Non-georeferenced");
    expect(georeferencingLabel("georeferenced_with_dem")).toBe("Georeferenced (DEM)");
    expect(georeferencingLabel(undefined)).toBe(NOT_AVAILABLE);
  });

  it("distinguishes fixture, synthetic, and named backends", () => {
    const fixture = createDeterministicFixture();
    expect(sourceStatusLabel(fixture.metadata)).toBe("Development fixture");
    expect(sourceStatusLabel(metricArtifact().metadata)).toBe("Synthetic Development Backend");
    expect(
      sourceStatusLabel({
        source: "backend",
        units: { spatial: "meters", elevation: "meters" },
        backend: {
          model_name: "depth-anything-v2",
          depth_scale: "metric",
          elevation_semantics: "absolute_elevation_dsm",
          georeferencing: "georeferenced_with_dem",
        },
      })
    ).toBe("Backend model (depth-anything-v2)");
  });
});

describe("scalar formatting", () => {
  it("keeps null, NaN, and zero distinct", () => {
    expect(formatScalar(undefined)).toBe(NOT_AVAILABLE);
    expect(formatScalar(null)).toBe(NOT_AVAILABLE);
    expect(formatScalar(NaN)).toBe("NaN (nodata marker)");
    expect(formatScalar(0)).toBe("0");
    expect(formatScalar(0.5)).toBe("0.5");
  });

  it("truncates checksums with full value on title", () => {
    expect(formatChecksum(undefined)).toEqual({ short: NOT_AVAILABLE });
    expect(formatChecksum("abc")).toEqual({ short: "abc" });
    const full = "a".repeat(64);
    const result = formatChecksum(full);
    expect(result.short).toContain("…");
    expect(result.full).toBe(full);
  });

  it("renders the backend affine in documented GDAL order", () => {
    expect(formatAffine([100, 0.5, 0, 200, 0, -0.5])).toBe("100, 0.5, 0 / 200, 0, -0.5");
  });
});

describe("describeArtifact for a complete metric product", () => {
  it("renders every section from authoritative fields", () => {
    const artifact = metricArtifact();
    const ids = describeArtifact(artifact, "dsm").map((s) => s.id);
    expect(ids).toEqual(["product", "spatial", "calibration", "provenance", "input"]);
    expect(rowOf(artifact, "product", "Product")).toBe("Absolute elevation (DSM)");
    expect(rowOf(artifact, "product", "Scale")).toBe("metric");
    expect(rowOf(artifact, "product", "Units")).toBe("meters");
    expect(rowOf(artifact, "product", "Artifact")).toBe("backend-synthetic-depth-terrain");
    expect(rowOf(artifact, "product", "Grid")).toBe("2×2 (meters)");
    expect(rowOf(artifact, "spatial", "CRS")).toBe("EPSG:32643");
    expect(rowOf(artifact, "spatial", "Reference")).toBe("Georeferenced (no elevation reference)");
    expect(rowOf(artifact, "spatial", "GSD")).toBe("0.5");
    expect(rowOf(artifact, "spatial", "Raster")).toBe("5×4");
    expect(rowOf(artifact, "spatial", "Nodata")).toBe("0");
    expect(rowOf(artifact, "spatial", "Affine")).toBe("100, 0.5, 0 / 200, 0, -0.5");
    expect(rowOf(artifact, "spatial", "Spatial bounds")).toBe("X [100, 102.5] Y [198, 200]");
    expect(rowOf(artifact, "spatial", "Display bounds")).toContain("X [0, 1]");
    expect(rowOf(artifact, "calibration", "Method")).toBe("scale_offset");
    expect(rowOf(artifact, "calibration", "Reference")).toBe("synthetic-dev-ref");
    expect(rowOf(artifact, "calibration", "Scale")).toBe("2.5");
    expect(rowOf(artifact, "calibration", "Offset")).toBe("10");
    expect(rowOf(artifact, "provenance", "Backend")).toBe("synthetic-depth 0.1.0");
    expect(rowOf(artifact, "provenance", "Source")).toBe("Synthetic Development Backend");
    expect(rowOf(artifact, "provenance", "Software")).toBe("0.1.0");
    expect(rowOf(artifact, "input", "File")).toBe("tile.png");
    expect(rowOf(artifact, "input", "Checksum")).toContain("…");
  });

  it("omits the calibration section without calibration facts", () => {
    const artifact = createDeterministicFixture();
    const ids = describeArtifact(artifact, "dsm").map((s) => s.id);
    expect(ids).not.toContain("calibration");
    expect(ids).toEqual(["product", "spatial", "provenance", "input"]);
  });
});

describe("missing data behavior", () => {
  it("uses a single consistent fallback", () => {
    const artifact = createDeterministicFixture();
    const spatial = sectionOf(artifact, "dsm", "spatial").rows;
    const byLabel = Object.fromEntries(spatial.map((r) => [r.label, r.value]));
    expect(byLabel["CRS"]).toBe("TEST-CRS-001");
    expect(byLabel["GSD"]).toBe(NOT_AVAILABLE);
    expect(byLabel["Nodata"]).toBe(NOT_AVAILABLE);
    expect(byLabel["Grid transform"]).toContain("origin");
    expect(byLabel["Transform"]).toBeUndefined();
    expect(spatial.find((r) => r.label === "Raster")).toBeUndefined();
    expect(spatial.find((r) => r.label === "Affine")).toBeUndefined();
    expect(spatial.find((r) => r.label === "Spatial bounds")).toBeUndefined();
  });

  it("shows fixture grid facts without backend claims", () => {
    const artifact = createDeterministicFixture();
    expect(rowOf(artifact, "product", "Scale")).toBe(NOT_AVAILABLE);
    expect(rowOf(artifact, "product", "Units")).toBe("meters");
    expect(rowOf(artifact, "product", "Grid")).toBe("8×8 (meters)");
    expect(rowOf(artifact, "provenance", "Source")).toBe("Development fixture");
    expect(rowOf(artifact, "input", "File")).toBe(artifact.label);
  });
});

describe("layer-aware derivation", () => {
  it("reflects rdsm/agl payloads when selected", () => {
    const artifact = createDeterministicFixture();
    const rdsm = activeGrid(artifact, "rdsm")!;
    expect(rdsm.kindLabel).toBe("Relative surface (rDSM)");
    expect(rdsm.width).toBe(8);
    const agl = activeGrid(artifact, "agl")!;
    expect(agl.kindLabel).toBe("Height above ground (AGL)");
    expect(describeArtifact(artifact, "rdsm").find((s) => s.id === "product")!.rows[0].value).toBe(
      "Relative surface (rDSM)"
    );
  });

  it("returns null for unavailable layer payloads", () => {
    expect(activeGrid(metricArtifact(), "rdsm")).toBeNull();
    expect(activeGrid(metricArtifact(), "agl")).toBeNull();
  });

  it("returns null without elevation data", () => {
    const artifact: SceneArtifact = {
      ...metricArtifact(),
      elevation: undefined,
    };
    expect(activeGrid(artifact, "dsm")).toBeNull();
  });
});

describe("derivation purity", () => {
  it("is a pure function of artifact and layer (exaggeration-invariant)", () => {
    const artifact = metricArtifact();
    const first = JSON.stringify(describeArtifact(artifact, "dsm"));
    const second = JSON.stringify(describeArtifact(artifact, "dsm"));
    expect(first).toBe(second);
    expect(first).not.toContain("exaggerat");
  });

  it("never embeds per-pixel data regardless of grid size", () => {
    const artifact = metricArtifact();
    artifact.elevation = {
      grid: new Float32Array(1000 * 1000),
      width: 1000,
      height: 1000,
      cellSize: 1,
      unit: "meters",
    };
    const text = JSON.stringify(describeArtifact(artifact, "dsm"));
    expect(text.length).toBeLessThan(3000);
    expect(text).toContain("1000×1000");
  });
});
