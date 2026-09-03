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

export function getSemanticLayerLabel(elevationSemantics: string | undefined): string {
  switch (elevationSemantics) {
    case "relative_depth":
      return "Relative Depth";
    case "relative_surface_rdsm":
      return "Relative Surface (rDSM)";
    case "height_agl_ndsm":
      return "Height Above Ground (AGL)";
    case "absolute_elevation_dsm":
      return "DSM";
    default:
      return "Depth";
  }
}

export function getSemanticLayerDescription(elevationSemantics: string | undefined): string {
  switch (elevationSemantics) {
    case "relative_depth":
      return "Scale-ambiguous relative depth values (not metric elevation)";
    case "relative_surface_rdsm":
      return "Relative height above local terrain surface";
    case "height_agl_ndsm":
      return "Height above ground level (nDSM)";
    case "absolute_elevation_dsm":
      return "Digital Surface Model — absolute elevation in metres";
    default:
      return "Depth visualization";
  }
}
