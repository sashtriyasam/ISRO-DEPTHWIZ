import type { LayerId, LayerDefinition, LayerState } from "./types";
import type { SceneArtifact } from "../types/scene";
import { ALL_LAYER_IDS, LAYER_LABELS, LAYER_DESCRIPTIONS, getSemanticLayerLabel, getSemanticLayerDescription } from "./types";

function isLayerAvailable(artifact: SceneArtifact, layerId: LayerId): boolean {
  switch (layerId) {
    case "dsm":
      return artifact.elevation != null;
    case "rdsm":
      return artifact.layers?.rdsm != null;
    case "agl":
      return artifact.layers?.agl != null;
    case "rgb":
      return artifact.texture != null;
    case "wireframe":
      return true;
    case "slope":
    case "contours":
    case "reference":
      return false;
    default:
      return false;
  }
}

export function createLayerState(artifact: SceneArtifact): LayerState {
  const backendSemantics = artifact.metadata.backend?.elevation_semantics;
  const semanticLabel = getSemanticLayerLabel(backendSemantics);
  const semanticDescription = getSemanticLayerDescription(backendSemantics);

  const layers: LayerDefinition[] = ALL_LAYER_IDS.map((id) => {
    const isDsm = id === "dsm" && artifact.elevation != null;
    return {
      id,
      label: isDsm ? semanticLabel : LAYER_LABELS[id],
      description: isDsm ? semanticDescription : LAYER_DESCRIPTIONS[id],
      visualizationType:
        id === "wireframe" ? "line-overlay"
        : id === "rgb" ? "texture"
        : id === "slope" || id === "contours" || id === "reference" ? "line-overlay"
        : "mesh-displacement",
      available: isLayerAvailable(artifact, id),
      enabled: false,
    };
  });

  const firstAvailable = layers.find((l) => l.available);
  if (firstAvailable) {
    firstAvailable.enabled = true;
  }

  return {
    activeLayerId: firstAvailable?.id ?? "dsm",
    layers,
  };
}

export function getActiveLayer(state: LayerState): LayerDefinition | undefined {
  return state.layers.find((l) => l.id === state.activeLayerId);
}

export function setActiveLayer(state: LayerState, layerId: LayerId): LayerState {
  const target = state.layers.find((l) => l.id === layerId);
  if (!target || !target.available) return state;

  return {
    ...state,
    activeLayerId: layerId,
    layers: state.layers.map((l) => ({
      ...l,
      enabled: l.id === layerId,
    })),
  };
}
