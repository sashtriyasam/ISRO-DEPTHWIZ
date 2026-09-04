import type { SpatialDetails, BackendOrigin } from "../types/scene";
import type { BackendSpatialDetails, BackendProductProvenance } from "./types";

export function mapSpatialDetails(
  details: BackendSpatialDetails | undefined | null
): SpatialDetails | undefined {
  if (!details) {
    return undefined;
  }
  const mapped: SpatialDetails = {};
  if (details.resolution_gsd !== undefined && details.resolution_gsd !== null) {
    mapped.gsd = details.resolution_gsd;
  }
  if (details.nodata !== undefined) {
    mapped.nodata = details.nodata;
  }
  if (details.raster_width !== undefined && details.raster_width !== null) {
    mapped.rasterWidth = details.raster_width;
  }
  if (details.raster_height !== undefined && details.raster_height !== null) {
    mapped.rasterHeight = details.raster_height;
  }
  if (details.units !== undefined && details.units !== null) {
    mapped.spatialUnits = details.units;
  }
  if (details.source !== undefined && details.source !== null) {
    mapped.source = details.source;
  }
  if (details.transform) {
    const t = details.transform;
    mapped.affine = [t.a, t.b, t.c, t.d, t.e, t.f];
  }
  if (details.bounds) {
    const b = details.bounds;
    mapped.spatialBounds = { minX: b.min_x, minY: b.min_y, maxX: b.max_x, maxY: b.max_y };
  }
  return Object.keys(mapped).length > 0 ? mapped : undefined;
}

export function applyProvenance(
  backend: BackendOrigin,
  provenance: BackendProductProvenance | undefined | null
): void {
  if (!provenance) {
    return;
  }
  if (provenance.source_input_id !== undefined && provenance.source_input_id !== null) {
    backend.input_id = provenance.source_input_id;
  }
  if (provenance.input_checksum !== undefined && provenance.input_checksum !== null) {
    backend.input_checksum = provenance.input_checksum;
  }
  if (provenance.software_version !== undefined && provenance.software_version !== null) {
    backend.software_version = provenance.software_version;
  }
  if (provenance.semantic_meaning !== undefined && provenance.semantic_meaning !== null) {
    backend.semantic_meaning = provenance.semantic_meaning;
  }
}
