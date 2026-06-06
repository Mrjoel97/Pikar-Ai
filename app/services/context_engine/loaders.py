# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Best-effort durable memory loaders for the context engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

_USER_MEMORY_FACTS_TABLE = "user_memory_facts"
_FACT_COLUMNS = (
    "key,value_json,memory_type,scope,agent_id,confidence,source_kind,"
    "source_ref,last_observed_at,updated_at"
)
_DEFAULT_FACT_LIMIT = 20
_MEMORY_TYPE_ORDER = {
    "constraint": 0,
    "goal": 1,
    "preference": 2,
    "fact": 3,
}


@dataclass(frozen=True)
class StructuredMemoryFact:
    """A lightweight read model for durable structured memory."""

    key: str
    value_json: Any
    memory_type: str = "fact"
    scope: str = "global"
    agent_id: str = ""
    confidence: float | None = None
    source_kind: str = "conversation"
    source_ref: str | None = None
    last_observed_at: str | None = None
    updated_at: str | None = None


def _is_valid_user_id(user_id: str | None) -> bool:
    if not user_id:
        return False
    try:
        UUID(str(user_id))
    except (TypeError, ValueError, AttributeError):
        return False
    return True


def _scope_filter(agent_name: str | None) -> str:
    if not agent_name:
        return "scope.eq.global"
    escaped_agent = str(agent_name).replace('"', '\\"')
    return f'scope.eq.global,and(scope.eq.agent,agent_id.eq."{escaped_agent}")'


def _map_fact(row: dict[str, Any]) -> StructuredMemoryFact:
    return StructuredMemoryFact(
        key=str(row.get("key") or ""),
        value_json=row.get("value_json"),
        memory_type=str(row.get("memory_type") or "fact"),
        scope=str(row.get("scope") or "global"),
        agent_id=str(row.get("agent_id") or ""),
        confidence=row.get("confidence"),
        source_kind=str(row.get("source_kind") or "conversation"),
        source_ref=row.get("source_ref"),
        last_observed_at=row.get("last_observed_at"),
        updated_at=row.get("updated_at"),
    )


def _normalize_key(key: str) -> str:
    return str(key or "").strip().lower()


def _scope_rank(fact: StructuredMemoryFact, agent_name: str | None) -> int:
    scope = str(fact.scope or "global").strip().lower()
    if (
        scope == "agent"
        and agent_name
        and str(fact.agent_id or "").strip() == str(agent_name).strip()
    ):
        return 2
    if scope == "global":
        return 1
    return 0


def _safe_confidence(confidence: float | None) -> float:
    try:
        return float(confidence)
    except (TypeError, ValueError):
        return 0.0


def _timestamp_rank(fact: StructuredMemoryFact) -> float:
    raw = fact.last_observed_at or fact.updated_at
    if not raw:
        return 0.0
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError, OSError):
        return 0.0


def _selection_rank(
    fact: StructuredMemoryFact,
    *,
    agent_name: str | None,
) -> tuple[int, float, float]:
    return (
        _scope_rank(fact, agent_name),
        _safe_confidence(fact.confidence),
        _timestamp_rank(fact),
    )


def select_structured_memory_facts_for_prompt(
    facts: list[StructuredMemoryFact],
    *,
    agent_name: str | None = None,
    limit: int = _DEFAULT_FACT_LIMIT,
) -> list[StructuredMemoryFact]:
    """Choose deterministic, non-conflicting facts for prompt injection.

    When multiple rows share the same key, agent-scoped rows win over global
    rows for that agent. Ties then prefer higher confidence and newer
    observation/update timestamps.
    """
    safe_limit = max(1, int(limit or _DEFAULT_FACT_LIMIT))
    best_by_key: dict[str, StructuredMemoryFact] = {}

    for fact in facts:
        normalized_key = _normalize_key(fact.key)
        if not normalized_key:
            continue
        current = best_by_key.get(normalized_key)
        if current is None or _selection_rank(
            fact,
            agent_name=agent_name,
        ) > _selection_rank(current, agent_name=agent_name):
            best_by_key[normalized_key] = fact

    selected = list(best_by_key.values())
    selected.sort(
        key=lambda fact: (
            _MEMORY_TYPE_ORDER.get(str(fact.memory_type or "fact").lower(), 99),
            -_scope_rank(fact, agent_name),
            _normalize_key(fact.key),
        )
    )
    return selected[:safe_limit]


async def load_structured_memory_facts(
    user_id: str | None,
    *,
    agent_name: str | None = None,
    limit: int = _DEFAULT_FACT_LIMIT,
) -> list[StructuredMemoryFact]:
    """Load durable structured facts for a user.

    This is intentionally best-effort: invalid user IDs, missing rows, and
    backend failures all produce an empty list so context assembly cannot break
    an agent turn.
    """
    if not _is_valid_user_id(user_id):
        return []

    safe_limit = max(1, int(limit or _DEFAULT_FACT_LIMIT))

    try:
        from app.services.supabase_client import get_async_client

        client = await get_async_client()
        response = (
            await client.table(_USER_MEMORY_FACTS_TABLE)
            .select(_FACT_COLUMNS)
            .eq("user_id", str(user_id))
            .or_(_scope_filter(agent_name))
            .limit(safe_limit)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        return [_map_fact(row) for row in rows if isinstance(row, dict)]
    except Exception as exc:  # pragma: no cover - best-effort guard
        logger.debug(
            "[ContextEngine] load_structured_memory_facts(user=%s, agent=%s) failed: %s",
            user_id,
            agent_name,
            exc,
        )
        return []


def load_structured_memory_facts_sync(
    user_id: str | None,
    *,
    agent_name: str | None = None,
    limit: int = _DEFAULT_FACT_LIMIT,
) -> list[StructuredMemoryFact]:
    """Sync variant for ADK callbacks that cannot await async loaders."""
    if not _is_valid_user_id(user_id):
        return []

    safe_limit = max(1, int(limit or _DEFAULT_FACT_LIMIT))

    try:
        from app.services.supabase_client import get_service_client

        client = get_service_client()
        if not client:
            return []
        response = (
            client.table(_USER_MEMORY_FACTS_TABLE)
            .select(_FACT_COLUMNS)
            .eq("user_id", str(user_id))
            .or_(_scope_filter(agent_name))
            .limit(safe_limit)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        return [_map_fact(row) for row in rows if isinstance(row, dict)]
    except Exception as exc:  # pragma: no cover - best-effort guard
        logger.debug(
            (
                "[ContextEngine] load_structured_memory_facts_sync"
                "(user=%s, agent=%s) failed: %s"
            ),
            user_id,
            agent_name,
            exc,
        )
        return []


__all__ = [
    "StructuredMemoryFact",
    "load_structured_memory_facts",
    "load_structured_memory_facts_sync",
    "select_structured_memory_facts_for_prompt",
]
