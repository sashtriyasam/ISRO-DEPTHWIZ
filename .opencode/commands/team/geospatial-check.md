# /team:geospatial-check

Gate any geospatial claim. Respect `AGENTS.md`. Owner: Shivam's track,
but anyone crossing into geospatial code runs this.

1. CRS: is it preserved from source, never invented? Path A output
   must carry no CRS.
2. Transform: affine preserved end-to-end (input → DSM → mesh →
   export)? Bounds/GSD consistent?
3. Nodata/validity: semantics correct and tested? Overlap/alignment/
   reprojection validated where used?
4. Export: does the GeoTIFF open in standard GIS with correct
   placement? Provenance attached?
5. Report file:line findings. Metric output without calibration
   evidence fails this check automatically.
