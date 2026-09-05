import type { BackendTerrainProduct } from "../backend/types";
import {
  meshDescriptorOf,
  relativeMeshDescriptorOf,
} from "../service/processing";
import type { ServiceResponseWire } from "../service/wireTypes";
import {
  ArtifactTransportFailure,
  type RelativeBundle,
  type TerrainBundle,
} from "./types";

function checksumOf(bundle: TerrainBundle): {
  expected: string | null;
  actual: string | null;
} {
  return {
    expected: bundle.response.summary.input_checksum,
    actual: bundle.terrain.mesh.source_checksum ?? null,
  };
}

export function verifyBundle(bundle: TerrainBundle): void {
  const { response, terrain } = bundle;
  const mesh = meshDescriptorOf(response);
  if (!mesh || !mesh.available) {
    throw new ArtifactTransportFailure({
      code: "ARTIFACT_UNAVAILABLE",
      message: "Service completed without an available mesh artifact",
      stage: null,
    });
  }

  const { expected, actual } = checksumOf(bundle);
  if (expected !== null && actual !== null && expected !== actual) {
    throw new ArtifactTransportFailure({
      code: "CHECKSUM_MISMATCH",
      message:
        "Terrain payload checksum does not match the service run summary",
      stage: null,
      detail: `expected input ${expected}, payload carries ${actual}`,
    });
  }

  const mismatches: string[] = [];
  if (mesh.semantics !== null && mesh.semantics !== terrain.mesh.semantics) {
    mismatches.push(
      `semantics descriptor=${mesh.semantics} payload=${terrain.mesh.semantics}`,
    );
  }
  const requestedTarget = response.summary.target_semantics;
  if (requestedTarget !== null && requestedTarget !== terrain.mesh.semantics) {
    mismatches.push(
      `target summary=${requestedTarget} payload=${terrain.mesh.semantics}`,
    );
  }
  if (mesh.units !== null && mesh.units !== terrain.mesh.units) {
    mismatches.push(
      `units descriptor=${mesh.units} payload=${terrain.mesh.units}`,
    );
  }
  if (mesh.width !== null && mesh.width !== terrain.mesh.width) {
    mismatches.push(
      `width descriptor=${mesh.width} payload=${terrain.mesh.width}`,
    );
  }
  if (mesh.height !== null && mesh.height !== terrain.mesh.height) {
    mismatches.push(
      `height descriptor=${mesh.height} payload=${terrain.mesh.height}`,
    );
  }
  if (mismatches.length > 0) {
    throw new ArtifactTransportFailure({
      code: "DESCRIPTOR_MISMATCH",
      message: "Terrain payload disagrees with the service artifact descriptor",
      stage: null,
      detail: mismatches.join("; "),
    });
  }
}

export function requireTerrainPayload(
  response: ServiceResponseWire,
  terrain: BackendTerrainProduct | null,
): asserts terrain is BackendTerrainProduct {
  const mesh = meshDescriptorOf(response);
  if (!mesh || !mesh.available) {
    throw new ArtifactTransportFailure({
      code: "ARTIFACT_UNAVAILABLE",
      message: "Service completed without an available mesh artifact",
      stage: null,
    });
  }
  if (!terrain) {
    throw new ArtifactTransportFailure({
      code: "PAYLOAD_FAILED",
      message: "Terrain payload missing for an available mesh descriptor",
      stage: null,
    });
  }
}

export function verifyRelativeBundle(bundle: RelativeBundle): void {
  const { response, relative } = bundle;
  const mesh = relativeMeshDescriptorOf(response);
  if (!mesh || !mesh.available) {
    throw new ArtifactTransportFailure({
      code: "ARTIFACT_UNAVAILABLE",
      message: "Service completed without an available relative mesh artifact",
      stage: null,
    });
  }

  const expected = response.summary.input_checksum;
  const actual = relative.mesh.source_checksum ?? null;
  if (expected !== null && actual !== null && expected !== actual) {
    throw new ArtifactTransportFailure({
      code: "CHECKSUM_MISMATCH",
      message:
        "Relative payload checksum does not match the service run summary",
      stage: null,
      detail: `expected input ${expected}, payload carries ${actual}`,
    });
  }

  const mismatches: string[] = [];
  if (mesh.semantics !== null && mesh.semantics !== relative.mesh.semantics) {
    mismatches.push(
      `semantics descriptor=${mesh.semantics} payload=${relative.mesh.semantics}`,
    );
  }
  if (mesh.units !== null && mesh.units !== relative.mesh.units) {
    mismatches.push(
      `units descriptor=${mesh.units} payload=${relative.mesh.units}`,
    );
  }
  if (mesh.width !== null && mesh.width !== relative.mesh.width) {
    mismatches.push(
      `width descriptor=${mesh.width} payload=${relative.mesh.width}`,
    );
  }
  if (mesh.height !== null && mesh.height !== relative.mesh.height) {
    mismatches.push(
      `height descriptor=${mesh.height} payload=${relative.mesh.height}`,
    );
  }
  if (mismatches.length > 0) {
    throw new ArtifactTransportFailure({
      code: "DESCRIPTOR_MISMATCH",
      message:
        "Relative payload disagrees with the service artifact descriptor",
      stage: null,
      detail: mismatches.join("; "),
    });
  }
}
