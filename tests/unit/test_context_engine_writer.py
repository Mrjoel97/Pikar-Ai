# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

from __future__ import annotations

from typing import Any

import pytest

from app.services.context_engine.writer import (
    infer_user_memory_fact_write_policy,
    normalize_user_memory_fact_payload,
    upsert_user_memory_fact,
    upsert_user_memory_fact_sync,
)


def test_normalize_user_memory_fact_payload_defaults() -> None:
    payload = normalize_user_memory_fact_payload(
        user_id=" user-123 ",
        key=" company_name ",
        value="Pikar AI",
    )

    assert payload == {
        "user_id": "user-123",
        "scope": "global",
        "agent_id": "",
        "memory_type": "fact",
        "key": "company_name",
        "value_json": "Pikar AI",
        "confidence": 0.9,
        "source_kind": "conversation",
        "source_ref": None,
    }


def test_normalize_user_memory_fact_payload_invalid_enums_fall_back() -> None:
    payload = normalize_user_memory_fact_payload(
        user_id="user-123",
        key="growth_target",
        value="enterprise",
        scope="public",
        memory_type="secret",
    )

    assert payload is not None
    assert payload["scope"] == "global"
    assert payload["memory_type"] == "fact"


def test_normalize_user_memory_fact_payload_accepts_known_enums_case_insensitive() -> None:
    payload = normalize_user_memory_fact_payload(
        user_id="user-123",
        key="tone",
        value="direct",
        scope=" Agent ",
        memory_type=" Preference ",
        agent_id="marketing",
        confidence=1.4,
        source_kind="tool",
        source_ref="save_user_context",
    )

    assert payload is not None
    assert payload["scope"] == "agent"
    assert payload["memory_type"] == "preference"
    assert payload["agent_id"] == "marketing"
    assert payload["confidence"] == 1.0
    assert payload["source_kind"] == "tool"
    assert payload["source_ref"] == "save_user_context"


def test_normalize_user_memory_fact_payload_preserves_json_values() -> None:
    value = {
        "channels": ["email", "linkedin"],
        "budget": {"currency": "USD", "amount": 2500},
    }

    payload = normalize_user_memory_fact_payload(
        user_id="user-123",
        key="marketing_plan",
        value=value,
    )

    assert payload is not None
    assert payload["value_json"] == value


def test_normalize_user_memory_fact_payload_no_ops_missing_user_or_key() -> None:
    assert (
        normalize_user_memory_fact_payload(
            user_id="",
            key="company_name",
            value="Pikar AI",
        )
        is None
    )
    assert (
        normalize_user_memory_fact_payload(
            user_id="user-123",
            key=" ",
            value="Pikar AI",
        )
        is None
    )


@pytest.mark.parametrize(
    ("key", "expected_type"),
    [
        ("company_name", "fact"),
        ("preferred_tone", "preference"),
        ("business_goal", "goal"),
        ("budget_constraint", "constraint"),
        ("compliance_requirement", "constraint"),
    ],
)
def test_infer_user_memory_fact_write_policy_classifies_memory_type(
    key: str,
    expected_type: str,
) -> None:
    policy = infer_user_memory_fact_write_policy(key)

    assert policy == {
        "memory_type": expected_type,
        "scope": "global",
        "agent_id": "",
    }


def test_infer_user_memory_fact_write_policy_supports_agent_scope_prefix() -> None:
    policy = infer_user_memory_fact_write_policy(
        "agent:preferred_report_format",
        agent_name="FinancialAnalysisAgent",
    )

    assert policy == {
        "memory_type": "preference",
        "scope": "agent",
        "agent_id": "FinancialAnalysisAgent",
    }


def test_infer_user_memory_fact_write_policy_keeps_ambiguous_agentless_key_global() -> None:
    policy = infer_user_memory_fact_write_policy("agent:preferred_report_format")

    assert policy == {
        "memory_type": "preference",
        "scope": "global",
        "agent_id": "",
    }


class _FakeUserMemoryFactsTable:
    def __init__(self) -> None:
        self.payload: dict[str, Any] | None = None
        self.on_conflict: str | None = None
        self.executed = False

    def upsert(
        self,
        payload: dict[str, Any],
        on_conflict: str | None = None,
    ) -> "_FakeUserMemoryFactsTable":
        self.payload = payload
        self.on_conflict = on_conflict
        return self

    async def execute(self) -> object:
        self.executed = True
        return object()


class _FakeSyncUserMemoryFactsTable(_FakeUserMemoryFactsTable):
    def execute(self) -> object:
        self.executed = True
        return object()


class _FakeSupabaseClient:
    def __init__(self, table: _FakeUserMemoryFactsTable) -> None:
        self.table_name: str | None = None
        self._table = table

    def table(self, name: str) -> _FakeUserMemoryFactsTable:
        self.table_name = name
        return self._table


@pytest.mark.asyncio
async def test_upsert_user_memory_fact_uses_expected_conflict_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    table = _FakeUserMemoryFactsTable()
    client = _FakeSupabaseClient(table)

    async def fake_get_async_client() -> _FakeSupabaseClient:
        return client

    from app.services import supabase_client

    monkeypatch.setattr(supabase_client, "get_async_client", fake_get_async_client)

    payload = normalize_user_memory_fact_payload(
        user_id="user-123",
        key="company_name",
        value="Pikar AI",
    )

    assert await upsert_user_memory_fact(payload) is True
    assert client.table_name == "user_memory_facts"
    assert table.payload == payload
    assert table.on_conflict == "user_id,scope,agent_id,key"
    assert table.executed is True


@pytest.mark.asyncio
async def test_upsert_user_memory_fact_no_ops_invalid_payload() -> None:
    assert await upsert_user_memory_fact(None) is False


@pytest.mark.asyncio
async def test_upsert_user_memory_fact_swallows_db_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_async_client() -> object:
        raise RuntimeError("database unavailable")

    from app.services import supabase_client

    monkeypatch.setattr(supabase_client, "get_async_client", fake_get_async_client)

    assert (
        await upsert_user_memory_fact(
            {
                "user_id": "user-123",
                "scope": "global",
                "agent_id": "",
                "memory_type": "fact",
                "key": "company_name",
                "value_json": "Pikar AI",
                "confidence": 0.9,
                "source_kind": "conversation",
                "source_ref": None,
            }
        )
        is False
    )


def test_upsert_user_memory_fact_sync_uses_expected_conflict_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    table = _FakeSyncUserMemoryFactsTable()
    client = _FakeSupabaseClient(table)

    from app.services import supabase_client

    monkeypatch.setattr(supabase_client, "get_service_client", lambda: client)

    payload = normalize_user_memory_fact_payload(
        user_id="user-123",
        key="company_name",
        value="Pikar AI",
    )

    assert upsert_user_memory_fact_sync(payload) is True
    assert client.table_name == "user_memory_facts"
    assert table.payload == payload
    assert table.on_conflict == "user_id,scope,agent_id,key"
    assert table.executed is True


def test_upsert_user_memory_fact_sync_no_ops_invalid_payload() -> None:
    assert upsert_user_memory_fact_sync(None) is False


def test_upsert_user_memory_fact_sync_swallows_db_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import supabase_client

    monkeypatch.setattr(
        supabase_client,
        "get_service_client",
        lambda: (_ for _ in ()).throw(RuntimeError("database unavailable")),
    )

    assert (
        upsert_user_memory_fact_sync(
            {
                "user_id": "user-123",
                "scope": "global",
                "agent_id": "",
                "memory_type": "fact",
                "key": "company_name",
                "value_json": "Pikar AI",
                "confidence": 0.9,
                "source_kind": "conversation",
                "source_ref": None,
            }
        )
        is False
    )
