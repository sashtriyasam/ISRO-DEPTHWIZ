import { ReactNode } from "react";

interface AppShellProps {
  header: ReactNode;
  viewport: ReactNode;
  panel: ReactNode;
  statusbar: ReactNode;
}

export function AppShell({ header, viewport, panel, statusbar }: AppShellProps) {
  return (
    <div className="app-shell">
      <header className="app-header">{header}</header>
      <div className="app-body">
        <main className="app-viewport">{viewport}</main>
        <aside className="app-panel">{panel}</aside>
      </div>
      <footer className="app-statusbar">{statusbar}</footer>

      <style>{`
        .app-shell {
          display: flex;
          flex-direction: column;
          width: 100%;
          height: 100%;
        }
        .app-header {
          height: var(--header-height);
          min-height: var(--header-height);
          background: var(--color-bg-secondary);
          border-bottom: 1px solid var(--color-border-subtle);
          display: flex;
          align-items: center;
          padding: 0 var(--spacing-lg);
          z-index: 10;
        }
        .app-body {
          flex: 1;
          display: flex;
          overflow: hidden;
          min-height: 0;
        }
        .app-viewport {
          flex: 1;
          position: relative;
          overflow: hidden;
          background: var(--color-bg-primary);
        }
        .app-panel {
          width: var(--panel-width);
          min-width: var(--panel-width);
          background: var(--color-bg-secondary);
          border-left: 1px solid var(--color-border-subtle);
          overflow-y: auto;
        }
        .app-statusbar {
          height: var(--statusbar-height);
          min-height: var(--statusbar-height);
          background: var(--color-bg-secondary);
          border-top: 1px solid var(--color-border-subtle);
          display: flex;
          align-items: center;
          padding: 0 var(--spacing-lg);
        }
      `}</style>
    </div>
  );
}
