import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BackendBridge, type ValidationReport } from "../../backend/bridge";
import { ValidationPanel } from "./ValidationPanel";

const REPORT: ValidationReport = {
  product: "dsm.tif",
  reference: "lidar.tif",
  metric: true,
  coverage: 0.98,
  native: { n: 100, rmse: 3.21, mae: 2.1, bias: -0.4, pearson_r: 0.97, spearman_rho: 0.95 },
};

function bridgeWith(report: ValidationReport): BackendBridge {
  const bridge = new BackendBridge();
  bridge.stageInputBytes = vi.fn(async () => ({ path: "C:/tmp/depthwiz-x/lidar.tif", cleanup: async () => {} }));
  bridge.executeValidate = vi.fn(async () => report);
  return bridge;
}

describe("ValidationPanel", () => {
  it("asks for a run before validation", () => {
    render(<ValidationPanel />);
    expect(screen.getByText(/Generate terrain first/)).toBeInTheDocument();
  });

  it("stages the reference, validates and shows metric scores", async () => {
    const bridge = bridgeWith(REPORT);
    render(<ValidationPanel productPath="C:/tmp/depthwiz-a/dsm.tif" bridge={bridge} />);
    const input = screen.getByLabelText("Reference height raster") as HTMLInputElement;
    const file = new File([new Uint8Array([1, 2, 3])], "lidar.tif");
    Object.defineProperty(input, "files", { value: [file] });
    fireEvent.change(input);
    await waitFor(() => expect(screen.getByText("3.21 m")).toBeInTheDocument());
    expect(bridge.executeValidate).toHaveBeenCalledWith(
      "C:/tmp/depthwiz-a/dsm.tif",
      "C:/tmp/depthwiz-x/lidar.tif",
    );
    expect(screen.getByText("0.970")).toBeInTheDocument();
  });

  it("rejects non-GeoTIFF references", async () => {
    render(<ValidationPanel productPath="dsm.tif" bridge={bridgeWith(REPORT)} />);
    const input = screen.getByLabelText("Reference height raster") as HTMLInputElement;
    Object.defineProperty(input, "files", { value: [new File(["x"], "notes.txt")] });
    fireEvent.change(input);
    await waitFor(() => expect(screen.getByRole("alert").textContent).toMatch(/GeoTIFF/));
  });
});
