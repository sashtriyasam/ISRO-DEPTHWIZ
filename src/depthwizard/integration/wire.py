"""Canonical JSON wire helpers for desktop transport payloads.

Single place defining JSON-safe serialization of transport models:
UTF-8 text, strict finite numbers (no NaN/Infinity tokens), and a
recursive safety scanner clients can trust before parsing.
"""

from __future__ import annotations

import json
import math
from typing import Any

from pydantic import BaseModel

from depthwizard.integration.transport import TransportTerrainProduct


def to_json_text(model: BaseModel) -> str:
    """Serialize a transport model to canonical JSON text.

    Rejects non-finite floats instead of emitting invalid JSON tokens.
    """
    data = model.model_dump(mode="json")
    _assert_json_safe(data)
    return json.dumps(data)


def terrain_product_from_json(text: str) -> TransportTerrainProduct:
    """Parse and validate terrain-product JSON text."""
    return TransportTerrainProduct.model_validate_json(text)


def is_json_safe(value: Any) -> bool:
    """Recursively check JSON-safe values (null/bool/number/string/arrays/objects).

    Numbers use exact-type checks: NumPy scalars subclass Python
    numeric types but are unsafe (they serialize unpredictably), so
    only genuine ``int``/``float`` pass. Non-finite floats fail. Dict
    keys must be strings; tuples count as arrays (Python json
    serializes them so). Pydantic models, datetimes and Paths are
    unsafe — convert first.
    """
    if value is None or type(value) is bool or type(value) is str:
        return True
    if type(value) is int:
        return True
    if type(value) is float:
        return math.isfinite(value)
    if isinstance(value, (list, tuple)):
        return all(is_json_safe(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and is_json_safe(item) for key, item in value.items())
    return False


def _assert_json_safe(value: Any) -> None:
    """Raise on non-JSON-safe payloads (with location context)."""
    if is_json_safe(value):
        return
    raise ValueError("transport payload is not JSON-safe (non-finite or exotic value)")


__all__ = ["is_json_safe", "terrain_product_from_json", "to_json_text"]
