export type HostRuntime = "browser" | "node";

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
    typeof process !== "undefined" &&
    typeof process.versions !== "undefined" &&
    typeof process.versions.node !== "undefined"
  ) {
    return "node";
  }
  return "browser";
}

export function detectHost(overrides: HostDetectionOverrides = {}): HostCapabilities {
  const runtime = overrides.runtime ?? detectRuntime();
  const desktop = runtime === "node";
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
  return "Desktop host";
}

export function canStageInputFiles(capabilities: HostCapabilities): boolean {
  return capabilities.localFilesystem;
}

export function canSpawnBackend(capabilities: HostCapabilities): boolean {
  return capabilities.processSpawning;
}
