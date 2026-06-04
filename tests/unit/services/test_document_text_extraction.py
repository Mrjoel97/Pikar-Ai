# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for the shared document extraction boundary."""

from __future__ import annotations

import io
import zipfile
from unittest.mock import patch

import pytest

from app.services.document_conversion import (
    DocumentConversionError,
    DocumentConversionResult,
)


def _make_ooxml_bytes(folder: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr(f"{folder}/document.xml", "<xml />")
    return buf.getvalue()


def _mock_markdown(markdown: str = "# Extracted\n\nBody") -> DocumentConversionResult:
    return DocumentConversionResult(markdown=markdown)


class TestExtractTextFromBytes:
    def test_supported_text_routes_to_markitdown_stream_adapter(self):
        from app.services.document_text_extraction import extract_text_from_bytes

        with patch(
            "app.services.document_text_extraction.convert_document_to_markdown",
            return_value=_mock_markdown("Hello, plain text world!"),
        ) as convert:
            result = extract_text_from_bytes(b"Hello, plain text world!", "text/plain")

        assert result == "Hello, plain text world!"
        convert.assert_called_once_with(
            b"Hello, plain text world!",
            "text/plain",
            filename=None,
        )

    @pytest.mark.parametrize(
        ("filename", "mime_type"),
        [
            ("report.pdf", "application/pdf"),
            (
                "contract.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            (
                "pipeline.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            ("legacy.xls", "application/vnd.ms-excel"),
            (
                "deck.pptx",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ),
            ("page.html", "text/html"),
            ("data.json", "application/json"),
            ("feed.xml", "application/xml"),
        ],
    )
    def test_supported_document_types_route_to_markitdown(
        self, filename: str, mime_type: str
    ):
        from app.services.document_text_extraction import extract_text_from_bytes

        with patch(
            "app.services.document_text_extraction.convert_document_to_markdown",
            return_value=_mock_markdown("Converted markdown"),
        ) as convert:
            result = extract_text_from_bytes(
                b"document-bytes", mime_type, filename=filename
            )

        assert result == "Converted markdown"
        convert.assert_called_once_with(b"document-bytes", mime_type, filename=filename)

    def test_octet_stream_docx_filename_fallback(self):
        from app.services.document_text_extraction import extract_text_from_bytes

        with patch(
            "app.services.document_text_extraction.convert_document_to_markdown",
            return_value=_mock_markdown("DOCX fallback"),
        ):
            result = extract_text_from_bytes(
                b"fake-docx",
                "application/octet-stream",
                filename="contract.docx",
            )

        assert result == "DOCX fallback"

    def test_ooxml_pptx_bytes_route_to_converter_even_with_generic_name(self):
        from app.services.document_text_extraction import extract_text_from_bytes

        pptx_bytes = _make_ooxml_bytes("ppt")
        with patch(
            "app.services.document_text_extraction.convert_document_to_markdown",
            return_value=_mock_markdown("Slide text"),
        ) as convert:
            result = extract_text_from_bytes(
                pptx_bytes,
                "application/octet-stream",
                filename="upload",
            )

        assert result == "Slide text"
        convert.assert_called_once_with(
            pptx_bytes,
            "application/octet-stream",
            filename="upload",
        )

    def test_image_routes_to_gemini_ocr(self):
        from app.services.document_text_extraction import extract_text_from_bytes

        with patch(
            "app.services.document_text_extraction.extract_text_with_gemini_vision",
            return_value="OCR image text",
        ) as ocr:
            result = extract_text_from_bytes(
                b"\x89PNG\r\nimage-bytes",
                "image/png",
                filename="scan.png",
            )

        assert result == "OCR image text"
        ocr.assert_called_once_with(
            b"\x89PNG\r\nimage-bytes",
            "image/png",
            filename="scan.png",
        )

    def test_unsupported_video_returns_storage_only(self):
        from app.services.document_text_extraction import extract_text_from_bytes

        assert extract_text_from_bytes(b"fake-video-bytes", "video/mp4") is None

    def test_empty_pdf_markitdown_output_falls_back_to_ocr(self):
        from app.services.document_text_extraction import extract_text_from_bytes

        with (
            patch(
                "app.services.document_text_extraction.convert_document_to_markdown",
                return_value=_mock_markdown(""),
            ) as convert,
            patch(
                "app.services.document_text_extraction.extract_text_with_gemini_vision",
                return_value="Scanned PDF text",
            ) as ocr,
        ):
            result = extract_text_from_bytes(
                b"%PDF scanned",
                "application/pdf",
                filename="scan.pdf",
            )

        assert result == "Scanned PDF text"
        convert.assert_called_once()
        ocr.assert_called_once_with(
            b"%PDF scanned",
            "application/pdf",
            filename="scan.pdf",
        )

    def test_legacy_doc_raises_clear_error(self):
        from app.services.document_text_extraction import (
            ExtractionError,
            extract_text_from_bytes,
        )

        with pytest.raises(ExtractionError, match="Legacy DOC extraction"):
            extract_text_from_bytes(
                b"\xd0\xcf\x11\xe0legacy-doc",
                "application/msword",
                filename="proposal.doc",
            )

    def test_conversion_error_is_wrapped_as_extraction_error(self):
        from app.services.document_text_extraction import (
            ExtractionError,
            extract_text_from_bytes,
        )

        with patch(
            "app.services.document_text_extraction.convert_document_to_markdown",
            side_effect=DocumentConversionError("malformed PDF"),
        ):
            with pytest.raises(ExtractionError, match="PDF extraction failed"):
                extract_text_from_bytes(b"bad-pdf-bytes", "application/pdf")


class TestIsSearchableFormat:
    @pytest.mark.parametrize(
        "mime_type",
        [
            "application/pdf",
            "application/json",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/xml",
            "image/png",
            "text/html",
            "text/markdown",
            "text/plain",
            "text/xml",
        ],
    )
    def test_supported_mimes_are_searchable(self, mime_type: str):
        from app.services.document_text_extraction import is_searchable_format

        assert is_searchable_format(mime_type) is True

    @pytest.mark.parametrize("mime_type", ["video/mp4", "", None])
    def test_storage_only_mimes_are_not_searchable(self, mime_type: str | None):
        from app.services.document_text_extraction import is_searchable_format

        assert is_searchable_format(mime_type) is False

    def test_filename_extension_fallback_is_searchable(self):
        from app.services.document_text_extraction import is_searchable_format

        assert is_searchable_format("application/octet-stream", filename="notes.docx")
        assert is_searchable_format("application/octet-stream", filename="table.xlsx")
        assert is_searchable_format("application/octet-stream", filename="slides.pptx")
        assert is_searchable_format("application/octet-stream", filename="old.xls")
        assert not is_searchable_format("application/octet-stream", filename="old.doc")
