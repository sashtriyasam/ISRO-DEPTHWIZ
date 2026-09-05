import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

const ROOT = resolve(__dirname, "..");
const ELECTRON_MAIN = resolve(ROOT, "electron", "main.ts");
const ELECTRON_PRELOAD = resolve(ROOT, "electron", "preload.ts");
const HOST_TYPES = resolve(ROOT, "src", "host", "electron.d.ts");

describe("Electron security audit", () => {
  const mainSource = readFileSync(ELECTRON_MAIN, "utf-8");
  const preloadSource = readFileSync(ELECTRON_PRELOAD, "utf-8");

  it("contextIsolation is enabled", () => {
    expect(mainSource).toContain("contextIsolation: true");
  });

  it("nodeIntegration is disabled", () => {
    expect(mainSource).toContain("nodeIntegration: false");
  });

  it("sandbox is enabled", () => {
    expect(mainSource).toContain("sandbox: true");
  });

  it("webSecurity is enabled", () => {
    expect(mainSource).toContain("webSecurity: true");
  });

  it("allowRunningInsecureContent is disabled", () => {
    expect(mainSource).toContain("allowRunningInsecureContent: false");
  });

  it("experimentalFeatures is disabled", () => {
    expect(mainSource).toContain("experimentalFeatures: false");
  });

  it("nodeIntegrationInWorker is disabled", () => {
    expect(mainSource).toContain("nodeIntegrationInWorker: false");
  });

  it("nodeIntegrationInSubFrames is disabled", () => {
    expect(mainSource).toContain("nodeIntegrationInSubFrames: false");
  });

  it("navigateOnDragDrop is disabled", () => {
    expect(mainSource).toContain("navigateOnDragDrop: false");
  });

  it("navigation is restricted via will-navigate", () => {
    expect(mainSource).toContain("will-navigate");
    expect(mainSource).toContain("event.preventDefault()");
  });

  it("new window creation is blocked", () => {
    expect(mainSource).toContain("setWindowOpenHandler");
    expect(mainSource).toContain('action: "deny"');
  });

  it("CSP header is set", () => {
    expect(mainSource).toContain("Content-Security-Policy");
    expect(mainSource).toContain("script-src 'self'");
  });

  it("no unsafe-eval in CSP", () => {
    expect(mainSource).not.toContain("unsafe-eval");
  });

  it("no unsafe-inline script-src in CSP", () => {
    const cspStart = mainSource.indexOf("Content-Security-Policy");
    const cspEnd = mainSource.indexOf("];", cspStart);
    const cspSection = mainSource.substring(cspStart, cspEnd);
    expect(cspSection).not.toContain("script-src 'unsafe-inline'");
  });

  it("IPC sender validation is present", () => {
    expect(mainSource).toContain("validateSender");
    expect(mainSource).toContain("rejectUnauthorized");
  });

  it("no wildcard IPC handlers", () => {
    expect(mainSource).not.toContain('ipcMain.handle("*"');
    expect(mainSource).not.toContain("ipcMain.on('*'");
  });

  it("no eval usage", () => {
    expect(mainSource).not.toContain("eval(");
    expect(mainSource).not.toContain("new Function(");
  });

  it("no shell.openExternal", () => {
    expect(mainSource).not.toContain("shell.openExternal");
  });

  it("no arbitrary process spawning from renderer", () => {
    expect(mainSource).not.toContain("exec(");
    expect(mainSource).not.toContain("execSync(");
    expect(mainSource).not.toContain("spawnSync(");
  });

  it("preload does not expose ipcRenderer directly", () => {
    const exposeMatch = preloadSource.match(
      /exposeInMainWorld\([^)]+\{([^}]+)\}/s,
    );
    if (exposeMatch) {
      expect(exposeMatch[1]).not.toContain("ipcRenderer");
    }
    expect(preloadSource).toContain("safeInvoke");
  });

  it("preload does not expose dangerous modules", () => {
    const dangerous = [
      "exposeInMainWorld('shell'",
      "exposeInMainWorld('fs'",
      "exposeInMainWorld('path'",
      "exposeInMainWorld('child_process'",
      "exposeInMainWorld('process'",
      "exposeInMainWorld('require'",
    ];
    for (const pattern of dangerous) {
      expect(preloadSource).not.toContain(pattern);
    }
  });

  it("preload uses channel allowlist", () => {
    expect(preloadSource).toContain("ALLOWED_CHANNELS");
    expect(preloadSource).toContain("Blocked IPC channel");
  });

  it("Python resolution uses system Python (external prerequisite)", () => {
    expect(mainSource).toContain("getPythonPath");
    expect(mainSource).toContain("DEPTHWIZARD_PYTHON");
  });

  it("Python missing produces actionable error", () => {
    expect(mainSource).toContain("Install Python 3.10+");
  });

  it("Python missing produces actionable error message", () => {
    expect(mainSource).toContain("Python not found");
    expect(mainSource).toContain("DEPTHWIZARD_PYTHON");
  });

  it("checkpoint resolution has deterministic priority", () => {
    expect(mainSource).toContain("DW_DAV2_CKPT");
    expect(mainSource).toContain("userData");
    expect(mainSource).toContain("resourcesPath");
  });

  it("input path validation rejects traversal without platform-dependent normalization", () => {
    expect(mainSource).toContain('segments.includes("..")');
  });

  it("execute-service timeout is capped", () => {
    expect(mainSource).toContain("Math.min");
    expect(mainSource).toContain("600_000");
  });

  it("process cleanup happens on all exit paths", () => {
    expect(mainSource).toContain('app.on("before-quit"');
    expect(mainSource).toContain('app.on("will-quit"');
    expect(mainSource).toContain('app.on("window-all-closed"');
    expect(mainSource).toContain("render-process-gone");
  });
});

describe("Electron API shape", () => {
  const typesSource = readFileSync(HOST_TYPES, "utf-8");

  it("defines ElectronHostCapabilities", () => {
    expect(typesSource).toContain("ElectronHostCapabilities");
    expect(typesSource).toContain('runtime: "electron"');
  });

  it("defines CheckpointStatus", () => {
    expect(typesSource).toContain("CheckpointStatus");
    expect(typesSource).toContain("exists: boolean");
  });

  it("defines DepthWizardElectron interface", () => {
    expect(typesSource).toContain("DepthWizardElectron");
  });

  it("includes all required methods", () => {
    expect(typesSource).toContain("getHostCapabilities");
    expect(typesSource).toContain("resolvePythonPath");
    expect(typesSource).toContain("resolveCheckpointPath");
    expect(typesSource).toContain("getCheckpointStatus");
    expect(typesSource).toContain("getScriptsDir");
    expect(typesSource).toContain("launchService");
    expect(typesSource).toContain("terminateService");
    expect(typesSource).toContain("executeService");
  });

  it("getHostCapabilities can return null (auth rejection)", () => {
    expect(typesSource).toContain("Promise<ElectronHostCapabilities | null>");
  });

  it("does not expose dangerous methods", () => {
    expect(typesSource).not.toContain("exec(");
    expect(typesSource).not.toContain("spawn(");
    expect(typesSource).not.toContain("require(");
  });
});
