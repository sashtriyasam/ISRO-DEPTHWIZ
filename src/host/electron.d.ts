export interface ElectronHostCapabilities {
  runtime: "electron";
  processSpawning: boolean;
  localFilesystem: boolean;
  platform: string;
  packaged: boolean;
}

export interface CheckpointStatus {
  exists: boolean;
  path: string;
  hash: string;
}

export interface DepthWizardElectron {
  getHostCapabilities(): Promise<ElectronHostCapabilities | null>;
  resolvePythonPath(): Promise<string | null>;
  resolveCheckpointPath(): Promise<string | null>;
  getCheckpointStatus(): Promise<CheckpointStatus | null>;
  getScriptsDir(): Promise<string | null>;
  launchService(args: {
    inputPath?: string;
    targetMode?: string;
  }): Promise<{ pid?: number; error?: string }>;
  terminateService(): Promise<{ terminated: boolean }>;
  executeService(args: {
    payload: unknown;
    timeoutMs?: number;
  }): Promise<unknown>;
}

declare global {
  interface Window {
    depthwizard?: DepthWizardElectron;
  }
}

export {};
