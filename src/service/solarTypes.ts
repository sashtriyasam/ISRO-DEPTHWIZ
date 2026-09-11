export interface SolarConfig {
  sun_elevation_deg?: number;
  sun_azimuth_deg?: number;
  min_shadow_area_px?: number;
  gsd_override?: number;
}

export interface SolarConstraint {
  height_m: number;
  quality: string;
  assumptions: string[];
  method: string;
  source_input_id: string;
}

export interface SolarAnalysisResult {
  constraints: SolarConstraint[];
  count: number;
  refused_reason: string | null;
}
