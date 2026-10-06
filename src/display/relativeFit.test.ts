import { describe, it, expect } from "vitest";
import type { SceneArtifact } from "../types/scene";
import { RELATIVE_RELIEF_FRACTION, relativeDisplayFit } from "./relativeFit";

function scene(
  elevation: "meters" | "relative",
  spatial: "meters" | "pixels",
  reliefY: number,
): SceneArtifact {
  return {
    metadata: {
      source: "backend",
      units: { spatial, elevation },
      bounds: { minX: 0, maxX: 2000, minY: 0, maxY: reliefY, minZ: 0, maxZ: 1000 },
    },
  } as unknown as SceneArtifact;
}

describe("relativeDisplayFit", () => {
  it("lifts flat relative scenes to a readable share of the footprint", () => {
    const fit = relativeDisplayFit(scene("relative", "pixels", 20));
    expect(fit * 20).toBeCloseTo(RELATIVE_RELIEF_FRACTION * 2000);
  });

  it("never rescales metric scenes", () => {
    expect(relativeDisplayFit(scene("meters", "meters", 20))).toBe(1);
  });

  it("returns 1 without a scene or relief", () => {
    expect(relativeDisplayFit(null)).toBe(1);
    expect(relativeDisplayFit(scene("relative", "pixels", 0))).toBe(1);
  });
});
