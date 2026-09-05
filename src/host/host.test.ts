import { describe, it, expect } from "vitest";
import {
  detectHost,
  hostLabel,
  canSpawnBackend,
  canStageInputFiles,
} from "./host";

describe("detectHost", () => {
  it("detects the Node test runtime as a desktop-capable host", () => {
    const host = detectHost();
    expect(host.runtime).toBe("node");
    expect(host.processSpawning).toBe(true);
    expect(host.localFilesystem).toBe(true);
  });

  it("accepts a browser descriptor through injection", () => {
    const host = detectHost({
      runtime: "browser",
      processSpawning: false,
      localFilesystem: false,
    });
    expect(host.runtime).toBe("browser");
    expect(canSpawnBackend(host)).toBe(false);
    expect(canStageInputFiles(host)).toBe(false);
  });

  it("accepts a future desktop host that is not Node", () => {
    const host = detectHost({
      runtime: "browser",
      processSpawning: true,
      localFilesystem: true,
    });
    expect(canSpawnBackend(host)).toBe(true);
    expect(canStageInputFiles(host)).toBe(true);
  });

  it("keeps host capability independent from backend identity", () => {
    const capable = detectHost({
      runtime: "node",
      processSpawning: true,
      localFilesystem: true,
    });
    expect(canSpawnBackend(capable)).toBe(true);
    expect(hostLabel(capable)).not.toContain("production");
    expect(hostLabel(capable)).not.toContain("model");
  });

  it("detects Electron as desktop-capable host", () => {
    const host = detectHost({
      runtime: "electron",
      processSpawning: true,
      localFilesystem: true,
    });
    expect(host.runtime).toBe("electron");
    expect(canSpawnBackend(host)).toBe(true);
    expect(canStageInputFiles(host)).toBe(true);
  });
});

describe("hostLabel", () => {
  it("states browser limitation honestly", () => {
    expect(hostLabel(detectHost({ runtime: "browser" }))).toBe(
      "Browser (desktop backend unavailable)"
    );
  });

  it("never claims production readiness", () => {
    expect(hostLabel(detectHost())).toBe("Desktop host");
  });

  it("labels Electron host", () => {
    expect(hostLabel(detectHost({ runtime: "electron" }))).toBe(
      "Desktop host (Electron)"
    );
  });
});
