import type { BridgeExecutionHooks } from "../backend/bridge";
import { OperationCancelledError } from "../backend/bridge";
import {
  validateServiceCapabilities,
  validateServiceResponse,
  ServiceWireError,
} from "./validator";
import { SubprocessServiceTransport, type ServiceTransport } from "./transport";
import {
  SERVICE_CONTRACT_VERSION,
  type MetricTargetSemantics,
  type ServiceCapabilitiesWire,
  type ServiceRequestWire,
  type ServiceResponseWire,
} from "./wireTypes";

export interface ServiceExecutionArgs {
  inputPath: string;
  targetSemantics?: MetricTargetSemantics;
  buildMesh?: boolean;
  backend?: string;
}

export interface ServiceExecution {
  request: ServiceRequestWire;
  response: ServiceResponseWire;
}

export class LocalServiceClient {
  private transport: ServiceTransport;
  private capabilitiesCache: ServiceCapabilitiesWire | null = null;

  constructor(transport?: ServiceTransport) {
    this.transport = transport ?? new SubprocessServiceTransport();
  }

  async capabilities(
    hooks: BridgeExecutionHooks = {},
  ): Promise<ServiceCapabilitiesWire> {
    if (this.capabilitiesCache) {
      return this.capabilitiesCache;
    }
    let raw: unknown;
    try {
      raw = await this.transport.invoke({ capabilities: true }, hooks);
    } catch (err) {
      if (err instanceof OperationCancelledError) {
        throw err;
      }
      throw new ServiceWireError(
        `Service capabilities unavailable: ${err instanceof Error ? err.message : String(err)}`,
      );
    }
    if (typeof raw !== "object" || raw === null || !("capabilities" in raw)) {
      throw new ServiceWireError(
        "Malformed capabilities envelope from service",
      );
    }
    const parsed = validateServiceCapabilities(
      (raw as { capabilities: unknown }).capabilities,
    );
    this.capabilitiesCache = parsed;
    return parsed;
  }

  buildRequest(args: ServiceExecutionArgs): ServiceRequestWire {
    if (!args.inputPath || args.inputPath.trim().length === 0) {
      throw new ServiceWireError(
        "Service request needs a non-empty input path",
      );
    }
    return {
      contract_version: SERVICE_CONTRACT_VERSION,
      input_path: args.inputPath,
      target_semantics: args.targetSemantics ?? "absolute_elevation_dsm",
      backend: args.backend ?? "synthetic-depth",
      preprocessor: "identity",
      build_mesh: args.buildMesh ?? true,
      geotiff_path: null,
      export_compression: "deflate",
      export_overwrite: false,
    };
  }

  async executeService(
    args: ServiceExecutionArgs,
    hooks: BridgeExecutionHooks = {},
  ): Promise<ServiceExecution> {
    const request = this.buildRequest(args);
    let raw: unknown;
    try {
      raw = await this.transport.invoke({ request }, hooks);
    } catch (err) {
      if (err instanceof OperationCancelledError) {
        throw err;
      }
      throw new ServiceWireError(
        `Service execution failed: ${err instanceof Error ? err.message : String(err)}`,
      );
    }
    if (typeof raw !== "object" || raw === null || !("response" in raw)) {
      throw new ServiceWireError(
        "Malformed service envelope: missing response",
      );
    }
    const response = validateServiceResponse(
      (raw as { response: unknown }).response,
    );
    return { request, response };
  }
}
