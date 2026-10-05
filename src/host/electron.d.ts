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
  /** Actual SHA-256 of the file (empty when missing). */
  hash: string;
  /** True only when the actual hash equals the pinned checkpoint hash. */
  verified: boolean;
}

export interface DepthWizardElectron {
  getHostCapabilities(): Promise<ElectronHostCapabilities | null>;
  resolvePythonPath(): Promise<string | null>;
  resolveCheckpointPath(): Promise<string | null>;
  getCheckpointStatus(): Promise<CheckpointStatus | null>;
  getScriptsDir(): Promise<string | null>;
  executeService(args: {
    payload: unknown;
    timeoutMs?: number;
    /** Lets cancelService terminate this run's Python process. */
    requestId?: string;
  }): Promise<unknown>;
  cancelService(args: { requestId: string }): Promise<{ cancelled: boolean }>;
  stageInputBytes(args: {
    bytes: Uint8Array;
    filename: string;
  }): Promise<{ path: string } | { error: string }>;
  cleanupStagedInput(args: {
    stagedPath: string;
  }): Promise<{ cleaned: boolean }>;
  showBackendSetup?(): Promise<void>;
  /**
   * Subscribe to stage-update events pushed by the main process during
   * execute-service. Returns an unsubscribe function.
   */
  onStageUpdate(callback: (stage: string) => void): () => void;
}

declare global {
  interface Window {
    depthwizard?: DepthWizardElectron;
  }
}

export {};
