export interface ElectronHostCapabilities {
  runtime: "electron";
  processSpawning: boolean;
  localFilesystem: boolean;
  platform: string;
}

export interface DepthWizardElectron {
  getHostCapabilities(): Promise<ElectronHostCapabilities>;
  resolvePythonPath(): Promise<string>;
  resolveCheckpointPath(): Promise<string>;
  getScriptsDir(): Promise<string>;
  launchService(args: {
    inputPath?: string;
    targetMode?: string;
  }): Promise<{ pid?: number; error?: string }>;
  terminateService(): Promise<{ terminated: boolean }>;
}

declare global {
  interface Window {
    depthwizard?: DepthWizardElectron;
  }
}

export {};
