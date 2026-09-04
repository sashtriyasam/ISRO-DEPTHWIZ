import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { RenderingControls } from "./RenderingControls";

describe("RenderingControls", () => {
  it("renders all three mode buttons", () => {
    render(<RenderingControls currentMode="shaded" onModeChange={() => undefined} />);
    expect(screen.getByRole("button", { name: "Shaded rendering mode" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Wireframe rendering mode" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Shaded + Wireframe rendering mode" })).toBeInTheDocument();
  });

  it("marks the active mode without relying on color alone", () => {
    render(<RenderingControls currentMode="wireframe" onModeChange={() => undefined} />);
    expect(screen.getByRole("button", { name: "Wireframe rendering mode" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Shaded rendering mode" })).toHaveAttribute("aria-pressed", "false");
  });

  it("notifies mode changes", () => {
    const onModeChange = vi.fn();
    render(<RenderingControls currentMode="shaded" onModeChange={onModeChange} />);
    fireEvent.click(screen.getByRole("button", { name: "Shaded + Wireframe rendering mode" }));
    expect(onModeChange).toHaveBeenCalledWith("shaded-wireframe");
  });
});
