import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ProcessingPanel } from "./ProcessingPanel";
import type { ProcessingState } from "../../processing/types";

describe("ProcessingPanel", () => {
  it("renders idle state", () => {
    render(<ProcessingPanel state={{ status: "idle" }} />);
    expect(screen.getByText("Processing")).toBeInTheDocument();
    expect(screen.getByText(/No processing operation/)).toBeInTheDocument();
  });

  it("renders running stage without percentages", () => {
    const state: ProcessingState = {
      status: "running",
      operationId: "op-1",
      sourceId: "backend-synthetic",
      sourceLabel: "Synthetic Development Backend",
      stage: "dsm_generation",
      completedStages: [],
      cancellable: true,
    };
    const { container } = render(<ProcessingPanel state={state} />);
    expect(screen.getByText("Generating DSM")).toBeInTheDocument();
    expect(screen.getByText("Processing…")).toBeInTheDocument();
    expect(container.textContent).not.toContain("%");
  });

  it("hides cancel when operation is not cancellable", () => {
    const state: ProcessingState = {
      status: "running",
      operationId: "op-1",
      sourceId: "s",
      sourceLabel: "s",
      stage: "loading",
      completedStages: [],
      cancellable: false,
    };
    render(<ProcessingPanel state={state} />);
    expect(screen.queryByRole("button", { name: "Cancel operation" })).toBeNull();
  });

  it("calls onCancel", () => {
    const onCancel = vi.fn();
    const state: ProcessingState = {
      status: "running",
      operationId: "op-1",
      sourceId: "s",
      sourceLabel: "s",
      stage: "loading",
      completedStages: [],
      cancellable: true,
    };
    render(<ProcessingPanel state={state} onCancel={onCancel} />);
    fireEvent.click(screen.getByRole("button", { name: "Cancel operation" }));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("renders error with stage, code, and previous-result note", () => {
    const state: ProcessingState = {
      status: "error",
      operationId: "op-1",
      sourceId: "s",
      sourceLabel: "s",
      failure: {
        code: "BACKEND_ERROR",
        message: "python exploded",
        stage: "inference_running",
        phase: "process",
        previousAvailable: true,
      },
      completedStages: [],
    };
    const { container } = render(<ProcessingPanel state={state} />);
    expect(screen.getByText("Failed")).toBeInTheDocument();
    expect(screen.getByText("Running depth estimation")).toBeInTheDocument();
    expect(container.textContent).toContain("BACKEND_ERROR");
    expect(screen.getByText("Previous result remains available.")).toBeInTheDocument();
    expect(screen.getByText(/review the input and try again/)).toBeInTheDocument();
  });

  it("renders cancelled distinctly from failure", () => {
    const state: ProcessingState = {
      status: "cancelled",
      operationId: "op-1",
      sourceId: "s",
      sourceLabel: "s",
      previousAvailable: true,
      completedStages: [],
    };
    const { container } = render(<ProcessingPanel state={state} />);
    expect(screen.getByText("Cancelled")).toBeInTheDocument();
    expect(container.textContent).not.toContain("Failed");
    expect(screen.getByText("Previous result remains available.")).toBeInTheDocument();
  });

  it("renders ready summary", () => {
    const state: ProcessingState = {
      status: "ready",
      operationId: "op-1",
      sourceId: "s",
      sourceLabel: "s",
      artifactId: "a",
      completedStages: ["preprocessing", "inference_running"],
      warnings: [],
    };
    render(<ProcessingPanel state={state} />);
    expect(screen.getByText("Ready")).toBeInTheDocument();
    expect(screen.getByText("2 completed")).toBeInTheDocument();
  });
});
