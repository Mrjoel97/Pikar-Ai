# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_convert_document_to_markdown_uses_byte_stream_and_stream_info():
    from app.services.document_conversion import convert_document_to_markdown

    markitdown = MagicMock()
    markitdown.convert_stream.return_value = MagicMock(markdown="# Converted")

    with patch(
        "app.services.document_conversion._get_markitdown", return_value=markitdown
    ):
        result = convert_document_to_markdown(
            b"hello",
            "text/plain; charset=utf-8",
            filename="notes.txt",
        )

    assert result.markdown == "# Converted"
    call = markitdown.convert_stream.call_args
    stream = call.args[0]
    stream_info = call.kwargs["stream_info"]
    assert stream.read() == b"hello"
    assert stream_info.mimetype == "text/plain"
    assert stream_info.extension == ".txt"
    assert stream_info.filename == "notes.txt"
    assert stream_info.url is None
    assert stream_info.local_path is None
