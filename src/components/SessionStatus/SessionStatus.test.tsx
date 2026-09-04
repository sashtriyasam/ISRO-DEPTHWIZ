import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { SessionStatus } from "./SessionStatus";

describe("SessionStatus", () => {
  it("renders session phase label", () => {
    render(<SessionPhase phase="empty" />);
    expect(screen.getByText(/Session Empty/i)).toBeTruthy();
  });

  it("renders reset button when canReset true", () => {
    render(<SessionReset canReset />);
    expect(screen.getByRole("button", { name: /reset project session/i })).toBeTruthy();
  });

  it("does not render reset button when canReset false", () => {
    render(<SessionReset canReset={false} />);
    expect(screen.queryByRole("button", { name: /reset project session/i })).toBeNull();
  });

  it("renders unsaved badge when dirty", () => {
    render(<SessionDirtyBadge dirty="dirty" />);
    expect(screen.getByText("unsaved")).toBeTruthy();
  });

  it("does not render unsaved badge when clean", () => {
    render(<SessionDirtyBadge dirty="clean" />);
    expect(screen.queryByText("unsaved")).toBeNull();
  });

  it("calls onReset when reset clicked", async () => {
    const onReset = vi.fn();
    render(
      <SessionStatus
        phase="ready"
        dirty="clean"
        canReset
        onReset={onReset}
      />
    );
    screen.getByRole("button", { name: /reset project session/i }).click();
    expect(onReset).toHaveBeenCalledOnce();
  });
});

function SessionPhase({ phase }: { phase: "empty" | "input-ready" | "processing" | "ready" | "error" }) {
  return <SessionStatus phase={phase} dirty="clean" canReset={false} />;
}

function SessionReset({ canReset }: { canReset: boolean }) {
  return <SessionStatus phase="empty" dirty="clean" canReset={canReset} onReset={vi.fn()} />;
}

function SessionDirtyBadge({ dirty }: { dirty: "clean" | "dirty" | "not-applicable" }) {
  return <SessionStatus phase="ready" dirty={dirty} canReset={false} />;
}
