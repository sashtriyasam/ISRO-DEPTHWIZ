import { describe, it, expect } from "vitest";
import { LocalServiceClient } from "../service/client";
import {
  SYNTHETIC_BACKEND_ID,
  describeBackendSource,
  isBackendRegistered,
  kindForBackendName,
  probeBackendAvailability,
} from "./sourceDescriptor";
import type { ServiceCapabilitiesWire } from "../service/wireTypes";
import { ApplicationBackendSource } from "../input/applicationSource";

function capabilitiesWith(backends: string[]): ServiceCapabilitiesWire {
  return {
    contract_version: "1",
    supported_input_formats: [".png"],
    supported_target_semantics: ["absolute_elevation_dsm"],
    available_backends: backends,
    mesh_supported: true,
    geotiff_supported: true,
  };
}

describe("backend identity", () => {
  it("names the synthetic backend id", () => {
    expect(SYNTHETIC_BACKEND_ID).toBe("synthetic-depth");
  });

  it("classifies backend names without inventing production status", () => {
    expect(kindForBackendName("synthetic-depth")).toBe("synthetic-development");
    expect(kindForBackendName("depth-anything-v2")).toBe("production");
    expect(kindForBackendName(null)).toBe("unknown");
  });

  it("checks registration against live capabilities", () => {
    expect(isBackendRegistered(capabilitiesWith(["synthetic-depth"]))).toBe(true);
    expect(isBackendRegistered(capabilitiesWith(["other-model"]))).toBe(false);
    expect(isBackendRegistered(capabilitiesWith([]))).toBe(false);
    expect(isBackendRegistered(null)).toBe(false);
  });
});

describe("describeBackendSource", () => {
  it("describes a file source with registered capabilities", () => {
    const source = new ApplicationBackendSource({
      stagedPath: "tile.png",
      metadata: {
        filename: "tile.png",
        format: "png",
        width: 4,
        height: 4,
        bandCount: 3,
        dtype: "RGB",
        georeferencing: "non_georeferenced",
        crs: null,
        gsd: null,
        nodata: null,
        sizeBytes: 10,
        checksum: "abc",
      },
    });
    const descriptor = describeBackendSource(source, capabilitiesWith(["synthetic-depth"]), {
      available: true,
    });
    expect(descriptor.id).toBe(source.id);
    expect(descriptor.kind).toBe("synthetic-development");
    expect(descriptor.availability).toEqual({ available: true });
    expect(descriptor.backendName).toBe("synthetic-depth");
    expect(descriptor.targetSemantics).toBe("absolute_elevation_dsm");
  });

  it("refuses identity claims without capabilities", () => {
    const source = new ApplicationBackendSource({ syntheticSize: { width: 4, height: 4 } });
    const descriptor = describeBackendSource(source, null, {
      available: false,
      reason: "unreachable",
      action: "retry",
    });
    expect(descriptor.kind).toBe("unknown");
    expect(descriptor.backendName).toBeNull();
    expect(descriptor.availability).toEqual({
      available: false,
      reason: "unreachable",
      action: "retry",
    });
  });
});

describe("probeBackendAvailability", () => {
  it("reports available when the synthetic backend is registered", async () => {
    const client = {
      capabilities: async () => capabilitiesWith(["synthetic-depth"]),
    } as unknown as LocalServiceClient;
    const result = await probeBackendAvailability(client);
    expect(result.availability).toEqual({ available: true });
    expect(result.capabilities?.available_backends).toEqual(["synthetic-depth"]);
  });

  it("reports unavailable without substituting synthetic output", async () => {
    const client = {
      capabilities: async () => capabilitiesWith(["other-model"]),
    } as unknown as LocalServiceClient;
    const result = await probeBackendAvailability(client);
    expect(result.availability.available).toBe(false);
    if (!result.availability.available) {
      expect(result.availability.reason).toContain("not registered");
      expect(result.availability.action).toBeTruthy();
    }
  });

  it("reports unreachable backends with an actionable reason", async () => {
    const client = {
      capabilities: async () => {
        throw new Error("spawn ENOENT");
      },
    } as unknown as LocalServiceClient;
    const result = await probeBackendAvailability(client);
    expect(result.capabilities).toBeNull();
    expect(result.availability.available).toBe(false);
    if (!result.availability.available) {
      expect(result.availability.action).toBeTruthy();
    }
  });

  it("never fabricates availability", async () => {
    const calls: string[] = [];
    const client = {
      capabilities: async () => {
        calls.push("probed");
        return capabilitiesWith(["synthetic-depth"]);
      },
    } as unknown as LocalServiceClient;
    await probeBackendAvailability(client);
    expect(calls).toEqual(["probed"]);
  });
});

describe("request construction honesty", () => {
  it("never sends a backend id other than the registered synthetic one", () => {
    const client = new LocalServiceClient();
    const request = client.buildRequest({ inputPath: "tile.png" });
    expect(request.backend).toBe(SYNTHETIC_BACKEND_ID);
  });

  it("ServiceRequestArgs exposes no backend override", () => {
    const client = new LocalServiceClient();
    const request = client.buildRequest({ inputPath: "tile.png" });
    expect("backendOverride" in request).toBe(false);
    expect(Object.keys(request).sort()).toEqual(
      [
        "backend",
        "build_mesh",
        "contract_version",
        "export_compression",
        "export_overwrite",
        "geotiff_path",
        "input_path",
        "preprocessor",
        "target_semantics",
      ].sort()
    );
  });
});
