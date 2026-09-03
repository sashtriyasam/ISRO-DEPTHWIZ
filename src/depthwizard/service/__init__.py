"""Thin local service boundary over PipelineRunner (no science here).

Transport-neutral, JSON-safe, versioned request/response contract for
desktop and future local clients. Synchronous; no sockets, no auth,
no database, no job store.
"""

from depthwizard.pipeline import CancellationToken
from depthwizard.service.models import (
    SERVICE_CONTRACT_VERSION,
    ArtifactDescriptor,
    ArtifactKind,
    RunSummary,
    ServiceCapabilities,
    ServiceError,
    ServiceRequest,
    ServiceResponse,
)
from depthwizard.service.service import LocalService, build_descriptors, build_response
from depthwizard.service.wire import (
    decode_request,
    decode_response,
    encode_request,
    encode_response,
)

__all__ = [
    "SERVICE_CONTRACT_VERSION",
    "ArtifactDescriptor",
    "ArtifactKind",
    "CancellationToken",
    "LocalService",
    "RunSummary",
    "ServiceCapabilities",
    "ServiceError",
    "ServiceRequest",
    "ServiceResponse",
    "build_descriptors",
    "build_response",
    "decode_request",
    "decode_response",
    "encode_request",
    "encode_response",
]
