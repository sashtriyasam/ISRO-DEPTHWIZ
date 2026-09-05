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
- Calibration comes from an in-process dev provider mirroring the
  sanctioned backend test collaborator
  (``tests/pipeline/support.py::SyntheticCalibrationProvider``): paired
  references fitted with the real ``ScaleOffsetCalibrator``. No DEM/GCP
  source is faked — the reference id marks it as synthetic dev data.
- The service is synchronous with no live progress: no stage lines are
  emitted. Stage history arrives post-hoc inside the response.
- Exit 0 for any valid wire exchange, even when
  ``response.success`` is false (a failed run is still a valid
  response). Non-zero exit means wire/process failure only.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from depthwizard.calibration import (
        CalibrationResult,
        CalibrationSamples,
        ScaleOffsetCalibrator,
    )
    from depthwizard.contracts.artifacts import DepthResult
    from depthwizard.contracts.semantics import ElevationSemantics
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


DEV_REFERENCE_ID = "synthetic-dev-ref"

#: Checkpoint search order for the optional real backend (never committed).
_DAV2_CANDIDATES = ("checkpoints/depth_anything_v2_vits.pth",)


def _resolve_dav2_checkpoint() -> Path | None:
    """Locate an external DA-V2 checkpoint without importing torch."""
    override = os.environ.get("DW_DAV2_CKPT")
    if override:
        candidate = Path(override)
        return candidate if candidate.is_file() else None
    root = Path(__file__).resolve().parent.parent
    for name in _DAV2_CANDIDATES:
        candidate = root / name
        if candidate.is_file():
            return candidate
    return None


def build_backends() -> dict[str, Any]:
    """Assemble the service backend registry.

    The deterministic synthetic backend is always present. The real
    ``depth-anything-v2-small`` backend is registered only when its
    runtime (upstream source + torch) is import-discoverable AND an
    external checkpoint file exists. Discovery uses ``find_spec``
    (no heavy imports, no model loading). Unknown or unavailable
    backends are rejected loudly by ``LocalService`` — never silently
    replaced with synthetic.
    """
    from depthwizard.backends.synthetic import SyntheticDepthBackend

    backends: dict[str, Any] = {"synthetic-depth": SyntheticDepthBackend()}
    if (
        importlib.util.find_spec("depth_anything_v2") is not None
        and importlib.util.find_spec("torch") is not None
        and _resolve_dav2_checkpoint() is not None
    ):
        from depthwizard.backends.depth_anything_v2 import DepthAnythingV2Backend

        backends["depth-anything-v2-small"] = DepthAnythingV2Backend()
    return backends


class DevCalibrationProvider:
    """Deterministic dev calibration provider (test infrastructure).

    Mirrors the sanctioned backend test collaborator
    ``tests/pipeline/support.py::SyntheticCalibrationProvider``:
    reference = 2.5 * predicted + 10 fitted with the real OLS
    calibrator. Never production data; the reference id says so.
    """

    def __init__(self, target: ElevationSemantics) -> None:
        """Bind the metric target semantics for this run."""
        self._target = target

    @property
    def name(self) -> str:
        """Stable provider name for run metadata."""
        return "synthetic-dev-provider"

    def calibrate(self, depth_result: DepthResult) -> CalibrationResult:
        """Fit paired references against the actual depth values."""
        predicted = depth_result.depth_values
        reference = tuple(2.5 * value + 10.0 for value in predicted)
        samples = CalibrationSamples(
            predicted_values=predicted,
            reference_values=reference,
            reference_id=DEV_REFERENCE_ID,
            reference_units="meters",
            target_semantics=self._target,
            source_checksum=depth_result.provenance.input_checksum,
        )
        return ScaleOffsetCalibrator().calibrate(samples)


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
    provider = DevCalibrationProvider(request.target_semantics)
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
