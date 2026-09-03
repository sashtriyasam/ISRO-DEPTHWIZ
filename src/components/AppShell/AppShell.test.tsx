import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AppShell } from "./AppShell";

describe("AppShell", () => {
  it("renders header, viewport, panel, and statusbar", () => {
    render(
      <AppShell
        header={<div data-testid="header">Header</div>}
        viewport={<div data-testid="viewport">Viewport</div>}
        panel={<div data-testid="panel">Panel</div>}
        statusbar={<div data-testid="statusbar">Status</div>}
      />
    );

    expect(screen.getByTestId("header")).toBeInTheDocument();
    expect(screen.getByTestId("viewport")).toBeInTheDocument();
    expect(screen.getByTestId("panel")).toBeInTheDocument();
    expect(screen.getByTestId("statusbar")).toBeInTheDocument();
  });

  it("has app-shell root class", () => {
    const { container } = render(
      <AppShell
        header={<div />}
        viewport={<div />}
        panel={<div />}
        statusbar={<div />}
      />
    );
    expect(container.querySelector(".app-shell")).toBeInTheDocument();
  });
});
