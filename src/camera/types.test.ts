import { describe, it, expect } from "vitest";
import type { CameraMode, CameraState } from "./types";

describe("CameraMode type", () => {
  it("orbit is a valid mode", () => {
    const mode: CameraMode = "orbit";
    expect(mode).toBe("orbit");
  });
});

describe("CameraState type", () => {
  it("can be constructed with required fields", () => {
    const state: CameraState = {
      mode: "orbit",
      position: { x: 1, y: 2, z: 3 } as any,
      target: { x: 0, y: 0, z: 0 } as any,
      distance: 5,
    };
    expect(state.mode).toBe("orbit");
    expect(state.distance).toBe(5);
  });
});
