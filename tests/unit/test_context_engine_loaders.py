from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.context_engine.loaders import (
    StructuredMemoryFact,
    load_structured_memory_facts,
    load_structured_memory_facts_sync,
)


VALID_USER_ID = "11111111-1111-1111-1111-111111111111"


class FakeMemoryFactsQuery:
    def __init__(self, rows=None, *, exc: Exception | None = None):
        self.rows = rows or []
        self.exc = exc
        self.calls: list[tuple[str, tuple, dict]] = []

    def select(self, *args, **kwargs):
        self.calls.append(("select", args, kwargs))
        return self

    def eq(self, *args, **kwargs):
        self.calls.append(("eq", args, kwargs))
        return self

    def or_(self, *args, **kwargs):
        self.calls.append(("or_", args, kwargs))
        return self

    def limit(self, *args, **kwargs):
        self.calls.append(("limit", args, kwargs))
        return self

    async def execute(self):
        self.calls.append(("execute", (), {}))
        if self.exc:
            raise self.exc
        return SimpleNamespace(data=self.rows)


class FakeMemoryFactsClient:
    def __init__(self, query: FakeMemoryFactsQuery):
        self.query = query
        self.tables: list[str] = []

    def table(self, name: str):
        self.tables.append(name)
        return self.query


class FakeSyncMemoryFactsQuery:
    def __init__(self, rows=None, *, exc: Exception | None = None):
        self.rows = rows or []
        self.exc = exc
        self.calls: list[tuple[str, tuple, dict]] = []

    def select(self, *args, **kwargs):
        self.calls.append(("select", args, kwargs))
        return self

    def eq(self, *args, **kwargs):
        self.calls.append(("eq", args, kwargs))
        return self

    def or_(self, *args, **kwargs):
        self.calls.append(("or_", args, kwargs))
        return self

    def limit(self, *args, **kwargs):
        self.calls.append(("limit", args, kwargs))
        return self

    def execute(self):
        self.calls.append(("execute", (), {}))
        if self.exc:
            raise self.exc
        return SimpleNamespace(data=self.rows)


@pytest.mark.asyncio
async def test_load_structured_memory_facts_returns_empty_for_invalid_user_id():
    get_client = AsyncMock()
    supabase_module = SimpleNamespace(get_async_client=get_client)

    with patch.dict(sys.modules, {"app.services.supabase_client": supabase_module}):
        assert await load_structured_memory_facts(None, agent_name="Planner") == []
        assert await load_structured_memory_facts("not-a-uuid") == []

    get_client.assert_not_called()


@pytest.mark.asyncio
async def test_load_structured_memory_facts_maps_database_rows():
    rows = [
        {
            "key": "preferred_currency",
            "value_json": {"code": "USD"},
            "memory_type": "preference",
            "scope": "global",
            "agent_id": "",
            "confidence": 0.91,
            "source_kind": "conversation",
            "source_ref": "session-1",
            "last_observed_at": "2026-06-01T12:00:00+00:00",
            "updated_at": "2026-06-02T12:00:00+00:00",
        }
    ]
    query = FakeMemoryFactsQuery(rows)
    client = FakeMemoryFactsClient(query)
    supabase_module = SimpleNamespace(get_async_client=AsyncMock(return_value=client))

    with patch.dict(sys.modules, {"app.services.supabase_client": supabase_module}):
        facts = await load_structured_memory_facts(VALID_USER_ID)

    assert facts == [
        StructuredMemoryFact(
            key="preferred_currency",
            value_json={"code": "USD"},
            memory_type="preference",
            scope="global",
            agent_id="",
            confidence=0.91,
            source_kind="conversation",
            source_ref="session-1",
            last_observed_at="2026-06-01T12:00:00+00:00",
            updated_at="2026-06-02T12:00:00+00:00",
        )
    ]
    assert client.tables == ["user_memory_facts"]


@pytest.mark.asyncio
async def test_load_structured_memory_facts_filters_global_and_matching_agent_scope():
    query = FakeMemoryFactsQuery([])
    client = FakeMemoryFactsClient(query)
    supabase_module = SimpleNamespace(get_async_client=AsyncMock(return_value=client))

    with patch.dict(sys.modules, {"app.services.supabase_client": supabase_module}):
        facts = await load_structured_memory_facts(
            VALID_USER_ID,
            agent_name="FinancialAnalysisAgent",
            limit=7,
        )

    assert facts == []
    assert ("eq", ("user_id", VALID_USER_ID), {}) in query.calls
    assert (
        "or_",
        (
            'scope.eq.global,and(scope.eq.agent,agent_id.eq."FinancialAnalysisAgent")',
        ),
        {},
    ) in query.calls
    assert ("limit", (7,), {}) in query.calls


@pytest.mark.asyncio
async def test_load_structured_memory_facts_returns_empty_on_database_failure():
    query = FakeMemoryFactsQuery(exc=RuntimeError("database unavailable"))
    client = FakeMemoryFactsClient(query)
    supabase_module = SimpleNamespace(get_async_client=AsyncMock(return_value=client))

    with patch.dict(sys.modules, {"app.services.supabase_client": supabase_module}):
        assert await load_structured_memory_facts(VALID_USER_ID) == []


def test_load_structured_memory_facts_sync_maps_rows():
    rows = [
        {
            "key": "preferred_currency",
            "value_json": "USD",
            "memory_type": "preference",
            "scope": "agent",
            "agent_id": "FinancialAnalysisAgent",
        }
    ]
    query = FakeSyncMemoryFactsQuery(rows)
    client = FakeMemoryFactsClient(query)
    supabase_module = SimpleNamespace(get_service_client=lambda: client)

    with patch.dict(sys.modules, {"app.services.supabase_client": supabase_module}):
        facts = load_structured_memory_facts_sync(
            VALID_USER_ID,
            agent_name="FinancialAnalysisAgent",
        )

    assert facts == [
        StructuredMemoryFact(
            key="preferred_currency",
            value_json="USD",
            memory_type="preference",
            scope="agent",
            agent_id="FinancialAnalysisAgent",
        )
    ]
    assert client.tables == ["user_memory_facts"]
    assert (
        "or_",
        (
            'scope.eq.global,and(scope.eq.agent,agent_id.eq."FinancialAnalysisAgent")',
        ),
        {},
    ) in query.calls


def test_load_structured_memory_facts_sync_returns_empty_for_invalid_user_id():
    supabase_module = SimpleNamespace(get_service_client=MagicMock())

    with patch.dict(sys.modules, {"app.services.supabase_client": supabase_module}):
        assert load_structured_memory_facts_sync("not-a-uuid") == []

    supabase_module.get_service_client.assert_not_called()
