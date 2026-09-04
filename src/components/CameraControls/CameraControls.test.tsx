import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CameraControls } from "./CameraControls";

describe("CameraControls", () => {
  it("renders all three mode buttons with accessible names", () => {
    render(
      <CameraControls currentMode="orbit" onModeChange={() => undefined} onFrameScene={() => undefined} onReset={() => undefined} />
    );
    expect(screen.getByRole("button", { name: "Orbit camera mode" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "First Person camera mode" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aerial camera mode" })).toBeInTheDocument();
  });

  it("marks the active mode without relying on color alone", () => {
    render(
      <CameraControls currentMode="aerial" onModeChange={() => undefined} onFrameScene={() => undefined} onReset={() => undefined} />
    );
    expect(screen.getByRole("button", { name: "Aerial camera mode" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Orbit camera mode" })).toHaveAttribute("aria-pressed", "false");
  });

  it("notifies mode changes", () => {
    const onModeChange = vi.fn();
    render(
      <CameraControls currentMode="orbit" onModeChange={onModeChange} onFrameScene={() => undefined} onReset={() => undefined} />
    );
    fireEvent.click(screen.getByRole("button", { name: "First Person camera mode" }));
    expect(onModeChange).toHaveBeenCalledWith("first-person");
  });

  it("shows first-person instructions and the picking note only in that mode", () => {
    const { rerender } = render(
      <CameraControls currentMode="orbit" onModeChange={() => undefined} onFrameScene={() => undefined} onReset={() => undefined} />
    );
    expect(screen.queryByText(/Terrain picking is paused/)).toBeNull();
    rerender(
      <CameraControls currentMode="first-person" onModeChange={() => undefined} onFrameScene={() => undefined} onReset={() => undefined} />
    );
    expect(screen.getByText(/W A S D/)).toBeInTheDocument();
    expect(screen.getByText(/Terrain picking is paused/)).toBeInTheDocument();
  });

  it("keeps Frame Scene and Reset actions", () => {
    const onFrameScene = vi.fn();
    const onReset = vi.fn();
    render(
      <CameraControls currentMode="orbit" onModeChange={() => undefined} onFrameScene={onFrameScene} onReset={onReset} />
    );
    fireEvent.click(screen.getByRole("button", { name: "Frame scene" }));
    fireEvent.click(screen.getByRole("button", { name: "Reset camera" }));
    expect(onFrameScene).toHaveBeenCalledOnce();
    expect(onReset).toHaveBeenCalledOnce();
  });
});
