export type HostRuntime = "browser" | "node" | "electron";

export interface HostCapabilities {
  runtime: HostRuntime;
  processSpawning: boolean;
  localFilesystem: boolean;
}

export interface HostDetectionOverrides {
  runtime?: HostRuntime;
  processSpawning?: boolean;
  localFilesystem?: boolean;
}

function detectRuntime(): HostRuntime {
  if (
    typeof window !== "undefined" &&
    typeof window.depthwizard !== "undefined"
  ) {
    return "electron";
  }
  if (
    typeof process !== "undefined" &&
    typeof process.versions !== "undefined"
  ) {
    if (typeof process.versions.electron !== "undefined") {
      return "electron";
    }
    if (typeof process.versions.node !== "undefined") {
      return "node";
    }
  }
  return "browser";
}

export function detectHost(
  overrides: HostDetectionOverrides = {},
): HostCapabilities {
  const runtime = overrides.runtime ?? detectRuntime();
  const desktop = runtime === "node" || runtime === "electron";
  return {
    runtime,
    processSpawning: overrides.processSpawning ?? desktop,
    localFilesystem: overrides.localFilesystem ?? desktop,
  };
}

export function hostLabel(capabilities: HostCapabilities): string {
  if (capabilities.runtime === "browser") {
    return "Browser (desktop backend unavailable)";
  }
  if (capabilities.runtime === "electron") {
    return "Desktop host (Electron)";
  }
  return "Desktop host";
}

export function canStageInputFiles(capabilities: HostCapabilities): boolean {
  return capabilities.localFilesystem;
}

export function canSpawnBackend(capabilities: HostCapabilities): boolean {
  return capabilities.processSpawning;
}
