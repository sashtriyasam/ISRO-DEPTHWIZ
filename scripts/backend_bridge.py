#!/usr/bin/env python3
"""Backend execution bridge: TypeScript → Python → DepthResult → JSON.

This script executes the actual SyntheticDepthBackend from the depthwizard
package and outputs the serialized DepthResult as JSON to stdout.

Architecture:
  TypeScript (bridge.ts)
    → spawns this Python script
    → this script runs DepthBackend.estimate_depth()
    → outputs JSON to stdout
    → TypeScript parses, validates, adapts

Usage:
  python scripts/backend_bridge.py <input_image_path>
  python scripts/backend_bridge.py --synthetic <width> <height>

The --synthetic flag generates a synthetic input without requiring a real file,
useful for end-to-end testing.
"""

from __future__ import annotations

import json
import sys
import math
import hashlib
import struct
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Self-contained backend implementation
# This mirrors the actual depthwizard backend exactly.
# When depthwizard is installed, we prefer the real package.
# ---------------------------------------------------------------------------

USE_REAL_BACKEND = False

try:
    from depthwizard.contracts.artifacts import DepthResult, ImageResolution
    from depthwizard.contracts.spatial import SpatialContext, SpatialKind
    from depthwizard.contracts.semantics import (
        DepthScale,
        ElevationSemantics,
        GeoreferencingLevel,
    )
    from depthwizard.contracts.provenance import ProductProvenance
    from depthwizard.ingestion.models import InputInspection, InputHandle
    from depthwizard.ingestion.api import inspect_input as real_inspect_input
    from depthwizard.backends.synthetic import SyntheticDepthBackend
    USE_REAL_BACKEND = True
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Self-contained fallback (identical logic to depthwizard backend)
# ---------------------------------------------------------------------------

def synthetic_depth_values(width: int, height: int) -> tuple:
    """Deterministic relative-depth pattern in [0, 1], row-major.
    
    v(col, row) = 0.5 * (1 + sin(2*pi*col/width) * cos(2*pi*row/height)).
    This is the EXACT SAME formula as depthwizard.backends.synthetic.
    """
    two_pi = 2.0 * math.pi
    values = []
    for row in range(height):
        cos_row = math.cos(two_pi * row / height)
        for col in range(width):
            values.append(0.5 * (1.0 + math.sin(two_pi * col / width) * cos_row))
    return tuple(values)


def create_synthetic_result(width: int, height: int, display_name: str = "synthetic-input") -> dict:
    """Create a DepthResult-compatible dict using the synthetic backend formula.
    
    This mirrors the exact output of SyntheticDepthBackend.estimate_depth().
    """
    depth_values = synthetic_depth_values(width, height)
    
    return {
        "model_name": "synthetic-depth",
        "model_version": "0.1.0",
        "checkpoint_id": None,
        "input_resolution": {"width": width, "height": height},
        "output_resolution": {"width": width, "height": height},
        "depth_scale": "relative",
        "elevation_semantics": "relative_depth",
        "georeferencing": "non_georeferenced",
        "depth_values": list(depth_values),
        "confidence_values": None,
        "valid_mask": None,
        "preprocessing": {"synthetic_pattern": "separable-sinusoid-normalized"},
        "units": None,
        "spatial": {"kind": "not_applicable", "details": None},
        "provenance": {
            "source_input_id": display_name,
            "input_checksum": None,
            "model_name": "synthetic-depth",
            "model_version": "0.1.0",
            "checkpoint_id": None,
            "calibration_method": None,
            "calibration_reference": None,
            "calibration_params": None,
            "software_version": "0.1.0",
            "code_commit": None,
            "generated_at": None,
            "units": None,
            "semantic_meaning": "relative_depth from synthetic development backend (not scientific inference)",
        },
    }


def create_synthetic_png(width: int, height: int, path: Path) -> Path:
    """Create a deterministic synthetic PNG for testing."""
    try:
        from PIL import Image
        img = Image.new("RGB", (width, height))
        pixels = img.load()
        for row in range(height):
            for col in range(width):
                v = 255 if (row + col) % 2 == 0 else 0
                pixels[col, row] = (v, (col * 32) % 256, (row * 40) % 256)
        img.save(path, format="PNG")
        return path
    except ImportError:
        # Fallback: create minimal valid PNG without Pillow
        return create_minimal_png(width, height, path)


def create_minimal_png(width: int, height: int, path: Path) -> Path:
    """Create a minimal valid PNG file without Pillow (raw bytes)."""
    import zlib
    
    def create_png_chunk(chunk_type: bytes, data: bytes) -> bytes:
        chunk = chunk_type + data
        crc = zlib.crc32(chunk) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk + struct.pack(">I", crc)
    
    # PNG signature
    signature = b'\x89PNG\r\n\x1a\n'
    
    # IHDR chunk
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr = create_png_chunk(b'IHDR', ihdr_data)
    
    # IDAT chunk (raw image data)
    raw_data = b''
    for row in range(height):
        raw_data += b'\x00'  # filter byte
        for col in range(width):
            v = 255 if (row + col) % 2 == 0 else 0
            raw_data += bytes([v, (col * 32) % 256, (row * 40) % 256])
    
    compressed = zlib.compress(raw_data)
    idat = create_png_chunk(b'IDAT', compressed)
    
    # IEND chunk
    iend = create_png_chunk(b'IEND', b'')
    
    with open(path, 'wb') as f:
        f.write(signature + ihdr + idat + iend)
    
    return path


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def inspect_image(path: Path) -> dict:
    """Inspect an image file and return inspection metadata."""
    try:
        from PIL import Image
        with Image.open(path) as img:
            width, height = img.size
            mode = img.mode
    except ImportError:
        # Minimal PNG parsing without Pillow
        width, height, mode = parse_png_dimensions(path)
    
    file_size = path.stat().st_size
    checksum = sha256_file(path)
    
    return {
        "handle": {
            "source_path": str(path),
            "display_name": path.name,
            "file_size": file_size,
            "sha256": checksum,
        },
        "detected_format": "png",
        "width": width,
        "height": height,
        "band_count": 3 if mode == "RGB" else 1,
        "dtype": "uint8",
        "georeferencing": "non_georeferenced",
        "spatial": {"kind": "not_applicable", "details": None},
        "source_format_metadata": {},
        "status": "valid",
    }


def parse_png_dimensions(path: Path) -> tuple:
    """Parse PNG dimensions from file header."""
    with open(path, 'rb') as f:
        header = f.read(24)
        if header[:8] != b'\x89PNG\r\n\x1a\n':
            raise ValueError("Not a valid PNG file")
        width = struct.unpack(">I", header[16:20])[0]
        height = struct.unpack(">I", header[20:24])[0]
    return width, height, "RGB"


def run_backend(inspection: dict) -> dict:
    """Run the backend and return the result."""
    if USE_REAL_BACKEND:
        # Use the actual depthwizard backend
        real_inspection = InputInspection(
            handle=InputHandle(**inspection["handle"]),
            detected_format=inspection["detected_format"],
            width=inspection["width"],
            height=inspection["height"],
            band_count=inspection.get("band_count"),
            dtype=inspection.get("dtype"),
            georeferencing=GeoreferencingLevel(inspection["georeferencing"]),
            spatial=SpatialContext(**inspection["spatial"]),
            source_format_metadata=inspection.get("source_format_metadata", {}),
        )
        backend = SyntheticDepthBackend()
        result = backend.estimate_depth(real_inspection)
        return result.model_dump()
    else:
        # Use self-contained fallback (identical formula)
        return create_synthetic_result(
            width=inspection["width"],
            height=inspection["height"],
            display_name=inspection["handle"]["display_name"],
        )


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: backend_bridge.py <input_path> or --synthetic <width> <height>"}))
        sys.exit(1)
    
    try:
        if sys.argv[1] == "--synthetic":
            # Generate synthetic input
            width = int(sys.argv[2]) if len(sys.argv) > 2 else 8
            height = int(sys.argv[3]) if len(sys.argv) > 3 else 8
            
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            
            create_synthetic_png(width, height, tmp_path)
            inspection = inspect_image(tmp_path)
            result = run_backend(inspection)
            
            # Clean up temp file
            tmp_path.unlink(missing_ok=True)
            
            print(json.dumps(result))
        else:
            # Use provided input file
            input_path = Path(sys.argv[1])
            if not input_path.exists():
                print(json.dumps({"error": f"Input file not found: {input_path}"}))
                sys.exit(1)
            
            inspection = inspect_image(input_path)
            result = run_backend(inspection)
            print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"error": str(e), "type": type(e).__name__}))
        sys.exit(1)


if __name__ == "__main__":
    main()
