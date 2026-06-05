# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Best-effort durable memory loaders for the context engine."""

from __future__ import annotations

from dataclasses import dataclass
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


__all__ = ["StructuredMemoryFact", "load_structured_memory_facts"]
