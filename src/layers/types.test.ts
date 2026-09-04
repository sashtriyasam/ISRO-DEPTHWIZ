import { describe, it, expect } from "vitest";
import { ALL_LAYER_IDS, LAYER_LABELS, LAYER_DESCRIPTIONS } from "./types";

describe("LayerId type", () => {
  it("contains all expected layer ids", () => {
    expect(ALL_LAYER_IDS).toContain("dsm");
    expect(ALL_LAYER_IDS).toContain("rdsm");
    expect(ALL_LAYER_IDS).toContain("agl");
    expect(ALL_LAYER_IDS).toContain("rgb");
    expect(ALL_LAYER_IDS).toContain("wireframe");
    expect(ALL_LAYER_IDS).toContain("slope");
    expect(ALL_LAYER_IDS).toContain("contours");
    expect(ALL_LAYER_IDS).toContain("reference");
    expect(ALL_LAYER_IDS).toHaveLength(8);
  });
});

describe("LAYER_LABELS", () => {
  it("has labels for all layer ids", () => {
    for (const id of ALL_LAYER_IDS) {
      expect(LAYER_LABELS[id]).toBeDefined();
      expect(typeof LAYER_LABELS[id]).toBe("string");
    }
  });
});

describe("LAYER_DESCRIPTIONS", () => {
  it("has descriptions for all layer ids", () => {
    for (const id of ALL_LAYER_IDS) {
      expect(LAYER_DESCRIPTIONS[id]).toBeDefined();
      expect(typeof LAYER_DESCRIPTIONS[id]).toBe("string");
    }
  });
});
