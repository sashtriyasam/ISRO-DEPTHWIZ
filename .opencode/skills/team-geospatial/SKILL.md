# Team Geospatial (DepthWizard)

- Preserve CRS, affine transform, bounds/GSD, spatial metadata, and
  provenance from input to export.
- Path A frames are LOCAL with units absent; inventing CRS/metres is a
  defect, not a shortcut.
- Validate: CRS round-trips, transform preservation, overlap/alignment,
  reprojection correctness, nodata/validity semantics, GeoTIFF that
  opens correctly placed in standard GIS.
- Metric rasters exist only downstream of calibration; source linkage
  is checksum-enforced.
