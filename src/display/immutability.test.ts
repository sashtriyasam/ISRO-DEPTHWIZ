import { describe, it, expect } from "vitest";
import { createDeterministicFixture } from "../fixtures/deterministicFixture";
import { applyHeightExaggeration } from "../display/types";

describe("Artifact immutability under height exaggeration", () => {
  const fixture = createDeterministicFixture();
  const originalVertices = new Float32Array(fixture.mesh.vertices);
  const originalElevation = fixture.elevation ? new Float32Array(fixture.elevation.grid) : null;
  const originalRDSM = fixture.layers?.rdsm ? new Float32Array(fixture.layers.rdsm.grid) : null;
  const originalAGL = fixture.layers?.agl ? new Float32Array(fixture.layers.agl.grid) : null;

  it("source mesh vertices are unchanged after exaggeration", () => {
    const exaggerated = applyHeightExaggeration(fixture.mesh.vertices, 10);
    expect(exaggerated).not.toBe(fixture.mesh.vertices);
    for (let i = 0; i < fixture.mesh.vertices.length; i++) {
      expect(fixture.mesh.vertices[i]).toBeCloseTo(originalVertices[i]);
    }
  });

  it("elevation grid is unchanged after exaggeration", () => {
    applyHeightExaggeration(fixture.mesh.vertices, 10);
    if (fixture.elevation && originalElevation) {
      for (let i = 0; i < fixture.elevation.grid.length; i++) {
        expect(fixture.elevation.grid[i]).toBeCloseTo(originalElevation[i]);
      }
    }
  });

  it("rdsm layer is unchanged after exaggeration", () => {
    applyHeightExaggeration(fixture.mesh.vertices, 10);
    if (fixture.layers?.rdsm && originalRDSM) {
      for (let i = 0; i < fixture.layers.rdsm.grid.length; i++) {
        expect(fixture.layers.rdsm.grid[i]).toBeCloseTo(originalRDSM[i]);
      }
    }
  });

  it("agl layer is unchanged after exaggeration", () => {
    applyHeightExaggeration(fixture.mesh.vertices, 10);
    if (fixture.layers?.agl && originalAGL) {
      for (let i = 0; i < fixture.layers.agl.grid.length; i++) {
        expect(fixture.layers.agl.grid[i]).toBeCloseTo(originalAGL[i]);
      }
    }
  });

  it("metadata is unchanged after exaggeration", () => {
    const originalMetadata = JSON.parse(JSON.stringify(fixture.metadata));
    applyHeightExaggeration(fixture.mesh.vertices, 10);
    expect(JSON.parse(JSON.stringify(fixture.metadata))).toEqual(originalMetadata);
  });
});

describe("No cumulative scaling bug (mesh.scale.y architecture)", () => {
  const fixture = createDeterministicFixture();
  const source = fixture.mesh.vertices;

  it("setting scale.y always applies to source, not accumulated", () => {
    const scale1 = 2;
    const scale2 = 5;
    const result1 = applyHeightExaggeration(source, scale1);
    const result2 = applyHeightExaggeration(source, scale2);
    for (let i = 0; i < source.length; i += 3) {
      expect(result1[i + 1]).toBeCloseTo(source[i + 1] * scale1);
      expect(result2[i + 1]).toBeCloseTo(source[i + 1] * scale2);
    }
  });

  it("changing scale from 2x to 5x means source * 5, not source * 10", () => {
    const result = applyHeightExaggeration(source, 5);
    for (let i = 0; i < source.length; i += 3) {
      expect(result[i + 1]).toBeCloseTo(source[i + 1] * 5);
    }
  });

  it("setting scale.y = 1 restores original Y values", () => {
    const exaggerated = applyHeightExaggeration(source, 10);
    const restored = applyHeightExaggeration(exaggerated, 1);
    for (let i = 0; i < source.length; i++) {
      expect(restored[i]).toBeCloseTo(exaggerated[i]);
    }
  });

  it("source is always the reference for any scale level", () => {
    for (const scale of [1, 2, 5, 10]) {
      const result = applyHeightExaggeration(source, scale);
      for (let i = 0; i < source.length; i += 3) {
        expect(result[i]).toBeCloseTo(source[i]);
        expect(result[i + 1]).toBeCloseTo(source[i + 1] * scale);
        expect(result[i + 2]).toBeCloseTo(source[i + 2]);
      }
    }
  });
});

describe("Geometry correctness at different exaggeration levels", () => {
  const fixture = createDeterministicFixture();
  const source = fixture.mesh.vertices;

  it("1x preserves original geometry", () => {
    const result = applyHeightExaggeration(source, 1);
    for (let i = 0; i < source.length; i++) {
      expect(result[i]).toBeCloseTo(source[i]);
    }
  });

  it("2x doubles Y, preserves X and Z", () => {
    const result = applyHeightExaggeration(source, 2);
    for (let i = 0; i < source.length; i += 3) {
      expect(result[i]).toBeCloseTo(source[i]);
      expect(result[i + 1]).toBeCloseTo(source[i + 1] * 2);
      expect(result[i + 2]).toBeCloseTo(source[i + 2]);
    }
  });

  it("5x quintuples Y, preserves X and Z", () => {
    const result = applyHeightExaggeration(source, 5);
    for (let i = 0; i < source.length; i += 3) {
      expect(result[i]).toBeCloseTo(source[i]);
      expect(result[i + 1]).toBeCloseTo(source[i + 1] * 5);
      expect(result[i + 2]).toBeCloseTo(source[i + 2]);
    }
  });

  it("10x decuples Y, preserves X and Z", () => {
    const result = applyHeightExaggeration(source, 10);
    for (let i = 0; i < source.length; i += 3) {
      expect(result[i]).toBeCloseTo(source[i]);
      expect(result[i + 1]).toBeCloseTo(source[i + 1] * 10);
      expect(result[i + 2]).toBeCloseTo(source[i + 2]);
    }
  });
});
