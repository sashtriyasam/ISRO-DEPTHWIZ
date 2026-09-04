import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { SessionStatus } from "./SessionStatus";

describe("SessionStatus", () => {
  it("renders session phase label", () => {
    render(<SessionPhase phase="empty" />);
    expect(screen.getByText(/Session Empty/i)).toBeTruthy();
  });

  it("renders processing phase", () => {
    render(<SessionPhase phase="processing" />);
    expect(screen.getByText(/Session Processing/i)).toBeTruthy();
  });

  it("renders ready phase", () => {
    render(<SessionPhase phase="ready" />);
    expect(screen.getByText(/Session Ready/i)).toBeTruthy();
  });

  it("renders error phase", () => {
    render(<SessionPhase phase="error" />);
    expect(screen.getByText(/Session Error/i)).toBeTruthy();
  });

  it("renders reset button when canReset true", () => {
    render(<SessionReset canReset />);
    expect(screen.getByRole("button", { name: /reset project session/i })).toBeTruthy();
  });

  it("does not render reset button when canReset false", () => {
    render(<SessionReset canReset={false} />);
    expect(screen.queryByRole("button", { name: /reset project session/i })).toBeNull();
  });

  it("renders modified badge when modified", () => {
    render(<SessionModifiedBadge modified="modified" />);
    expect(screen.getByText("modified")).toBeTruthy();
  });

  it("does not render modified badge when clean", () => {
    render(<SessionModifiedBadge modified="clean" />);
    expect(screen.queryByText("modified")).toBeNull();
  });

  it("modified badge has accessible label", () => {
    render(<SessionModifiedBadge modified="modified" />);
    expect(screen.getByLabelText("Analysis state active")).toBeTruthy();
  });

  it("calls onReset when reset clicked", async () => {
    const onReset = vi.fn();
    render(
      <SessionStatus
        phase="ready"
        modified="clean"
        canReset
        onReset={onReset}
      />
    );
    screen.getByRole("button", { name: /reset project session/i }).click();
    expect(onReset).toHaveBeenCalledOnce();
  });
});

function SessionPhase({ phase }: { phase: "empty" | "processing" | "ready" | "error" }) {
  return <SessionStatus phase={phase} modified="clean" canReset={false} />;
}

function SessionReset({ canReset }: { canReset: boolean }) {
  return <SessionStatus phase="empty" modified="clean" canReset={canReset} onReset={vi.fn()} />;
}

function SessionModifiedBadge({ modified }: { modified: "clean" | "modified" }) {
  return <SessionStatus phase="ready" modified={modified} canReset={false} />;
}
