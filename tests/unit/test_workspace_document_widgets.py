from __future__ import annotations

from app.agents.tools.docs import _build_document_widget
from app.agents.tools.forms import _build_form_widget
from app.agents.tools.google_sheets import _build_sheet_widget


def test_google_doc_widget_matches_frontend_document_contract() -> None:
    widget = _build_document_widget(
        title="Strategy Memo",
        doc_id="doc-1",
        doc_url="https://docs.google.com/document/d/doc-1",
    )

    assert widget["type"] == "document"
    assert widget["data"]["documentUrl"] == "https://docs.google.com/document/d/doc-1"
    assert widget["data"]["title"] == "Strategy Memo"
    assert widget["data"]["fileType"] == "gdoc"
    assert widget["data"]["sizeBytes"] == 0


def test_google_sheet_widget_matches_frontend_document_contract() -> None:
    widget = _build_sheet_widget(
        title="Revenue Tracker",
        doc_id="sheet-1",
        doc_url="https://docs.google.com/spreadsheets/d/sheet-1",
    )

    assert widget["type"] == "document"
    assert (
        widget["data"]["documentUrl"]
        == "https://docs.google.com/spreadsheets/d/sheet-1"
    )
    assert widget["data"]["title"] == "Revenue Tracker"
    assert widget["data"]["fileType"] == "gsheet"
    assert widget["data"]["sizeBytes"] == 0


def test_google_form_widget_matches_frontend_document_contract() -> None:
    widget = _build_form_widget(
        title="Customer Feedback",
        form_id="form-1",
        form_url="https://docs.google.com/forms/d/form-1/viewform",
        edit_url="https://docs.google.com/forms/d/form-1/edit",
    )

    assert widget["type"] == "document"
    assert (
        widget["data"]["documentUrl"]
        == "https://docs.google.com/forms/d/form-1/viewform"
    )
    assert widget["data"]["title"] == "Customer Feedback"
    assert widget["data"]["fileType"] == "gform"
    assert widget["data"]["sizeBytes"] == 0
    assert widget["data"]["editUrl"] == "https://docs.google.com/forms/d/form-1/edit"
