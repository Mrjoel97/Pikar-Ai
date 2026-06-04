from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_supabase(inserted_id: str = "doc-1") -> tuple[MagicMock, MagicMock, MagicMock]:
    supabase = MagicMock()
    bucket = MagicMock()
    supabase.storage.from_.return_value = bucket

    insert_query = MagicMock()
    insert_query.execute.return_value = SimpleNamespace(data=[{"id": inserted_id}])

    update_query = MagicMock()
    update_query.eq.return_value = update_query
    update_query.execute.return_value = SimpleNamespace(data=[{"id": inserted_id}])

    table = MagicMock()
    table.insert.return_value = insert_query
    table.update.return_value = update_query
    supabase.table.return_value = table
    return supabase, table, update_query


@pytest.mark.asyncio
async def test_save_to_vault_finalizes_embedding_count(monkeypatch):
    from app.agents.tools import brain_dump
    from app.rag import knowledge_vault
    from app.services import supabase_client

    supabase, table, update_query = _make_supabase()
    ingest_mock = AsyncMock(return_value={"success": True, "chunk_count": 3})
    monkeypatch.setattr(supabase_client, "get_service_client", lambda: supabase)
    monkeypatch.setattr(knowledge_vault, "ingest_document_content", ingest_mock)

    result = await brain_dump._save_to_vault(
        "Markdown content for search",
        "Brain Dump Transcript",
        "Brain Dump Transcript",
        "user-1",
    )

    assert result["doc_id"] == "doc-1"
    assert result["file_path"].startswith("user-1/brain_dump_transcript_")
    inserted = table.insert.call_args.args[0]
    assert inserted["is_processed"] is False
    assert inserted["embedding_count"] == 0
    assert inserted["metadata"]["processing_status"] == "processing"

    ingest_mock.assert_awaited_once()
    assert ingest_mock.await_args.kwargs["user_id"] == "user-1"
    assert ingest_mock.await_args.kwargs["metadata"]["document_id"] == "doc-1"

    update_payload = table.update.call_args.args[0]
    assert update_payload["is_processed"] is True
    assert update_payload["embedding_count"] == 3
    assert update_payload["metadata"]["processing_status"] == "completed"
    update_query.eq.assert_any_call("id", "doc-1")


@pytest.mark.asyncio
async def test_save_to_vault_ingest_false_leaves_pending(monkeypatch):
    from app.agents.tools import brain_dump
    from app.rag import knowledge_vault
    from app.services import supabase_client

    supabase, table, _update_query = _make_supabase()
    ingest_mock = AsyncMock()
    monkeypatch.setattr(supabase_client, "get_service_client", lambda: supabase)
    monkeypatch.setattr(knowledge_vault, "ingest_document_content", ingest_mock)

    result = await brain_dump._save_to_vault(
        "Transcript content",
        "Brain Dump Transcript",
        "Brain Dump Transcript",
        "user-1",
        ingest=False,
    )

    assert result["doc_id"] == "doc-1"
    inserted = table.insert.call_args.args[0]
    assert inserted["is_processed"] is False
    assert inserted["embedding_count"] == 0
    assert inserted["metadata"]["processing_status"] == "pending_ingestion"
    ingest_mock.assert_not_awaited()
    table.update.assert_not_called()


@pytest.mark.asyncio
async def test_background_transcript_ingestion_marks_vault_row_searchable(monkeypatch):
    from app.rag import knowledge_vault
    from app.routers import voice_session
    from app.services import supabase_client

    supabase, table, update_query = _make_supabase()
    ingest_mock = AsyncMock(return_value={"success": True, "chunk_count": 2})
    monkeypatch.setattr(supabase_client, "get_service_client", lambda: supabase)
    monkeypatch.setattr(knowledge_vault, "ingest_document_content", ingest_mock)

    await voice_session._ingest_brainstorm_transcript_background(
        transcript_markdown="## Transcript\nUser: hello",
        transcript_file_path="user-1/transcript.md",
        transcript_doc_id="doc-1",
        session_id="session-1",
        user_id="user-1",
    )

    update_payload = table.update.call_args.args[0]
    assert update_payload["is_processed"] is True
    assert update_payload["embedding_count"] == 2
    assert update_payload["metadata"]["processing_status"] == "completed"
    update_query.eq.assert_any_call("id", "doc-1")
    update_query.eq.assert_any_call("user_id", "user-1")


@pytest.mark.asyncio
async def test_add_business_knowledge_passes_current_user(monkeypatch):
    from app.agents.tools import brain_dump
    from app.orchestration import knowledge_tools
    from app.services import request_context

    save_mock = AsyncMock(
        return_value={
            "doc_id": "doc-1",
            "file_path": "user-1/policy.md",
            "embedding_count": 1,
            "processed": True,
        }
    )
    monkeypatch.setattr(request_context, "get_current_user_id", lambda: "user-1")
    monkeypatch.setattr(brain_dump, "_save_to_vault", save_mock)

    result = await knowledge_tools.add_business_knowledge(
        "Company policy", "Policy", category="policy"
    )

    assert result["success"] is True
    assert result["user_scoped"] is True
    assert result["document_id"] == "doc-1"
    save_mock.assert_awaited_once_with(
        "Company policy",
        "Policy",
        "policy",
        "user-1",
        metadata={
            "category": "policy",
            "source": "executive_knowledge_tool",
            "title": "Policy",
        },
    )
