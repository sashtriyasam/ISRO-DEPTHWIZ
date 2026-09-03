export type DepthScale = "relative" | "metric";

export type ElevationSemantics =
  | "relative_depth"
  | "relative_surface_rdsm"
  | "height_agl_ndsm"
  | "absolute_elevation_dsm";

export type GeoreferencingLevel =
  | "non_georeferenced"
  | "georeferenced_no_elevation_reference"
  | "georeferenced_with_dem"
  | "georeferenced_with_gcp";

export interface BackendAffineTransform {
  a: number;
  b: number;
  c: number;
  d: number;
  e: number;
  f: number;
}

export interface BackendBounds {
  min_x: number;
  min_y: number;
  max_x: number;
  max_y: number;
}

export interface BackendSpatialDetails {
  crs?: string | null;
  transform?: BackendAffineTransform | null;
  bounds?: BackendBounds | null;
  pixel_width?: number | null;
  pixel_height?: number | null;
  resolution_gsd?: number | null;
  nodata?: number | null;
  units?: string | null;
  raster_width?: number | null;
  raster_height?: number | null;
  source?: string | null;
}

export interface BackendSpatialContext {
  kind: "present" | "unavailable" | "not_applicable";
  details?: BackendSpatialDetails | null;
}

export interface BackendImageResolution {
  width: number;
  height: number;
}

export interface BackendProductProvenance {
  source_input_id?: string | null;
  input_checksum?: string | null;
  model_name?: string | null;
  model_version?: string | null;
  checkpoint_id?: string | null;
  calibration_method?: string | null;
  calibration_reference?: string | null;
  calibration_params?: number[] | null;
  software_version?: string | null;
  code_commit?: string | null;
  generated_at?: string | null;
  units?: string | null;
  semantic_meaning?: string | null;
}

export interface BackendDepthResult {
  model_name: string;
  model_version?: string | null;
  checkpoint_id?: string | null;

  input_resolution: BackendImageResolution;
  output_resolution: BackendImageResolution;

  depth_scale: DepthScale;
  elevation_semantics: ElevationSemantics;
  georeferencing: GeoreferencingLevel;

  depth_values: number[];
  confidence_values?: number[] | null;
  valid_mask?: boolean[] | null;

  preprocessing?: Record<string, string>;
  units?: string | null;

  spatial: BackendSpatialContext;
  provenance?: BackendProductProvenance;
}

export interface BackendCalibrationResult {
  method: "scale_offset";
  scale: number;
  offset: number;
  reference_id: string;
  reference_checksum?: string | null;
  reference_units: string;
  target_semantics: ElevationSemantics;
  total_samples: number;
  valid_samples: number;
  rmse: number;
  mae: number;
  max_abs_residual: number;
  r_squared: number;
  engine_version: string;
  source_input_id?: string | null;
  source_checksum?: string | null;
}
