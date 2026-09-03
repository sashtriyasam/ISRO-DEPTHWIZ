import { StrictMode } from "react";
import { AppShell } from "../components/AppShell/AppShell";
import { Viewer } from "../viewer/Viewer";
import { useTestFixture } from "../fixtures/useTestFixture";
import { StatusBar } from "../components/StatusBar/StatusBar";

export function App() {
  const fixture = useTestFixture();

  return (
    <StrictMode>
      <AppShell
        header={<Header />}
        viewport={<Viewer scene={fixture} />}
        panel={<SidePanel />}
        statusbar={<StatusBar />}
      />
    </StrictMode>
  );
}

function Header() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-md)", height: "100%" }}>
      <span style={{ fontWeight: 600, fontSize: "var(--font-size-md)" }}>DepthWizard</span>
      <span style={{ color: "var(--color-text-muted)", fontSize: "var(--font-size-xs)" }}>
        v0.1.0-dev
      </span>
    </div>
  );
}

function SidePanel() {
  return (
    <div style={{ padding: "var(--spacing-md)", display: "flex", flexDirection: "column", gap: "var(--spacing-md)" }}>
      <div>
        <div style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "var(--spacing-sm)" }}>
          Scene Info
        </div>
        <div style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
          Deterministic test fixture
        </div>
      </div>
      <div>
        <div style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "var(--spacing-sm)" }}>
          Status
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-sm)" }}>
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--color-status-ok)" }} />
          <span style={{ fontSize: "var(--font-size-sm)", color: "var(--color-status-ok)" }}>Ready</span>
        </div>
      </div>
    </div>
  );
}
