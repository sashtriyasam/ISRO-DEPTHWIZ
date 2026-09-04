import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import type { SceneArtifact } from "../../types/scene";
import { createDeterministicFixture } from "../../fixtures/deterministicFixture";
import { MetadataPanel } from "./MetadataPanel";

function metricArtifact(): SceneArtifact {
  return {
    id: "backend-synthetic-depth-terrain",
    label: "synthetic-depth terrain",
    mesh: { vertices: new Float32Array(0), indices: new Uint32Array(0), vertexCount: 0, indexCount: 0 },
    elevation: { grid: new Float32Array([10, 11, 12, 13]), width: 2, height: 2, cellSize: 1, unit: "meters" },
    metadata: {
      source: "backend",
      units: { spatial: "meters", elevation: "meters" },
      CRS: "EPSG:32643",
      backend: {
        model_name: "synthetic-depth",
        depth_scale: "metric",
        elevation_semantics: "absolute_elevation_dsm",
        georeferencing: "georeferenced_no_elevation_reference",
        calibration_method: "scale_offset",
        calibration_reference: "synthetic-dev-ref",
        input_checksum: "a".repeat(64),
      },
      spatialDetails: { gsd: 0.5, rasterWidth: 5, rasterHeight: 4 },
    },
  };
}

describe("MetadataPanel", () => {
  it("explains the empty state", () => {
    render(<MetadataPanel artifact={null} activeLayerId="dsm" />);
    expect(screen.getByText("Metadata")).toBeInTheDocument();
    expect(screen.getByText(/No artifact loaded/)).toBeInTheDocument();
  });

  it("renders all sections for a complete product", () => {
    const { container } = render(<MetadataPanel artifact={metricArtifact()} activeLayerId="dsm" />);
    const summaries = Array.from(container.querySelectorAll("summary")).map((s) => s.textContent);
    expect(summaries).toEqual(["Product", "Spatial", "Calibration", "Provenance", "Input"]);
    expect(screen.getByText("EPSG:32643")).toBeInTheDocument();
    expect(screen.getByText("synthetic-dev-ref")).toBeInTheDocument();
    expect(screen.getByText("Absolute elevation (DSM)")).toBeInTheDocument();
  });

  it("uses one consistent fallback for missing fields", () => {
    const { container } = render(
      <MetadataPanel artifact={createDeterministicFixture()} activeLayerId="dsm" />
    );
    expect(container.textContent).toContain("Not available");
    expect(container.textContent).not.toContain("unknown");
    expect(container.textContent).not.toContain("N/A");
  });

  it("reflects the active layer without stale product data", () => {
    const fixture = createDeterministicFixture();
    const { rerender, container } = render(<MetadataPanel artifact={fixture} activeLayerId="rdsm" />);
    expect(container.textContent).toContain("Relative surface (rDSM)");
    rerender(<MetadataPanel artifact={fixture} activeLayerId="agl" />);
    expect(container.textContent).toContain("Height above ground (AGL)");
    expect(container.textContent).not.toContain("Relative surface (rDSM)");
  });

  it("updates atomically on artifact replacement", () => {
    const { rerender, container } = render(
      <MetadataPanel artifact={createDeterministicFixture()} activeLayerId="dsm" />
    );
    expect(container.textContent).toContain("Development fixture");
    rerender(<MetadataPanel artifact={metricArtifact()} activeLayerId="dsm" />);
    expect(container.textContent).toContain("Synthetic Development Backend");
    expect(container.textContent).not.toContain("Development fixture");
  });

  it("keeps meaning out of color alone with text labels", () => {
    const { container } = render(<MetadataPanel artifact={metricArtifact()} activeLayerId="dsm" />);
    const details = container.querySelectorAll("details");
    expect(details.length).toBe(5);
    for (const d of Array.from(details)) {
      const summary = d.querySelector(":scope > summary");
      expect(summary).not.toBeNull();
      expect(summary!.textContent!.length).toBeGreaterThan(0);
    }
  });
});
