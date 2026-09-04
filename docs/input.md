# Input Ingestion Workspace

How DepthWizard takes a user-selected image from file picker to
backend-validated terrain input.

## Rule

“The frontend performs lightweight input checks; authoritative parsing
and scientific validation remain in the backend.”

## Supported formats (backend-owned truth)

The UI never hardcodes format support. On mount, `InputWorkspace`
asks the real backend (`--capabilities`, sourced from
`SUPPORTED_SUFFIXES` in `depthwizard/ingestion/formats.py`):

- `.png` → PNG (Pillow)
- `.jpg` / `.jpeg` → JPEG (Pillow)
- `.tif` / `.tiff` → TIFF / GeoTIFF (rasterio, GTiff driver; CRS,
  transform, bounds, GSD and nodata preserved when present)

If capabilities cannot load, file selection stays disabled with a
retry action — the UI never guesses.

## Lifecycle (separate from processing state)

```
empty → selected → validating → validated → (Generate) → processing
                                  ↘ invalid (structured error + action)
```

- **Client checks** (`checkClientSide`): non-empty file, extension in
  the backend allow-list.   MIME type is informational only and never
  trusted alone; no maximum size is invented (the backend sets no size
  limit).
- **Backend validation** (`--inspect` → real `inspect_input`): decode,
  mislabel detection, dimension/band/dtype capture, CRS and spatial
  metadata. Structured failures carry the backend error code
  (`invalid_input`, `unsupported_format`, …) plus a user action.
- A validated file shows backend-provided metadata only: filename,
  format, dimensions, bands, dtype, georeferencing, CRS (or “Not
  available” — never invented), GSD, nodata, size, checksum.
- The built-in development fixture bypasses backend validation and is
  labeled as synthetic test data.

## File transfer boundary

Browsers expose `File` bytes, while the backend accepts filesystem
paths — so the bridge stages bytes to a uniquely-named temp file
(`stageInputBytes`: sanitized basename preserving the real suffix,
`mkdtemp` directory, structured argv, no shell). Ownership is
explicit: `InputWorkspace` holds the staged file until replace /
clear / unmount, and processing never deletes a file it is still
reading. Selection and staging controls lock while an operation runs.

## Processing integration

“Generate terrain” builds a `FileInputSource` (stable checksum-based
id) and reuses the existing M13 operation lifecycle
(`runProcessingOperation` → `ArtifactLoader` → `--terrain-file` →
`SceneArtifact` → viewer). No second state machine exists. On success
the new artifact replaces the old one and inspection / measurement /
profile state is cleared; on failure or cancellation the previous
terrain keeps rendering.

## Security

User files are untrusted: never executed, never interpolated into
shell strings, never trusted by extension or MIME alone — the backend
content-sniffs every file. Temp files live under the OS temp dir and
are removed after use. No checkpoints, datasets, or user imagery are
committed; tests use tiny generated fixtures labeled as test data.

## Future Tauri path

`ClientFile{bytes}` and `stageInputBytes` keep React free of
filesystem APIs: a Tauri build can swap in a native-dialog provider
returning real paths (skipping staging) without touching the UI or
the validation flow.
