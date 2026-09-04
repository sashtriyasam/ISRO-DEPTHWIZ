"""Canonical JSON wire encoding for the local service contract.

Single place defining how requests/responses cross future transports
(subprocess JSON, stdio, localhost HTTP, Tauri IPC): UTF-8 JSON text
with the shapes in ``models.py``. No pickle, no NumPy, no callables.
"""

from __future__ import annotations

from depthwizard.service.models import ServiceRequest, ServiceResponse


def encode_request(request: ServiceRequest) -> str:
    """Serialize a request to canonical JSON text."""
    return request.model_dump_json()


def decode_request(data: str) -> ServiceRequest:
    """Parse canonical JSON text into a request (validates)."""
    return ServiceRequest.model_validate_json(data)


def encode_response(response: ServiceResponse) -> str:
    """Serialize a response to canonical JSON text."""
    return response.model_dump_json()


def decode_response(data: str) -> ServiceResponse:
    """Parse canonical JSON text into a response (validates)."""
    return ServiceResponse.model_validate_json(data)
