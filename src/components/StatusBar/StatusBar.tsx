import { APP_VERSION } from "../../version";

interface StatusBarProps {
  sourceLabel: string;
  note: string;
}

export function StatusBar({ sourceLabel, note }: StatusBarProps) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-lg)", width: "100%", fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
      <span>{sourceLabel}</span>
      <span style={{ color: "var(--color-border)" }}>|</span>
      <span>{note}</span>
      <div style={{ flex: 1 }} />
      <span>DepthWizard v{APP_VERSION}</span>
    </div>
  );
}
