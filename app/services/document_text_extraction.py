# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Shared MIME-aware document text extraction for vault ingestion.

The public API in this module is intentionally stable. Internally, supported
documents are converted to Markdown through ``document_conversion`` so RAG
ingestion preserves useful structure such as headings, tables, and slide
boundaries.
"""

from __future__ import annotations

import io
import logging
import os
import zipfile

from app.services.document_conversion import (
    DocumentConversionError,
    convert_document_to_markdown,
)
from app.services.document_ocr import (
    DocumentOcrError,
    extract_text_with_gemini_vision,
    is_ocr_candidate,
)

_PDF_MIME = "application/pdf"
_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_XLS_MIME = "application/vnd.ms-excel"
_PPTX_MIME_PREFIX = "application/vnd.openxmlformats-officedocument.presentationml"
_DOC_LEGACY_MIME = "application/msword"

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Raised when a supported format cannot be parsed."""


_TEXT_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".txt",
        ".md",
        ".markdown",
        ".csv",
        ".tsv",
        ".json",
        ".py",
        ".js",
        ".ts",
        ".html",
        ".htm",
        ".css",
        ".sql",
        ".xml",
        ".yaml",
        ".yml",
    }
)

_DOCUMENT_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".pdf",
        ".docx",
        ".xlsx",
        ".xls",
        ".pptx",
    }
)

_SEARCHABLE_MIMES: frozenset[str] = frozenset(
    {
        "application/csv",
        "application/json",
        "application/markdown",
        "application/pdf",
        "application/xml",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/csv",
        "text/html",
        "text/markdown",
        "text/md",
        "text/plain",
        "text/tsv",
        "text/x-markdown",
        "text/xml",
    }
)


def _normalise_mime(mime_type: str | None) -> str:
    """Strip charset / boundary suffixes and lowercase the MIME string."""
    if not mime_type:
        return ""
    return mime_type.lower().split(";")[0].strip()


def _normalise_extension(filename: str | None) -> str:
    """Return the lowercase suffix for *filename* or ``""`` when absent."""
    if not filename:
        return ""
    return os.path.splitext(filename)[1].lower()


def _detect_ooxml_family(file_bytes: bytes) -> str | None:
    """Return the OOXML family when bytes look like an Office archive."""
    if not file_bytes.startswith(b"PK"):
        return None

    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as archive:
            names = archive.namelist()
    except zipfile.BadZipFile:
        return None

    if any(name.startswith("word/") for name in names):
        return "docx"
    if any(name.startswith("xl/") for name in names):
        return "xlsx"
    if any(name.startswith("ppt/") for name in names):
        return "pptx"
    return None


def _resolve_extraction_target(
    file_bytes: bytes,
    mime_type: str | None,
    filename: str | None,
) -> str | None:
    """Resolve the best converter target for uploaded content."""
    normalised = _normalise_mime(mime_type)
    extension = _normalise_extension(filename)
    ooxml_family = _detect_ooxml_family(file_bytes)

    if normalised == _DOC_LEGACY_MIME or extension == ".doc":
        return "legacy-doc"

    if normalised == _XLS_MIME or extension == ".xls":
        return "xls"

    if normalised == _PDF_MIME or extension == ".pdf":
        return "pdf"

    if normalised == _DOCX_MIME or extension == ".docx" or ooxml_family == "docx":
        return "docx"

    if normalised == _XLSX_MIME or extension == ".xlsx" or ooxml_family == "xlsx":
        return "xlsx"

    if (
        normalised.startswith(_PPTX_MIME_PREFIX)
        or extension == ".pptx"
        or ooxml_family == "pptx"
    ):
        return "pptx"

    if is_ocr_candidate(normalised, filename):
        return "ocr"

    if normalised.startswith("text/") or extension in _TEXT_EXTENSIONS:
        return "text"

    if normalised in {"application/json", "application/xml", "application/csv"}:
        return "text"

    return None


def is_searchable_format(
    mime_type: str | None,
    filename: str | None = None,
) -> bool:
    """Return ``True`` when a file can be embedded as searchable text."""
    normalised = _normalise_mime(mime_type)
    extension = _normalise_extension(filename)

    if extension == ".doc" or normalised == _DOC_LEGACY_MIME:
        return False
    if is_ocr_candidate(normalised, filename):
        return True
    if extension in _TEXT_EXTENSIONS or extension in _DOCUMENT_EXTENSIONS:
        return True
    if normalised.startswith("text/"):
        return True
    if normalised.startswith(_PPTX_MIME_PREFIX):
        return True
    return normalised in _SEARCHABLE_MIMES


def extract_text_from_bytes(
    file_bytes: bytes,
    mime_type: str | None,
    *,
    filename: str | None = None,
) -> str | None:
    """Extract searchable Markdown/text from raw file bytes.

    Returns ``None`` for storage-only formats and raises ``ExtractionError``
    when a supported format cannot be parsed.
    """
    target = _resolve_extraction_target(file_bytes, mime_type, filename)

    if target is None:
        return None

    if target == "legacy-doc":
        raise ExtractionError(
            "Legacy DOC extraction is not supported yet. "
            "Please upload a DOCX, PDF, or text export."
        )

    if target == "ocr":
        try:
            return extract_text_with_gemini_vision(
                file_bytes,
                mime_type,
                filename=filename,
            )
        except DocumentOcrError as exc:
            raise ExtractionError(f"OCR extraction failed: {exc}") from exc

    try:
        markdown = convert_document_to_markdown(
            file_bytes,
            mime_type,
            filename=filename,
        ).markdown
    except DocumentConversionError as exc:
        label = target.upper() if target != "text" else "text"
        raise ExtractionError(f"{label} extraction failed: {exc}") from exc

    if markdown.strip() or target != "pdf":
        return markdown

    try:
        ocr_text = extract_text_with_gemini_vision(
            file_bytes,
            mime_type,
            filename=filename,
        )
    except DocumentOcrError as exc:
        logger.warning(
            "OCR fallback failed for %s after empty MarkItDown PDF output: %s",
            filename or "<unnamed>",
            exc,
        )
        return markdown

    return ocr_text or markdown
