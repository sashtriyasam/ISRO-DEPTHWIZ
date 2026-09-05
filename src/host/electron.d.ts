export interface ElectronHostCapabilities {
  runtime: "electron";
  processSpawning: boolean;
  localFilesystem: boolean;
  platform: string;
  packaged: boolean;
}

export interface DepthWizardElectron {
  getHostCapabilities(): Promise<ElectronHostCapabilities>;
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
