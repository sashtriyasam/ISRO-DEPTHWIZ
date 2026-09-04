import { describe, it, expect } from "vitest";
import {
  validateServiceCapabilities,
  validateServiceResponse,
  ServiceWireError,
} from "./validator";

function validResponse(): Record<string, unknown> {
  return {
    contract_version: "1",
    success: true,
    final_state: "completed",
    states: ["input_validated", "preprocessing", "completed"],
    failure: null,
    artifacts: [
      {
        kind: "mesh",
        available: true,
        persisted: false,
        path: null,
        semantics: "absolute_elevation_dsm",
        units: "meters",
        width: 4,
        height: 4,
        georeferenced: false,
      },
    ],
    summary: {
      input_path: "tile.png",
      input_checksum: "abc",
      backend_name: "synthetic-depth",
      backend_version: "0.1.0",
      calibration_method: "scale_offset",
      calibration_reference: "synthetic-dev-ref",
      target_semantics: "absolute_elevation_dsm",
      mesh_requested: true,
      geotiff_path: null,
      engine_version: "0.1.0",
    },
  };
}

describe("validateServiceResponse", () => {
  it("accepts a valid response", () => {
    const parsed = validateServiceResponse(validResponse());
    expect(parsed.success).toBe(true);
    expect(parsed.final_state).toBe("completed");
    expect(parsed.artifacts).toHaveLength(1);
  });

  it("rejects wrong contract versions", () => {
    expect(() =>
      validateServiceResponse({ ...validResponse(), contract_version: "2" })
    ).toThrow(ServiceWireError);
  });

  it("rejects unknown states", () => {
    expect(() =>
      validateServiceResponse({ ...validResponse(), final_state: "flying" })
    ).toThrow(ServiceWireError);
    expect(() =>
      validateServiceResponse({ ...validResponse(), states: ["preprocessing", "warp"] })
    ).toThrow(ServiceWireError);
  });

  it("rejects malformed failures", () => {
    expect(() =>
      validateServiceResponse({
        ...validResponse(),
        success: false,
        final_state: "failed",
        failure: { message: "no code" },
      })
    ).toThrow(ServiceWireError);
  });

  it("rejects malformed artifact descriptors", () => {
    expect(() =>
      validateServiceResponse({ ...validResponse(), artifacts: [{ kind: "starship" }] })
    ).toThrow(ServiceWireError);
  });

  it("rejects success/final_state inconsistency", () => {
    expect(() =>
      validateServiceResponse({ ...validResponse(), final_state: "failed" })
    ).toThrow(ServiceWireError);
    expect(() =>
      validateServiceResponse({
        ...validResponse(),
        success: false,
        final_state: "completed",
        failure: { code: "X", message: "y", stage: null },
      })
    ).toThrow(ServiceWireError);
  });

  it("requires a failure record on unsuccessful responses", () => {
    expect(() =>
      validateServiceResponse({ ...validResponse(), success: false, final_state: "failed" })
    ).toThrow(ServiceWireError);
  });

  it("rejects malformed JSON shapes", () => {
    expect(() => validateServiceResponse(null)).toThrow(ServiceWireError);
    expect(() => validateServiceResponse("ok")).toThrow(ServiceWireError);
    expect(() => validateServiceResponse({})).toThrow(ServiceWireError);
  });
});

describe("validateServiceCapabilities", () => {
  it("accepts real capability shapes", () => {
    const parsed = validateServiceCapabilities({
      contract_version: "1",
      supported_input_formats: [".png"],
      supported_target_semantics: ["absolute_elevation_dsm"],
      available_backends: ["synthetic-depth"],
      mesh_supported: true,
      geotiff_supported: true,
    });
    expect(parsed.supported_input_formats).toEqual([".png"]);
  });

  it("rejects wrong versions and malformed fields", () => {
    expect(() =>
      validateServiceCapabilities({ contract_version: "9", supported_input_formats: [] })
    ).toThrow(ServiceWireError);
    expect(() =>
      validateServiceCapabilities({
        contract_version: "1",
        supported_input_formats: [".png"],
        supported_target_semantics: [],
        available_backends: [],
        mesh_supported: "yes",
        geotiff_supported: true,
      })
    ).toThrow(ServiceWireError);
  });
});
