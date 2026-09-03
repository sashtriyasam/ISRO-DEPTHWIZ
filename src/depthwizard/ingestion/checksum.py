"""Deterministic SHA-256 checksums, streamed in chunks."""

from __future__ import annotations

import hashlib
from pathlib import Path

from depthwizard.errors import InvalidInputError

_CHUNK_SIZE = 65536


def sha256_file(path: Path, chunk_size: int = _CHUNK_SIZE) -> str:
    """Return the hex SHA-256 digest of a file without loading it fully.

    Raises :class:`InvalidInputError` when the file cannot be read.
    """
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as handle:
            while True:
                chunk = handle.read(chunk_size)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError as exc:
        raise InvalidInputError(f"unreadable input file: {path.name}: {exc}") from exc
    return digest.hexdigest()
