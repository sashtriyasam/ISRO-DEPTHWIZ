import { describe, it, expect } from "vitest";
import {
  EXAGGERATION_LEVELS,
  DEFAULT_EXAGGERATION,
  EXAGGERATION_LABELS,
  isValidExaggeration,
  applyHeightExaggeration,
} from "./types";

describe("ExaggerationLevel type", () => {
  it("has exactly 4 supported levels", () => {
    expect(EXAGGERATION_LEVELS).toEqual([1, 2, 5, 10]);
    expect(EXAGGERATION_LEVELS).toHaveLength(4);
  });

  it("default is 1", () => {
    expect(DEFAULT_EXAGGERATION).toBe(1);
  });

  it("has labels for all levels", () => {
    for (const level of EXAGGERATION_LEVELS) {
      expect(EXAGGERATION_LABELS[level]).toBeDefined();
      expect(typeof EXAGGERATION_LABELS[level]).toBe("string");
    }
  });
});

describe("isValidExaggeration", () => {
  it("accepts valid levels", () => {
    expect(isValidExaggeration(1)).toBe(true);
    expect(isValidExaggeration(2)).toBe(true);
    expect(isValidExaggeration(5)).toBe(true);
    expect(isValidExaggeration(10)).toBe(true);
  });

  it("rejects invalid levels", () => {
    expect(isValidExaggeration(0)).toBe(false);
    expect(isValidExaggeration(3)).toBe(false);
    expect(isValidExaggeration(7)).toBe(false);
    expect(isValidExaggeration(100)).toBe(false);
    expect(isValidExaggeration(-1)).toBe(false);
  });
});

describe("applyHeightExaggeration", () => {
  const sourceVertices = new Float32Array([
    0, 1, 0,
    1, 2, 0,
    0, 3, 1,
  ]);

  it("1x returns equivalent values", () => {
    const result = applyHeightExaggeration(sourceVertices, 1);
    expect(result[0]).toBeCloseTo(0);
    expect(result[1]).toBeCloseTo(1);
    expect(result[2]).toBeCloseTo(0);
    expect(result[3]).toBeCloseTo(1);
    expect(result[4]).toBeCloseTo(2);
    expect(result[5]).toBeCloseTo(0);
  });

  it("2x scales Y by 2", () => {
    const result = applyHeightExaggeration(sourceVertices, 2);
    expect(result[0]).toBeCloseTo(0);
    expect(result[1]).toBeCloseTo(2);
    expect(result[2]).toBeCloseTo(0);
    expect(result[3]).toBeCloseTo(1);
    expect(result[4]).toBeCloseTo(4);
    expect(result[5]).toBeCloseTo(0);
  });

  it("5x scales Y by 5", () => {
    const result = applyHeightExaggeration(sourceVertices, 5);
    expect(result[1]).toBeCloseTo(5);
    expect(result[4]).toBeCloseTo(10);
    expect(result[7]).toBeCloseTo(15);
  });

  it("10x scales Y by 10", () => {
    const result = applyHeightExaggeration(sourceVertices, 10);
    expect(result[1]).toBeCloseTo(10);
    expect(result[4]).toBeCloseTo(20);
    expect(result[7]).toBeCloseTo(30);
  });

  it("preserves X and Z coordinates", () => {
    const result = applyHeightExaggeration(sourceVertices, 5);
    expect(result[0]).toBeCloseTo(0);
    expect(result[2]).toBeCloseTo(0);
    expect(result[3]).toBeCloseTo(1);
    expect(result[5]).toBeCloseTo(0);
  });

  it("does not mutate source array", () => {
    const original = new Float32Array(sourceVertices);
    applyHeightExaggeration(sourceVertices, 10);
    for (let i = 0; i < sourceVertices.length; i++) {
      expect(sourceVertices[i]).toBeCloseTo(original[i]);
    }
  });

  it("returns a new array", () => {
    const result = applyHeightExaggeration(sourceVertices, 2);
    expect(result).not.toBe(sourceVertices);
  });
});
