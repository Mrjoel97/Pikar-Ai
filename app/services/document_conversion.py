# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Byte-scoped document conversion for ingestion.

This module is the narrow adapter around MarkItDown. It intentionally accepts
bytes and stream metadata only; callers should not pass user-controlled paths or
URLs into MarkItDown from hosted upload flows.
"""

from __future__ import annotations

import io
import logging
import os
import threading
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_MARKITDOWN_LOCK = threading.Lock()
_MARKITDOWN_INSTANCE = None


@dataclass(frozen=True)
class DocumentConversionResult:
    """Markdown output produced from uploaded document bytes."""

    markdown: str
    converter: str = "markitdown"
    content_format: str = "markdown"


class DocumentConversionError(Exception):
    """Raised when MarkItDown cannot convert a supported document."""


def _normalise_mime(mime_type: str | None) -> str | None:
    if not mime_type:
        return None
    value = mime_type.lower().split(";")[0].strip()
    return value or None


def _normalise_extension(filename: str | None) -> str | None:
    if not filename:
        return None
    extension = os.path.splitext(filename)[1].lower()
    return extension or None


def _get_markitdown():
    """Return a cached MarkItDown instance with plugins disabled."""
    global _MARKITDOWN_INSTANCE

    if _MARKITDOWN_INSTANCE is not None:
        return _MARKITDOWN_INSTANCE

    with _MARKITDOWN_LOCK:
        if _MARKITDOWN_INSTANCE is not None:
            return _MARKITDOWN_INSTANCE

        try:
            from markitdown import MarkItDown
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise DocumentConversionError(
                "MarkItDown conversion unavailable: markitdown is not installed"
            ) from exc

        _MARKITDOWN_INSTANCE = MarkItDown(enable_plugins=False)
        return _MARKITDOWN_INSTANCE


def convert_document_to_markdown(
    file_bytes: bytes,
    mime_type: str | None,
    *,
    filename: str | None = None,
) -> DocumentConversionResult:
    """Convert uploaded document bytes to Markdown via MarkItDown.

    The conversion uses ``convert_stream`` with explicit ``StreamInfo`` so the
    converter only sees the uploaded bytes and cannot dereference paths or URLs.
    """
    try:
        from markitdown import StreamInfo
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise DocumentConversionError(
            "MarkItDown conversion unavailable: markitdown is not installed"
        ) from exc

    stream_info = StreamInfo(
        mimetype=_normalise_mime(mime_type),
        extension=_normalise_extension(filename),
        filename=filename,
    )

    try:
        result = _get_markitdown().convert_stream(
            io.BytesIO(file_bytes),
            stream_info=stream_info,
        )
    except Exception as exc:
        logger.warning(
            "MarkItDown conversion failed for %s (mime=%s): %s",
            filename or "<unnamed>",
            mime_type or "<unknown>",
            exc,
        )
        raise DocumentConversionError(str(exc)) from exc

    return DocumentConversionResult(markdown=result.markdown)
