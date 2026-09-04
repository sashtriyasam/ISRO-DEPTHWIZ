import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { FlythroughPanel } from "./FlythroughPanel";
import type { FlythroughWaypoint, PlaybackStatus } from "../../flythrough/types";

function waypoints(count: number): FlythroughWaypoint[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `wp-${i + 1}`,
    position: { x: i * 4, y: 4, z: 7 },
    target: { x: 0, y: 0, z: 0 },
  }));
}

function baseProps(overrides: Partial<Parameters<typeof FlythroughPanel>[0]> = {}) {
  return {
    waypoints: [] as readonly FlythroughWaypoint[],
    status: "idle" as PlaybackStatus,
    speed: 1 as const,
    currentIndex: 0,
    canCapture: true,
    navigationLocked: false,
    onAddWaypoint: () => undefined,
    onRemoveWaypoint: () => undefined,
    onClear: () => undefined,
    onPlay: () => undefined,
    onPause: () => undefined,
    onResume: () => undefined,
    onStop: () => undefined,
    onReset: () => undefined,
    onSpeedChange: () => undefined,
    ...overrides,
  };
}

describe("FlythroughPanel", () => {
  it("explains the empty state", () => {
    render(<FlythroughPanel {...baseProps()} />);
    expect(screen.getByText("Flythrough")).toBeInTheDocument();
    expect(screen.getByText(/Add a waypoint from the current camera position/)).toBeInTheDocument();
  });

  it("requires a second waypoint before playback", () => {
    render(<FlythroughPanel {...baseProps({ waypoints: waypoints(1) })} />);
    expect(screen.getByText(/Add at least one more waypoint/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Play flythrough" })).toBeNull();
  });

  it("lists waypoints with remove actions", () => {
    const onRemoveWaypoint = vi.fn();
    render(<FlythroughPanel {...baseProps({ waypoints: waypoints(2), onRemoveWaypoint })} />);
    expect(screen.getByText("Waypoint 1")).toBeInTheDocument();
    expect(screen.getByText("Waypoint 2")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Remove waypoint 1" }));
    expect(onRemoveWaypoint).toHaveBeenCalledWith("wp-1");
  });

  it("captures waypoints on demand, never automatically", () => {
    const onAddWaypoint = vi.fn();
    render(<FlythroughPanel {...baseProps({ onAddWaypoint })} />);
    expect(onAddWaypoint).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Add waypoint from current camera" }));
    expect(onAddWaypoint).toHaveBeenCalledOnce();
  });

  it("drives play, pause, resume, stop, and reset", () => {
    const handlers = {
      onPlay: vi.fn(),
      onPause: vi.fn(),
      onResume: vi.fn(),
      onStop: vi.fn(),
      onReset: vi.fn(),
    };
    const { rerender } = render(
      <FlythroughPanel {...baseProps({ waypoints: waypoints(2), status: "ready", ...handlers })} />
    );
    fireEvent.click(screen.getByRole("button", { name: "Play flythrough" }));
    expect(handlers.onPlay).toHaveBeenCalledOnce();

    rerender(
      <FlythroughPanel {...baseProps({ waypoints: waypoints(2), status: "playing", ...handlers })} />
    );
    expect(screen.getByText("Flythrough playing…")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Pause flythrough" }));
    expect(handlers.onPause).toHaveBeenCalledOnce();

    rerender(
      <FlythroughPanel {...baseProps({ waypoints: waypoints(2), status: "paused", ...handlers })} />
    );
    fireEvent.click(screen.getByRole("button", { name: "Resume flythrough" }));
    expect(handlers.onResume).toHaveBeenCalledOnce();
    fireEvent.click(screen.getByRole("button", { name: "Stop flythrough" }));
    expect(handlers.onStop).toHaveBeenCalledOnce();

    rerender(
      <FlythroughPanel {...baseProps({ waypoints: waypoints(2), status: "completed", ...handlers })} />
    );
    expect(screen.getByText(/completed at the final waypoint/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Reset flythrough" }));
    expect(handlers.onReset).toHaveBeenCalledOnce();
  });

  it("shows waypoint progress without percentages", () => {
    const { container } = render(
      <FlythroughPanel {...baseProps({ waypoints: waypoints(3), status: "playing", currentIndex: 1 })} />
    );
    expect(screen.getByText(/Waypoint 2 of 3/)).toBeInTheDocument();
    expect(container.textContent).not.toContain("%");
  });

  it("offers only the typed speed set with 1× default", () => {
    const onSpeedChange = vi.fn();
    render(<FlythroughPanel {...baseProps({ waypoints: waypoints(2), onSpeedChange })} />);
    expect(screen.getByRole("button", { name: "Playback speed 1×" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "Playback speed 2×" }));
    expect(onSpeedChange).toHaveBeenCalledWith(2);
    fireEvent.click(screen.getByRole("button", { name: "Playback speed 0.5×" }));
    expect(onSpeedChange).toHaveBeenCalledWith(0.5);
  });

  it("disables capture while playing and notes locked navigation", () => {
    render(
      <FlythroughPanel
        {...baseProps({ waypoints: waypoints(2), status: "playing", navigationLocked: true })}
      />
    );
    expect(screen.getByRole("button", { name: "Add waypoint from current camera" })).toBeDisabled();
    expect(screen.getByText(/Manual camera controls resume after Stop/)).toBeInTheDocument();
  });

  it("clears the trajectory explicitly", () => {
    const onClear = vi.fn();
    render(<FlythroughPanel {...baseProps({ waypoints: waypoints(2), onClear })} />);
    fireEvent.click(screen.getByRole("button", { name: "Clear waypoints" }));
    expect(onClear).toHaveBeenCalledOnce();
  });
});
