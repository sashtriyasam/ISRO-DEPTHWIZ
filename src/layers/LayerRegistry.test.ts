import { describe, it, expect } from "vitest";
import { createLayerState, getActiveLayer, setActiveLayer } from "./LayerRegistry";
import { createDeterministicFixture } from "../fixtures/deterministicFixture";

describe("createLayerState", () => {
  const fixture = createDeterministicFixture();
  const state = createLayerState(fixture);

  it("creates layers for all layer ids", () => {
    expect(state.layers).toHaveLength(8);
  });

  it("marks dsm as available", () => {
    const dsm = state.layers.find((l) => l.id === "dsm");
    expect(dsm?.available).toBe(true);
  });

  it("marks rdsm as available", () => {
    const rdsm = state.layers.find((l) => l.id === "rdsm");
    expect(rdsm?.available).toBe(true);
  });

  it("marks agl as available", () => {
    const agl = state.layers.find((l) => l.id === "agl");
    expect(agl?.available).toBe(true);
  });

  it("marks wireframe as available", () => {
    const wireframe = state.layers.find((l) => l.id === "wireframe");
    expect(wireframe?.available).toBe(true);
  });

  it("marks slope as unavailable", () => {
    const slope = state.layers.find((l) => l.id === "slope");
    expect(slope?.available).toBe(false);
  });

  it("marks contours as unavailable", () => {
    const contours = state.layers.find((l) => l.id === "contours");
    expect(contours?.available).toBe(false);
  });

  it("enables the first available layer", () => {
    expect(state.activeLayerId).toBeTruthy();
    const active = state.layers.find((l) => l.id === state.activeLayerId);
    expect(active?.enabled).toBe(true);
    expect(active?.available).toBe(true);
  });
});

describe("getActiveLayer", () => {
  it("returns the active layer", () => {
    const fixture = createDeterministicFixture();
    const state = createLayerState(fixture);
    const active = getActiveLayer(state);
    expect(active).toBeDefined();
    expect(active?.id).toBe(state.activeLayerId);
    expect(active?.enabled).toBe(true);
  });
});

describe("setActiveLayer", () => {
  it("switches to a different available layer", () => {
    const fixture = createDeterministicFixture();
    const state = createLayerState(fixture);
    const newState = setActiveLayer(state, "wireframe");
    expect(newState.activeLayerId).toBe("wireframe");
    const active = newState.layers.find((l) => l.id === "wireframe");
    expect(active?.enabled).toBe(true);
  });

  it("does not switch to an unavailable layer", () => {
    const fixture = createDeterministicFixture();
    const state = createLayerState(fixture);
    const originalId = state.activeLayerId;
    const newState = setActiveLayer(state, "slope");
    expect(newState.activeLayerId).toBe(originalId);
  });

  it("returns same state for same layer", () => {
    const fixture = createDeterministicFixture();
    const state = createLayerState(fixture);
    const newState = setActiveLayer(state, state.activeLayerId);
    expect(newState).toEqual(state);
  });
});
