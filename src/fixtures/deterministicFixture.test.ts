import { describe, it, expect } from "vitest";
import { createDeterministicFixture } from "../fixtures/deterministicFixture";

describe("deterministicFixture", () => {
  const fixture = createDeterministicFixture();

  it("has correct id and source", () => {
    expect(fixture.id).toBe("dev-fixture-001");
    expect(fixture.metadata.source).toBe("deterministic-fixture");
  });

  it("has correct mesh dimensions", () => {
    expect(fixture.mesh.vertexCount).toBe(64);
    expect(fixture.mesh.indexCount).toBe(294);
    expect(fixture.mesh.vertices.length).toBe(64 * 3);
    expect(fixture.mesh.indices.length).toBe(294);
  });

  it("has elevation data", () => {
    expect(fixture.elevation).toBeDefined();
    expect(fixture.elevation!.width).toBe(8);
    expect(fixture.elevation!.height).toBe(8);
    expect(fixture.elevation!.cellSize).toBe(1.0);
    expect(fixture.elevation!.unit).toBe("meters");
    expect(fixture.elevation!.grid.length).toBe(64);
  });

  it("produces identical output on repeated calls", () => {
    const f2 = createDeterministicFixture();
    expect(f2.mesh.vertices).toEqual(fixture.mesh.vertices);
    expect(f2.mesh.indices).toEqual(fixture.mesh.indices);
    expect(f2.elevation!.grid).toEqual(fixture.elevation!.grid);
  });

  it("has valid triangle indices", () => {
    const maxVertex = fixture.mesh.vertexCount - 1;
    for (let i = 0; i < fixture.mesh.indices.length; i++) {
      expect(fixture.mesh.indices[i]).toBeGreaterThanOrEqual(0);
      expect(fixture.mesh.indices[i]).toBeLessThanOrEqual(maxVertex);
    }
  });

  it("has units set to meters", () => {
    expect(fixture.metadata.units.spatial).toBe("meters");
    expect(fixture.metadata.units.elevation).toBe("meters");
  });
});
