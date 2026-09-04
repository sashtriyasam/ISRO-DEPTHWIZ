import { describe, it, expect } from "vitest";
import {
  meshDescriptorOf,
  serviceFailureToProcessingFailure,
  serviceStatesToStages,
} from "./processing";
import type { ServiceResponseWire } from "./wireTypes";

function responseWith(
  states: string[],
  failure: ServiceResponseWire["failure"] = null
): ServiceResponseWire {
  return {
    contract_version: "1",
    success: failure === null,
    final_state: failure === null ? "completed" : "failed",
    states,
    failure,
    artifacts: [],
    summary: {
      input_path: "x",
      input_checksum: null,
      backend_name: null,
      backend_version: null,
      calibration_method: null,
      calibration_reference: null,
      target_semantics: null,
      mesh_requested: false,
      geotiff_path: null,
      engine_version: "0.1.0",
    },
  };
}

describe("serviceStatesToStages", () => {
  it("maps backend states to frontend stages in order", () => {
    expect(
      serviceStatesToStages([
        "input_validated",
        "preprocessing",
        "inference_running",
        "calibrating",
        "dsm_generation",
        "mesh_generation",
        "completed",
      ])
    ).toEqual([
      "loading",
      "preprocessing",
      "inference_running",
      "calibrating",
      "dsm_generation",
      "mesh_generation",
    ]);
  });

  it("drops terminal and export-only states", () => {
    expect(serviceStatesToStages(["failed"])).toEqual([]);
    expect(serviceStatesToStages(["exporting", "completed"])).toEqual([]);
  });

  it("drops unknown states without failing", () => {
    expect(serviceStatesToStages(["preprocessing", "warp_drive"])).toEqual(["preprocessing"]);
  });

  it("deduplicates repeated states", () => {
    expect(serviceStatesToStages(["preprocessing", "preprocessing"])).toEqual(["preprocessing"]);
  });
});

describe("serviceFailureToProcessingFailure", () => {
  it("preserves backend code, message, and stage", () => {
    const failure = serviceFailureToProcessingFailure(
      responseWith(["input_validated", "failed"], {
        code: "CalibrationError",
        message: "fit exploded",
        stage: "calibrating",
      }),
      true
    );
    expect(failure.code).toBe("CalibrationError");
    expect(failure.message).toBe("fit exploded");
    expect(failure.stage).toBe("calibrating");
    expect(failure.phase).toBe("process");
    expect(failure.previousAvailable).toBe(true);
  });

  it("falls back to the last completed stage for unknown stages", () => {
    const failure = serviceFailureToProcessingFailure(
      responseWith(["preprocessing", "failed"], {
        code: "X",
        message: "y",
        stage: "warp_drive",
      }),
      false
    );
    expect(failure.stage).toBe("preprocessing");
  });
});

describe("meshDescriptorOf", () => {
  it("finds the mesh descriptor", () => {
    const response = responseWith(["completed"]);
    response.artifacts = [
      {
        kind: "depth",
        available: true,
        persisted: false,
        path: null,
        semantics: "relative_depth",
        units: null,
        width: 4,
        height: 4,
        georeferenced: false,
      },
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
    ];
    expect(meshDescriptorOf(response)?.available).toBe(true);
    expect(meshDescriptorOf(response)?.semantics).toBe("absolute_elevation_dsm");
  });

  it("returns undefined without a mesh descriptor", () => {
    expect(meshDescriptorOf(responseWith([]))).toBeUndefined();
  });
});
