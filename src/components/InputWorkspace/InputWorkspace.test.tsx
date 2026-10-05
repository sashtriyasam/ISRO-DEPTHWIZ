import { describe, it, expect, vi } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  within,
} from "@testing-library/react";
import { BackendBridge } from "../../backend/bridge";
import { InputWorkspace } from "./InputWorkspace";
import { makeTestPng, makeCorruptBytes } from "../../input/testFixtures";
import { FixtureSource } from "../../artifact/FixtureSource";
import { ApplicationBackendSource } from "../../input/applicationSource";
import { LocalServiceClient } from "../../service/client";
import type { ServiceCapabilitiesWire } from "../../service/wireTypes";

const bridge = new BackendBridge({ bridgeScript: "scripts/backend_bridge.py" });
const SLOW = { timeout: 20000 };

// Stub client that only advertises the synthetic backend (for isolated tests)
const syntheticOnlyClient = {
  capabilities: async (): Promise<ServiceCapabilitiesWire> => ({
    contract_version: "1",
    supported_input_formats: [".png", ".jpg", ".jpeg", ".tif", ".tiff"],
    supported_target_semantics: ["absolute_elevation_dsm", "height_agl_ndsm"],
    available_backends: ["synthetic-depth"],
    mesh_supported: true,
    geotiff_supported: true,
  }),
} as unknown as LocalServiceClient;

function pngFile(name = "tile.png"): File {
  return new File([makeTestPng(4, 4) as unknown as BlobPart], name, {
    type: "image/png",
  });
}

async function openFile(container: HTMLElement, file: File) {
  const input = container.querySelector(
    'input[type="file"]',
  ) as HTMLInputElement;
  Object.defineProperty(input, "files", { value: [file], configurable: true });
  fireEvent.change(input);
}

function gcpFile(name = "gcps.csv"): File {
  return new File(["pixel_col,pixel_row,elevation\n0,0,100\n1,1,101\n2,2,103\n"], name, {
    type: "text/csv",
  });
}

async function attachReference(file: File) {
  const input = screen.getByLabelText("Calibration reference file") as HTMLInputElement;
  Object.defineProperty(input, "files", { value: [file], configurable: true });
  fireEvent.change(input);
}

async function waitForSupported(container: HTMLElement) {
  await waitFor(
    () => expect(container.textContent).toContain("Supported:"),
    SLOW,
  );
}

describe("InputWorkspace", () => {
  it("loads capabilities and advertises real backend formats", async () => {
    const { container } = render(
      <InputWorkspace
        bridge={bridge}
        processingRunning={false}
        onGenerate={() => undefined}
      />,
    );
    await waitForSupported(container);
    expect(container.textContent).toContain("PNG");
    expect(container.textContent).toContain("GeoTIFF");
    expect(container.textContent).not.toContain("BMP");
  });

  it("rejects unsupported extensions without backend validation", async () => {
    const onGenerate = vi.fn();
    const { container } = render(
      <InputWorkspace
        bridge={bridge}
        processingRunning={false}
        onGenerate={onGenerate}
      />,
    );
    await waitForSupported(container);
    const bad = new File(["hello"], "notes.txt", { type: "text/plain" });
    await openFile(container, bad);
    await waitFor(() => {
      expect(
        screen.getByText("Unsupported input format (.txt)."),
      ).toBeInTheDocument();
    }, SLOW);
    expect(screen.getByText(/Choose another file/)).toBeInTheDocument();
  });

  it("validates a file through the backend and shows metadata", async () => {
    const { container } = render(
      <InputWorkspace
        bridge={bridge}
        processingRunning={false}
        onGenerate={() => undefined}
      />,
    );
    await waitForSupported(container);
    await openFile(container, pngFile());
    await waitFor(() => {
      expect(screen.getByText("Validated")).toBeInTheDocument();
    }, SLOW);
    const workspace = container.firstChild as HTMLElement;
    expect(within(workspace).getByText("tile.png")).toBeInTheDocument();
    expect(within(workspace).getByText("4×4")).toBeInTheDocument();
    expect(within(workspace).getByText("Not available")).toBeInTheDocument();
  });

  it("passes selected calibration method and mesh levels through", async () => {
    const onGenerate = vi.fn();
    const { container } = render(
      <InputWorkspace
        bridge={bridge}
        processingRunning={false}
        onGenerate={onGenerate}
      />,
    );
    await waitForSupported(container);
    await openFile(container, pngFile());
    await waitFor(() => {
      expect(screen.getByText("Validated")).toBeInTheDocument();
    }, SLOW);
    await attachReference(gcpFile());
    await waitFor(() => {
      expect(screen.getByText(/calibrated against gcps\.csv/)).toBeInTheDocument();
    }, SLOW);
    fireEvent.click(screen.getByRole("radio", { name: "Piecewise Linear" }));
    fireEvent.change(
      screen.getByRole("combobox", { name: "Mesh LOD levels" }),
      {
        target: { value: "1" },
      },
    );
    fireEvent.click(screen.getByRole("button", { name: "Generate terrain" }));
    expect(onGenerate).toHaveBeenCalledOnce();
    const source = onGenerate.mock.calls[0][0] as ApplicationBackendSource;
    expect(source.calibrationMethod).toBe("piecewise_linear");
    expect(source.meshLevels).toEqual([1]);
    expect(source.mode).toBe("metric");
    expect(source.calibrationReference).toMatch(/gcps\.csv$/);
  });

  it("runs relative output without a calibration reference (no metres)", async () => {
    const onGenerate = vi.fn();
    const { container } = render(
      <InputWorkspace
        bridge={bridge}
        processingRunning={false}
        onGenerate={onGenerate}
      />,
    );
    await waitForSupported(container);
    await openFile(container, pngFile());
    await waitFor(() => {
      expect(screen.getByText("Validated")).toBeInTheDocument();
    }, SLOW);
    expect(screen.getByText(/relative surface \(no metric units\)/)).toBeInTheDocument();
    expect(screen.queryByRole("radio", { name: "Piecewise Linear" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Generate terrain" }));
    const source = onGenerate.mock.calls[0][0] as ApplicationBackendSource;
    expect(source.mode).toBe("relative");
    expect(source.calibrationReference).toBeUndefined();
    expect(source.calibrationMethod).toBeUndefined();
  });

  it("rejects calibration references that are not DEM GeoTIFF or GCP CSV", async () => {
    const { container } = render(
      <InputWorkspace
        bridge={bridge}
        processingRunning={false}
        onGenerate={() => undefined}
      />,
    );
    await waitForSupported(container);
    await openFile(container, pngFile());
    await waitFor(() => {
      expect(screen.getByText("Validated")).toBeInTheDocument();
    }, SLOW);
    await attachReference(new File(["x"], "notes.txt", { type: "text/plain" }));
    await waitFor(() => {
      expect(screen.getByText(/Unsupported reference format \(\.txt\)/)).toBeInTheDocument();
    }, SLOW);
  });

  it("shows backend rejection reasons for corrupt files", async () => {
    const { container } = render(
      <InputWorkspace
        bridge={bridge}
        processingRunning={false}
        onGenerate={() => undefined}
      />,
    );
    await waitForSupported(container);
    const corrupt = new File(
      [makeCorruptBytes() as unknown as BlobPart],
      "corrupt.png",
      {
        type: "image/png",
      },
    );
    await openFile(container, corrupt);
    await waitFor(() => {
      expect(screen.getByText("Input could not be read.")).toBeInTheDocument();
    }, SLOW);
  });

  it("generates a file source on demand, not on selection", async () => {
    const onGenerate = vi.fn();
    const { container } = render(
      <InputWorkspace
        bridge={bridge}
        serviceClient={syntheticOnlyClient}
        processingRunning={false}
        onGenerate={onGenerate}
      />,
    );
    await waitForSupported(container);
    await openFile(container, pngFile());
    await waitFor(() => {
      expect(screen.getByText("Validated")).toBeInTheDocument();
    }, SLOW);
    expect(onGenerate).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Generate terrain" }));
    expect(onGenerate).toHaveBeenCalledOnce();
    const source = onGenerate.mock.calls[0][0] as ApplicationBackendSource;
    expect(source).toBeInstanceOf(ApplicationBackendSource);
    expect(source.kind).toBe("file");
    expect(source.backendLabel).toBe("Synthetic Development Backend");
  });

  it("shows the registered backend identity without a dropdown", async () => {
    const { container } = render(
      <InputWorkspace
        bridge={bridge}
        serviceClient={syntheticOnlyClient}
        processingRunning={false}
        onGenerate={() => undefined}
      />,
    );
    await waitForSupported(container);
    expect(container.textContent).toContain(
      "Backend: Synthetic Development Backend",
    );
  });

  it("states the desktop host honestly without claiming production", async () => {
    const { container } = render(
      <InputWorkspace
        bridge={bridge}
        processingRunning={false}
        onGenerate={() => undefined}
      />,
    );
    await waitForSupported(container);
    expect(container.textContent).toContain("Host: Desktop host");
    expect(container.textContent).not.toContain("Production");
  });

  it("offers capability-driven output targets and passes the selection through", async () => {
    const onGenerate = vi.fn();
    const { container } = render(
      <InputWorkspace
        bridge={bridge}
        processingRunning={false}
        onGenerate={onGenerate}
      />,
    );
    await waitForSupported(container);
    await openFile(container, pngFile());
    await waitFor(() => {
      expect(screen.getByText("Validated")).toBeInTheDocument();
    }, SLOW);
    await attachReference(gcpFile());
    await waitFor(() => {
      expect(screen.getByRole("radio", { name: "Height / AGL" })).toBeInTheDocument();
    }, SLOW);
    fireEvent.click(screen.getByRole("radio", { name: "Height / AGL" }));
    fireEvent.click(screen.getByRole("button", { name: "Generate terrain" }));
    expect(onGenerate).toHaveBeenCalledOnce();
    const source = onGenerate.mock.calls[0][0] as { targetSemantics: string };
    expect(source.targetSemantics).toBe("height_agl_ndsm");
  });

  it("blocks generation with an explicit state when the backend is unregistered", async () => {
    const stubClient = {
      capabilities: async (): Promise<ServiceCapabilitiesWire> => ({
        contract_version: "1",
        supported_input_formats: [".png"],
        supported_target_semantics: ["absolute_elevation_dsm"],
        available_backends: ["retired-model"],
        mesh_supported: true,
        geotiff_supported: false,
      }),
    } as unknown as LocalServiceClient;
    const onGenerate = vi.fn();
    const { container } = render(
      <InputWorkspace
        bridge={bridge}
        serviceClient={stubClient}
        processingRunning={false}
        onGenerate={onGenerate}
      />,
    );
    await waitFor(
      () => expect(container.textContent).toContain("Supported:"),
      SLOW,
    );
    await openFile(container, pngFile());
    await waitFor(() => {
      expect(screen.getByText("Validated")).toBeInTheDocument();
    }, SLOW);
    expect(screen.getByText(/Backend unavailable/)).toBeInTheDocument();
    expect(screen.getByText(/will not be substituted/)).toBeInTheDocument();
    const generate = screen.getByRole("button", { name: "Generate terrain" });
    expect(generate).toBeDisabled();
    fireEvent.click(generate);
    expect(onGenerate).not.toHaveBeenCalled();
  });

  it("disables generation while processing runs", async () => {
    const { container: runningContainer } = render(
      <InputWorkspace
        bridge={bridge}
        processingRunning
        onGenerate={() => undefined}
      />,
    );
    await waitFor(
      () => expect(runningContainer.textContent).toContain("Supported:"),
      SLOW,
    );
    const generate = screen.queryByRole("button", { name: "Generate terrain" });
    if (generate) {
      expect(generate).toBeDisabled();
    }
  });

  it("offers the development fixture without backend validation", async () => {
    const onGenerate = vi.fn();
    render(
      <InputWorkspace
        bridge={bridge}
        processingRunning={false}
        onGenerate={onGenerate}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Use development fixture" }),
    );
    await waitFor(() => {
      expect(screen.getByText("Validated")).toBeInTheDocument();
    }, SLOW);
    fireEvent.click(screen.getByRole("button", { name: "Generate terrain" }));
    expect(onGenerate).toHaveBeenCalledOnce();
    expect(onGenerate.mock.calls[0][0]).toBeInstanceOf(FixtureSource);
  });

  it("clears back to empty", async () => {
    const { container } = render(
      <InputWorkspace
        bridge={bridge}
        processingRunning={false}
        onGenerate={() => undefined}
      />,
    );
    await waitForSupported(container);
    await openFile(container, pngFile());
    await waitFor(() => {
      expect(screen.getByText("Validated")).toBeInTheDocument();
    }, SLOW);
    fireEvent.click(screen.getByRole("button", { name: "Clear" }));
    await waitFor(() => {
      expect(screen.queryByText("Validated")).toBeNull();
    }, SLOW);
  });
});

describe("InputWorkspace georeferenced defaults", () => {
  async function geotiffFile(): Promise<File> {
    const { execFileSync } = await import("child_process");
    const { mkdtempSync, readFileSync } = await import("fs");
    const { tmpdir } = await import("os");
    const { join } = await import("path");
    const dir = mkdtempSync(join(tmpdir(), "depthwiz-geo-ui-"));
    const out = join(dir, "scene.tif");
    const script = [
      "import numpy as np, rasterio, sys",
      "from rasterio.transform import Affine",
      "p = sys.argv[1]",
      "a = (np.arange(3*8*8) % 255).astype('uint8').reshape(3, 8, 8)",
      "with rasterio.open(p, 'w', driver='GTiff', height=8, width=8, count=3, dtype='uint8',",
      "    crs='EPSG:32643', transform=Affine(0.5, 0, 715000, 0, -0.5, 3160000)) as d: d.write(a)",
    ].join("\n");
    const python = process.env.DEPTHWIZARD_PYTHON ?? "python";
    execFileSync(python, ["-c", script, out]);
    return new File([readFileSync(out)], "scene.tif", { type: "image/tiff" });
  }

  it("defaults GeoTIFF input to metric output on the automatic Copernicus DEM", async () => {
    const onGenerate = vi.fn();
    const { container } = render(
      <InputWorkspace bridge={bridge} processingRunning={false} onGenerate={onGenerate} />,
    );
    await waitForSupported(container);
    await openFile(container, await geotiffFile());
    await waitFor(() => expect(screen.getByText("Validated")).toBeInTheDocument(), SLOW);
    expect(screen.getByRole("checkbox", { name: "Use Copernicus DEM automatically" })).toBeChecked();
    fireEvent.click(screen.getByRole("button", { name: "Generate terrain" }));
    const source = onGenerate.mock.calls[0][0] as ApplicationBackendSource;
    expect(source.mode).toBe("metric");
    expect(source.autoReference).toBe(true);
    expect(source.calibrationMethod).toBe("dem_anchored");
    expect(source.targetSemantics).toBe("absolute_elevation_dsm");
  }, 60000);

  it("can opt out of the automatic DEM (relative output)", async () => {
    const onGenerate = vi.fn();
    const { container } = render(
      <InputWorkspace bridge={bridge} processingRunning={false} onGenerate={onGenerate} />,
    );
    await waitForSupported(container);
    await openFile(container, await geotiffFile());
    await waitFor(() => expect(screen.getByText("Validated")).toBeInTheDocument(), SLOW);
    fireEvent.click(screen.getByRole("checkbox", { name: "Use Copernicus DEM automatically" }));
    fireEvent.click(screen.getByRole("button", { name: "Generate terrain" }));
    const source = onGenerate.mock.calls[0][0] as ApplicationBackendSource;
    expect(source.mode).toBe("relative");
    expect(source.autoReference).toBe(false);
  }, 60000);
});
