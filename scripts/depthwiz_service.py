#!/usr/bin/env python3
"""Stdio transport for the backend LocalService wire contract (v1).

Reads ONE JSON document from stdin, writes ONE JSON document to stdout.
Diagnostics go to stderr; stdout carries only the wire document.

Envelope in:   {"capabilities": true}
               {"request": {...ServiceRequest...}}
Envelope out:  {"capabilities": {...ServiceCapabilities...}}
               {"response": {...ServiceResponse...}}

- Requests are decoded with the real wire decoder
  (``depthwizard.service.wire.decode_request``); ``LocalService``
  executes the real ``PipelineRunner``; responses are encoded with the
  real wire encoder (``encode_response``). This script never touches
  scientific pipeline modules directly.
- Calibration comes from ``select_calibration_provider``: the request's
  ``calibration_reference_path`` (DEM GeoTIFF or GCP CSV) backs metric
  runs. Without one, metric runs fail at the calibrating stage unless
  ``DW_DEV_CALIBRATION=1`` explicitly enables the labelled synthetic dev
  calibration (test suites only; the packaged app strips it).
- The service is synchronous with no live progress: no stage lines are
  emitted. Stage history arrives post-hoc inside the response.
- Exit 0 for any valid wire exchange, even when
  ``response.success`` is false (a failed run is still a valid
  response). Non-zero exit means wire/process failure only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_script_dir = Path(__file__).resolve().parent
for _candidate in (
    _script_dir.parent / "src",
    _script_dir / "src",
    _script_dir.parent,
    _script_dir,
):
    if (_candidate / "depthwizard").is_dir() and str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

try:
    from depthwizard.calibration import select_calibration_provider
    from depthwizard.service import (
        LocalService,
        decode_request,
        encode_response,
    )
except ImportError as exc:
    print(
        json.dumps({"wire_error": f"depthwizard package not installed: {exc}"}),
        flush=True,
    )
    sys.exit(1)


#: M17 checkpoint file name (canonical candidate, never committed).
_M17_CHECKPOINT_FILE = "m17_geonrw_struct_best.pt"

#: Satellite DA-V2 checkpoint file name (never committed).
_SAT_CHECKPOINT_FILE = "depth_anything_v2_satellite.pth"
_SAT_CHECKPOINT_ENV = "DW_DAV2_SAT_CKPT"


def _m17_checkpoint_present() -> bool:
    """Whether an M17 checkpoint resolves (discovery only, no loading)."""
    import os

    override = os.environ.get("DW_M17_CKPT")
    if override:
        return Path(override).is_file()
    root = Path(__file__).resolve().parent.parent
    return (root / "checkpoints" / _M17_CHECKPOINT_FILE).is_file()


def _sat_checkpoint_present() -> bool:
    """Whether a satellite DA-V2 checkpoint resolves (discovery only, no loading)."""
    import os

    override = os.environ.get(_SAT_CHECKPOINT_ENV)
    if override:
        return Path(override).is_file()
    root = Path(__file__).resolve().parent.parent
    return (root / "checkpoints" / _SAT_CHECKPOINT_FILE).is_file()


def build_backends() -> dict[str, Any]:
    """Assemble the service backend registry.

    The deterministic synthetic backend is always present. The real
    ``depth-anything-v2-small`` backend is registered only when its
    runtime (upstream source + torch) is import-discoverable AND an
    external checkpoint resolves via the canonical
    ``depthwizard.runtime`` order (explicit ``DW_DAV2_CKPT`` → packaged
    data dir → repo-dev ``checkpoints/``). Discovery uses ``find_spec``
    (no heavy imports, no model loading). Unknown or unavailable
    backends are rejected loudly by ``LocalService`` — never silently
    replaced with synthetic.
    """
    from depthwizard.backends.synthetic import SyntheticDepthBackend
    from depthwizard.runtime.diagnostics import module_available, resolve_checkpoint

    backends: dict[str, Any] = {"synthetic-depth": SyntheticDepthBackend()}
    checkpoint, _location = resolve_checkpoint()
    if (
        module_available("depth_anything_v2")
        and module_available("torch")
        and checkpoint is not None
    ):
        from depthwizard.backends.depth_anything_v2 import DepthAnythingV2Backend

        backends["depth-anything-v2-small"] = DepthAnythingV2Backend()
    if _m17_checkpoint_present():
        from depthwizard.backends.m17 import M17DepthBackend

        backends["m17-geonrw-struct"] = M17DepthBackend()
    if _sat_checkpoint_present():
        from depthwizard.backends.satellite import SatelliteDepthBackend

        backends["depth-anything-v2-satellite"] = SatelliteDepthBackend()
    return backends


def handle_capabilities() -> dict[str, Any]:
    """Answer capability discovery without running the pipeline."""
    service = LocalService(backends=build_backends())
    return {"capabilities": service.capabilities().model_dump()}


def handle_request(payload: object) -> dict[str, Any]:
    """Decode, execute through LocalService, encode the response."""
    if not isinstance(payload, dict):
        return {"wire_error": "request envelope must be a JSON object"}
    try:
        request = decode_request(json.dumps(payload))
    except Exception as exc:
        return {"wire_error": f"invalid ServiceRequest: {exc}"}
    provider = select_calibration_provider(
        request.calibration_reference_path,
        request.target_semantics,
        request.calibration_method,
    )
    try:
        response = LocalService(backends=build_backends()).execute(request, provider)
    except Exception as exc:
        return {"wire_error": f"service execution failed: {type(exc).__name__}: {exc}"}
    return {"response": json.loads(encode_response(response))}


def main() -> int:
    """Read one wire document, write one wire document."""
    try:
        raw = sys.stdin.read()
    except Exception as exc:
        print(f"cannot read stdin: {exc}", file=sys.stderr, flush=True)
        return 2
    try:
        envelope = json.loads(raw)
    except Exception as exc:
        print(f"stdin is not valid JSON: {exc}", file=sys.stderr, flush=True)
        return 2
    if not isinstance(envelope, dict):
        print("wire envelope must be a JSON object", file=sys.stderr, flush=True)
        return 2
    if envelope.get("capabilities") is True:
        print(json.dumps(handle_capabilities()), flush=True)
        return 0
    if "request" in envelope:
        result = handle_request(envelope["request"])
        if "wire_error" in result:
            print(f"wire failure: {result['wire_error']}", file=sys.stderr, flush=True)
            return 2
        print(json.dumps(result), flush=True)
        return 0
    print("wire envelope needs 'capabilities' or 'request'", file=sys.stderr, flush=True)
    return 2


if __name__ == "__main__":
    sys.exit(main())
