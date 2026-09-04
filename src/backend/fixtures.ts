import type { BackendDepthResult, BackendCalibrationResult } from "./types";

export const BACKEND_TEST_FIXTURE: BackendDepthResult = {
  model_name: "synthetic-depth",
  model_version: "0.1.0",
  checkpoint_id: null,

  input_resolution: { width: 4, height: 4 },
  output_resolution: { width: 4, height: 4 },

  depth_scale: "relative",
  elevation_semantics: "relative_depth",
  georeferencing: "non_georeferenced",

  depth_values: [
    0.5, 0.5, 0.5, 0.5,
    0.5, 0.5, 0.5, 0.5,
    0.5, 0.5, 0.5, 0.5,
    0.5, 0.5, 0.5, 0.5,
  ],

  preprocessing: { synthetic_pattern: "separable-sinusoid-normalized" },
  units: null,

  spatial: {
    kind: "not_applicable",
  },

  provenance: {
    source_input_id: "test-input.png",
    input_checksum: "a".repeat(64),
    model_name: "synthetic-depth",
    model_version: "0.1.0",
    checkpoint_id: null,
    calibration_method: null,
    calibration_reference: null,
    calibration_params: null,
    software_version: "0.1.0",
    code_commit: null,
    generated_at: null,
    units: null,
    semantic_meaning: "relative_depth from synthetic development backend",
  },
};

export const BACKEND_CALIBRATION_FIXTURE: BackendCalibrationResult = {
  method: "scale_offset",
  scale: 100.0,
  offset: 0.0,
  reference_id: "test-dem",
  reference_checksum: null,
  reference_units: "meters",
  target_semantics: "absolute_elevation_dsm",
  total_samples: 16,
  valid_samples: 16,
  rmse: 0.0,
  mae: 0.0,
  max_abs_residual: 0.0,
  r_squared: 1.0,
  engine_version: "0.1.0",
  source_input_id: "test-input.png",
  source_checksum: null,
};

export const BACKEND_METRIC_FIXTURE: BackendDepthResult = {
  ...BACKEND_TEST_FIXTURE,
  depth_scale: "metric",
  elevation_semantics: "absolute_elevation_dsm",
  units: "meters",
  spatial: {
    kind: "present",
    details: {
      crs: "EPSG:4326",
      transform: { a: 0.0, b: 1.0, c: 0.0, d: 0.0, e: 0.0, f: 1.0 },
      bounds: { min_x: 0.0, min_y: 0.0, max_x: 3.0, max_y: 3.0 },
      pixel_width: 1,
      pixel_height: 1,
      units: "meters",
      raster_width: 4,
      raster_height: 4,
    },
  },
};
