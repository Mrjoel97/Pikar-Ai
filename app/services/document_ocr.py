# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Gemini Vision OCR fallback for document ingestion."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".tif"}
)

_IMAGE_MIME_BY_EXTENSION: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".webp": "image/webp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
}

_OCR_PROMPT = (
    "Extract all readable text from this document for a knowledge base. "
    "Preserve headings, lists, tables, and page order where possible. "
    "Return Markdown only. If there is no readable text, return an empty response."
)


class DocumentOcrError(Exception):
    """Raised when Gemini Vision OCR cannot run."""


def _normalise_mime(mime_type: str | None) -> str:
    if not mime_type:
        return ""
    return mime_type.lower().split(";")[0].strip()


def _normalise_extension(filename: str | None) -> str:
    if not filename:
        return ""
    return os.path.splitext(filename)[1].lower()


def resolve_ocr_mime_type(mime_type: str | None, filename: str | None) -> str:
    """Return the MIME type Gemini should receive for OCR."""
    normalised = _normalise_mime(mime_type)
    if normalised == "application/pdf" or normalised.startswith("image/"):
        return normalised

    extension = _normalise_extension(filename)
    if extension == ".pdf":
        return "application/pdf"
    if extension in _IMAGE_MIME_BY_EXTENSION:
        return _IMAGE_MIME_BY_EXTENSION[extension]

    return normalised or "application/octet-stream"


def is_ocr_candidate(mime_type: str | None, filename: str | None = None) -> bool:
    """Return True when Gemini Vision can attempt OCR for the upload."""
    normalised = _normalise_mime(mime_type)
    extension = _normalise_extension(filename)
    return (
        normalised == "application/pdf"
        or normalised.startswith("image/")
        or extension == ".pdf"
        or extension in _IMAGE_EXTENSIONS
    )


def extract_text_with_gemini_vision(
    file_bytes: bytes,
    mime_type: str | None,
    *,
    filename: str | None = None,
) -> str:
    """Extract OCR text from PDF/image bytes using Gemini Vision."""
    try:
        from google.genai import types

        from app.agents.shared import GEMINI_AGENT_MODEL_FALLBACK, get_model
    except Exception as exc:  # pragma: no cover - dependency guard
        raise DocumentOcrError(f"Gemini Vision OCR unavailable: {exc}") from exc

    ocr_mime_type = resolve_ocr_mime_type(mime_type, filename)
    if ocr_mime_type == "application/octet-stream":
        raise DocumentOcrError("Gemini Vision OCR needs a PDF or image MIME type")

    try:
        model = get_model(GEMINI_AGENT_MODEL_FALLBACK)
        response = model.api_client.models.generate_content(
            model=model.model,
            contents=[
                types.Part.from_bytes(data=file_bytes, mime_type=ocr_mime_type),
                _OCR_PROMPT,
            ],
            config=types.GenerateContentConfig(temperature=0.0),
        )
    except Exception as exc:
        logger.warning(
            "Gemini Vision OCR failed for %s (mime=%s): %s",
            filename or "<unnamed>",
            ocr_mime_type,
            exc,
        )
        raise DocumentOcrError(str(exc)) from exc

    return (response.text or "").strip()
