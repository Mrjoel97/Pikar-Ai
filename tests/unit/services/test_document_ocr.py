# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_resolve_ocr_mime_type_uses_filename_fallback():
    from app.services.document_ocr import resolve_ocr_mime_type

    assert (
        resolve_ocr_mime_type("application/octet-stream", "scan.pdf")
        == "application/pdf"
    )
    assert (
        resolve_ocr_mime_type("application/octet-stream", "receipt.jpeg")
        == "image/jpeg"
    )


def test_extract_text_with_gemini_vision_uses_fallback_model_and_bytes():
    from app.services.document_ocr import extract_text_with_gemini_vision

    model = MagicMock()
    model.model = "gemini-2.5-flash"
    model.api_client.models.generate_content.return_value = MagicMock(text="OCR text")

    with patch("app.agents.shared.get_model", return_value=model) as get_model:
        result = extract_text_with_gemini_vision(
            b"%PDF",
            "application/pdf",
            filename="scan.pdf",
        )

    assert result == "OCR text"
    get_model.assert_called_once()
    call = model.api_client.models.generate_content.call_args
    assert call.kwargs["model"] == "gemini-2.5-flash"
