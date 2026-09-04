import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { BackendBridge } from "../../backend/bridge";
import { InputWorkspace } from "./InputWorkspace";
import { makeTestPng, makeCorruptBytes } from "../../input/testFixtures";
import { FixtureSource } from "../../artifact/FixtureSource";
import { ApplicationBackendSource } from "../../input/applicationSource";
import { LocalServiceClient } from "../../service/client";
import type { ServiceCapabilitiesWire } from "../../service/wireTypes";

const bridge = new BackendBridge({ bridgeScript: "scripts/backend_bridge.py" });
const SLOW = { timeout: 20000 };

function pngFile(name = "tile.png"): File {
  return new File([makeTestPng(4, 4) as unknown as BlobPart], name, { type: "image/png" });
}

async function openFile(container: HTMLElement, file: File) {
  const input = container.querySelector('input[type="file"]') as HTMLInputElement;
  Object.defineProperty(input, "files", { value: [file], configurable: true });
  fireEvent.change(input);
}

async function waitForSupported(container: HTMLElement) {
  await waitFor(() => expect(container.textContent).toContain("Supported:"), SLOW);
}

describe("InputWorkspace", () => {
  it("loads capabilities and advertises real backend formats", async () => {
    const { container } = render(
      <InputWorkspace bridge={bridge} processingRunning={false} onGenerate={() => undefined} />
    );
    await waitForSupported(container);
    expect(container.textContent).toContain("PNG");
    expect(container.textContent).toContain("GeoTIFF");
    expect(container.textContent).not.toContain("BMP");
  });

  it("rejects unsupported extensions without backend validation", async () => {
    const onGenerate = vi.fn();
    const { container } = render(
      <InputWorkspace bridge={bridge} processingRunning={false} onGenerate={onGenerate} />
    );
    await waitForSupported(container);
    const bad = new File(["hello"], "notes.txt", { type: "text/plain" });
    await openFile(container, bad);
    await waitFor(() => {
      expect(screen.getByText("Unsupported input format (.txt).")).toBeInTheDocument();
    }, SLOW);
    expect(screen.getByText(/Choose another file/)).toBeInTheDocument();
  });

  it("validates a file through the backend and shows metadata", async () => {
    const { container } = render(
      <InputWorkspace bridge={bridge} processingRunning={false} onGenerate={() => undefined} />
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

  it("shows backend rejection reasons for corrupt files", async () => {
    const { container } = render(
      <InputWorkspace bridge={bridge} processingRunning={false} onGenerate={() => undefined} />
    );
    await waitForSupported(container);
    const corrupt = new File([makeCorruptBytes() as unknown as BlobPart], "corrupt.png", {
      type: "image/png",
    });
    await openFile(container, corrupt);
    await waitFor(() => {
      expect(screen.getByText("Input could not be read.")).toBeInTheDocument();
    }, SLOW);
  });

  it("generates a file source on demand, not on selection", async () => {
    const onGenerate = vi.fn();
    const { container } = render(
      <InputWorkspace bridge={bridge} processingRunning={false} onGenerate={onGenerate} />
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
      <InputWorkspace bridge={bridge} processingRunning={false} onGenerate={() => undefined} />
    );
    await waitForSupported(container);
    expect(container.textContent).toContain("Backend: Synthetic Development Backend");
  });

  it("states the desktop host honestly without claiming production", async () => {
    const { container } = render(
      <InputWorkspace bridge={bridge} processingRunning={false} onGenerate={() => undefined} />
    );
    await waitForSupported(container);
    expect(container.textContent).toContain("Host: Desktop host");
    expect(container.textContent).not.toContain("Production");
  });

  it("offers capability-driven output targets and passes the selection through", async () => {
    const onGenerate = vi.fn();
    const { container } = render(
      <InputWorkspace bridge={bridge} processingRunning={false} onGenerate={onGenerate} />
    );
    await waitForSupported(container);
    await openFile(container, pngFile());
    await waitFor(() => {
      expect(screen.getByText("Validated")).toBeInTheDocument();
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
      />
    );
    await waitFor(() => expect(container.textContent).toContain("Supported:"), SLOW);
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
      <InputWorkspace bridge={bridge} processingRunning onGenerate={() => undefined} />
    );
    await waitFor(
      () => expect(runningContainer.textContent).toContain("Supported:"),
      SLOW
    );
    const generate = screen.queryByRole("button", { name: "Generate terrain" });
    if (generate) {
      expect(generate).toBeDisabled();
    }
  });

  it("offers the development fixture without backend validation", async () => {
    const onGenerate = vi.fn();
    render(
      <InputWorkspace bridge={bridge} processingRunning={false} onGenerate={onGenerate} />
    );
    fireEvent.click(screen.getByRole("button", { name: "Use development fixture" }));
    await waitFor(() => {
      expect(screen.getByText("Validated")).toBeInTheDocument();
    }, SLOW);
    fireEvent.click(screen.getByRole("button", { name: "Generate terrain" }));
    expect(onGenerate).toHaveBeenCalledOnce();
    expect(onGenerate.mock.calls[0][0]).toBeInstanceOf(FixtureSource);
  });

  it("clears back to empty", async () => {
    const { container } = render(
      <InputWorkspace bridge={bridge} processingRunning={false} onGenerate={() => undefined} />
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
