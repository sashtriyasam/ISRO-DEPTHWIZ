import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import type { ElevationProfile } from "../../profile/types";
import { ProfileChart } from "./ProfileChart";

function profileWith(units: "meters" | "relative", semantics?: string): ElevationProfile {
  const point = {
    displayPosition: { x: 0, y: 0, z: 0 },
    scientific: { elevation: 0 },
    uv: { u: 0, v: 0 },
    gridIndex: { col: 0, row: 0 },
    layerId: "dsm",
    artifactId: "test",
  };
  return {
    pointA: point,
    pointB: point,
    points: [
      { pathPosition: { x: 0, z: 0 }, cumulativeDistance: 0, elevation: 10 },
      { pathPosition: { x: 1, z: 0 }, cumulativeDistance: 1, elevation: 12 },
    ],
    totalDistance: 1,
    minElevation: 10,
    maxElevation: 12,
    sampleCount: 2,
    units,
    source: "backend",
    elevationSemantics: semantics,
  };
}

beforeEach(() => {
  (globalThis as Record<string, unknown>).ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
});

describe("ProfileChart units", () => {
  it("titles metric profiles in meters", () => {
    render(<ProfileChart profile={profileWith("meters", "absolute_elevation_dsm")} />);
    expect(screen.getByText("Elevation (m)")).toBeInTheDocument();
    expect(screen.getByText("Distance (m)")).toBeInTheDocument();
  });

  it("titles relative profiles without fabricating meters", () => {
    const { container } = render(<ProfileChart profile={profileWith("relative", "relative_depth")} />);
    expect(screen.getByText("Relative depth (relative)")).toBeInTheDocument();
    expect(screen.getByText("Distance (relative)")).toBeInTheDocument();
    expect(container.textContent).not.toContain("(m)");
  });

  it("describes the profile accessibly with real units", () => {
    const { container } = render(<ProfileChart profile={profileWith("relative", "relative_depth")} />);
    const labelled = container.querySelector('[aria-label*="units relative"]');
    expect(labelled).not.toBeNull();
  });
});
