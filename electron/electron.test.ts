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
    // ipcRenderer is imported but not exposed to the renderer
    // Check that it's not passed to contextBridge.exposeInMainWorld
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
});

describe("Electron API shape", () => {
  const typesSource = readFileSync(HOST_TYPES, "utf-8");

  it("defines ElectronHostCapabilities", () => {
    expect(typesSource).toContain("ElectronHostCapabilities");
    expect(typesSource).toContain('runtime: "electron"');
  });

  it("defines DepthWizardElectron interface", () => {
    expect(typesSource).toContain("DepthWizardElectron");
  });

  it("includes required methods", () => {
    expect(typesSource).toContain("getHostCapabilities");
    expect(typesSource).toContain("launchService");
    expect(typesSource).toContain("terminateService");
    expect(typesSource).toContain("executeService");
  });

  it("does not expose dangerous methods", () => {
    expect(typesSource).not.toContain("exec(");
    expect(typesSource).not.toContain("spawn(");
    expect(typesSource).not.toContain("require(");
  });
});
