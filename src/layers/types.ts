export type LayerId =
  | "rgb"
  | "dsm"
  | "rdsm"
  | "agl"
  | "slope"
  | "contours"
  | "reference"
  | "wireframe";

export type LayerVisualizationType = "mesh-color" | "mesh-displacement" | "texture" | "line-overlay";

export interface LayerDefinition {
  id: LayerId;
  label: string;
  description: string;
  visualizationType: LayerVisualizationType;
  available: boolean;
  enabled: boolean;
}

export interface LayerState {
  activeLayerId: LayerId;
  layers: LayerDefinition[];
}

export const ALL_LAYER_IDS: LayerId[] = [
  "rgb", "dsm", "rdsm", "agl", "slope", "contours", "reference", "wireframe",
];

export const LAYER_LABELS: Record<LayerId, string> = {
  rgb: "RGB",
  dsm: "DSM",
  rdsm: "rDSM",
  agl: "AGL",
  slope: "Slope",
  contours: "Contours",
  reference: "Reference",
  wireframe: "Wireframe",
};

export const LAYER_DESCRIPTIONS: Record<LayerId, string> = {
  rgb: "Surface color display",
  dsm: "Digital Surface Model — elevation height map",
  rdsm: "Relative Digital Surface Model — height above local terrain",
  agl: "Above Ground Level — height above ground surface",
  slope: "Terrain slope visualization",
  contours: "Elevation contour lines",
  reference: "Reference elevation overlay",
  wireframe: "Mesh wireframe overlay",
};
