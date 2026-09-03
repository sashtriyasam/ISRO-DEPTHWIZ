export function StatusBar() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-lg)", width: "100%", fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
      <span>Development Fixture</span>
      <span style={{ color: "var(--color-border)" }}>|</span>
      <span>Synthetic terrain — not scientific output</span>
      <div style={{ flex: 1 }} />
      <span>DepthWizard v0.1.0</span>
    </div>
  );
}
