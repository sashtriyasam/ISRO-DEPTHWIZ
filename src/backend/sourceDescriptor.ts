import { LocalServiceClient } from "../service/client";
import type { ServiceCapabilitiesWire } from "../service/wireTypes";
import type { ApplicationBackendSource } from "../input/applicationSource";

export const SYNTHETIC_BACKEND_ID = "synthetic-depth";

export type BackendSourceKind = "synthetic-development" | "production" | "fixture" | "unknown";

export type BackendAvailability =
  | { available: true }
  | { available: false; reason: string; action: string };

export interface BackendSourceDescriptor {
  id: string;
  label: string;
  kind: BackendSourceKind;
  availability: BackendAvailability;
  backendName: string | null;
  backendVersion: string | null;
  targetSemantics: string | null;
  capabilities: ServiceCapabilitiesWire | null;
}

export function kindForBackendName(backendName: string | null): BackendSourceKind {
  if (backendName === null) {
    return "unknown";
  }
  if (backendName === SYNTHETIC_BACKEND_ID) {
    return "synthetic-development";
  }
  return "production";
}

export function describeBackendSource(
  source: ApplicationBackendSource,
  capabilities: ServiceCapabilitiesWire | null,
  availability: BackendAvailability
): BackendSourceDescriptor {
  const registered = capabilities?.available_backends ?? null;
  const backendName =
    registered !== null && registered.length > 0 ? registered[0] : null;
  return {
    id: source.id,
    label: source.label,
    kind: kindForBackendName(backendName),
    availability,
    backendName,
    backendVersion: null,
    targetSemantics: source.kind === "file" ? source.targetSemantics : null,
    capabilities,
  };
}

export function isBackendRegistered(
  capabilities: ServiceCapabilitiesWire | null,
  backendId: string = SYNTHETIC_BACKEND_ID
): boolean {
  if (!capabilities) {
    return false;
  }
  return capabilities.available_backends.includes(backendId);
}

export async function probeBackendAvailability(
  client?: LocalServiceClient
): Promise<{ capabilities: ServiceCapabilitiesWire | null; availability: BackendAvailability }> {
  const active = client ?? new LocalServiceClient();
  try {
    const capabilities = await active.capabilities();
    if (!isBackendRegistered(capabilities)) {
      return {
        capabilities,
        availability: {
          available: false,
          reason: `Backend "${SYNTHETIC_BACKEND_ID}" is not registered by the service.`,
          action: "Check the backend installation; synthetic output will not be substituted.",
        },
      };
    }
    return { capabilities, availability: { available: true } };
  } catch (err) {
    return {
      capabilities: null,
      availability: {
        available: false,
        reason: err instanceof Error ? err.message : String(err),
        action: "Check that the backend process is reachable, then retry.",
      },
    };
  }
}
