import { describe, it, expect } from "vitest";
import type { ArtifactSource, ArtifactState } from "./types";

describe("ArtifactState type", () => {
  it("valid states", () => {
    const states: ArtifactState[] = ["idle", "loading", "ready", "error"];
    expect(states).toHaveLength(4);
  });
});

describe("ArtifactSource interface", () => {
  it("can be implemented", () => {
    const source: ArtifactSource = {
      id: "test",
      label: "Test Source",
      load: async () => ({ id: "a", label: "A", mesh: {} as any, metadata: {} as any }),
    };
    expect(source.id).toBe("test");
    expect(source.label).toBe("Test Source");
  });
});
