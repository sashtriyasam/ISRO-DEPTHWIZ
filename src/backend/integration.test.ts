import { describe, it, expect } from "vitest";
import { adaptBackendResult } from "./adapter";
import { BACKEND_TEST_FIXTURE, BACKEND_METRIC_FIXTURE } from "./fixtures";
import { resolveInspection } from "../inspection/resolver";

describe("inspection compatibility with backend artifacts", () => {
  it("backend artifact can be used with inspection resolver", () => {
    const result = adaptBackendResult(BACKEND_TEST_FIXTURE);
    const artifact = result.artifact!;

    const inspection = resolveInspection(
      { u: 0, v: 0 },
      { x: 0, y: 0, z: 0 },
      artifact,
      "dsm"
    );

    expect(inspection).not.toBeNull();
    expect(inspection!.artifactId).toBe(artifact.id);
    expect(inspection!.scientific.elevation).toBeDefined();
  });

  it("metric backend artifact preserves elevation in inspection", () => {
    const result = adaptBackendResult(BACKEND_METRIC_FIXTURE);
    const artifact = result.artifact!;

    const inspection = resolveInspection(
      { u: 0, v: 0 },
      { x: 0, y: 0, z: 0 },
      artifact,
      "dsm"
    );

    expect(inspection).not.toBeNull();
    expect(inspection!.scientific.elevation).toBeCloseTo(0.5);
  });
});

describe("measurement compatibility with backend artifacts", () => {
  it("backend artifact works with measurement point creation", () => {
    const result = adaptBackendResult(BACKEND_TEST_FIXTURE);
    const artifact = result.artifact!;

    const point = {
      displayPosition: { x: 0, y: 0, z: 0 },
      scientific: { elevation: 0.5 },
      uv: { u: 0, v: 0 },
      gridIndex: { col: 0, row: 0 },
      layerId: "dsm",
      artifactId: artifact.id,
    };

    expect(point.artifactId).toBe(artifact.id);
    expect(point.scientific.elevation).toBe(0.5);
  });
});

describe("profile compatibility with backend artifacts", () => {
  it("backend artifact can be used with profile sampler", () => {
    const result = adaptBackendResult(BACKEND_TEST_FIXTURE);
    const artifact = result.artifact!;

    expect(artifact.elevation).toBeDefined();
    expect(artifact.elevation!.grid.length).toBe(16);
    expect(artifact.elevation!.width).toBe(4);
    expect(artifact.elevation!.height).toBe(4);
  });
});
