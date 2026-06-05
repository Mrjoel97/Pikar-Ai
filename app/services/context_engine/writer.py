# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Write-side primitives for durable context memory facts."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_TABLE = "user_memory_facts"
_SAFE_SCOPE = "global"
_SAFE_MEMORY_TYPE = "fact"
_SAFE_SOURCE_KIND = "conversation"
_VALID_SCOPES = frozenset({"global", "agent", "workspace", "initiative"})
_VALID_MEMORY_TYPES = frozenset({"fact", "preference", "goal", "constraint"})
_PREFERENCE_KEYWORDS = frozenset(
    {
        "preference",
        "preferred",
        "tone",
        "style",
        "format",
        "language",
        "timezone",
        "channel",
        "cadence",
    }
)
_GOAL_KEYWORDS = frozenset(
    {
        "goal",
        "objective",
        "target",
        "kpi",
        "okr",
        "milestone",
        "priority",
        "north_star",
    }
)
_CONSTRAINT_KEYWORDS = frozenset(
    {
        "constraint",
        "requirement",
        "budget",
        "deadline",
        "compliance",
        "legal",
        "risk",
        "avoid",
        "never",
        "must",
        "do_not",
    }
)
_AGENT_SCOPE_PREFIXES = ("agent:", "agent.", "agent_")


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_enum(value: Any, valid_values: frozenset[str], default: str) -> str:
    normalized = _clean_text(value).lower()
    if normalized in valid_values:
        return normalized
    return default


def _normalize_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.9
    return min(1.0, max(0.0, confidence))


def _normalize_json_value(value: Any) -> Any:
    """Return a JSON-compatible value for the ``value_json`` column."""
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return str(value)
    return value


def _key_tokens(key: str) -> set[str]:
    normalized = _clean_text(key).lower().replace("-", "_")
    tokens = {token for token in normalized.replace(".", "_").split("_") if token}
    tokens.add(normalized)
    return tokens


def _normalize_agent_key(agent_name: str | None) -> str:
    return _clean_text(agent_name).lower().replace(" ", "").replace("_", "")


def infer_user_memory_fact_write_policy(
    key: str,
    *,
    agent_name: str | None = None,
) -> dict[str, str]:
    """Infer memory type and scope for a saved context key.

    The policy is intentionally deterministic and conservative. Ambiguous keys
    remain global facts; callers can still pass explicit values to
    ``normalize_user_memory_fact_payload`` when they know more.
    """
    normalized_key = _clean_text(key).lower()
    tokens = _key_tokens(normalized_key)

    memory_type = _SAFE_MEMORY_TYPE
    if tokens & _CONSTRAINT_KEYWORDS:
        memory_type = "constraint"
    elif tokens & _GOAL_KEYWORDS:
        memory_type = "goal"
    elif tokens & _PREFERENCE_KEYWORDS:
        memory_type = "preference"

    scope = _SAFE_SCOPE
    agent_id = ""
    normalized_agent = _normalize_agent_key(agent_name)
    explicit_agent_scope = normalized_key.startswith(_AGENT_SCOPE_PREFIXES)
    agent_prefixed_key = bool(
        normalized_agent
        and normalized_key.replace("_", "").startswith(normalized_agent)
    )
    if agent_name and (explicit_agent_scope or agent_prefixed_key):
        scope = "agent"
        agent_id = _clean_text(agent_name)

    return {
        "memory_type": memory_type,
        "scope": scope,
        "agent_id": agent_id,
    }


def normalize_user_memory_fact_payload(
    user_id: str,
    key: str,
    value: Any,
    memory_type: str = _SAFE_MEMORY_TYPE,
    scope: str = _SAFE_SCOPE,
    agent_id: str = "",
    confidence: float = 0.9,
    source_kind: str = _SAFE_SOURCE_KIND,
    source_ref: str | None = None,
) -> dict[str, Any] | None:
    """Normalize a durable ``user_memory_facts`` write payload.

    Returns ``None`` when the required identity or memory key is missing.
    Callers can treat that as a write no-op.
    """
    normalized_user_id = _clean_text(user_id)
    normalized_key = _clean_text(key)
    if not normalized_user_id or not normalized_key:
        return None

    normalized_source_kind = _clean_text(source_kind) or _SAFE_SOURCE_KIND
    normalized_source_ref = _clean_text(source_ref) or None

    return {
        "user_id": normalized_user_id,
        "scope": _normalize_enum(scope, _VALID_SCOPES, _SAFE_SCOPE),
        "agent_id": _clean_text(agent_id),
        "memory_type": _normalize_enum(
            memory_type,
            _VALID_MEMORY_TYPES,
            _SAFE_MEMORY_TYPE,
        ),
        "key": normalized_key,
        "value_json": _normalize_json_value(value),
        "confidence": _normalize_confidence(confidence),
        "source_kind": normalized_source_kind,
        "source_ref": normalized_source_ref,
    }


async def upsert_user_memory_fact(payload: dict[str, Any] | None) -> bool:
    """Best-effort upsert for a normalized ``user_memory_facts`` payload."""
    if not payload:
        return False

    try:
        from app.services.supabase_client import get_async_client

        client = await get_async_client()
        await (
            client.table(_TABLE)
            .upsert(payload, on_conflict="user_id,scope,agent_id,key")
            .execute()
        )
        return True
    except Exception as exc:  # pragma: no cover - best-effort
        logger.debug("[ContextWriter] upsert_user_memory_fact failed: %s", exc)
        return False


def upsert_user_memory_fact_sync(payload: dict[str, Any] | None) -> bool:
    """Sync variant for ADK callbacks that cannot await async writers."""
    if not payload:
        return False

    try:
        from app.services.supabase_client import get_service_client

        client = get_service_client()
        if not client:
            return False
        client.table(_TABLE).upsert(
            payload,
            on_conflict="user_id,scope,agent_id,key",
        ).execute()
        return True
    except Exception as exc:  # pragma: no cover - best-effort
        logger.debug("[ContextWriter] upsert_user_memory_fact_sync failed: %s", exc)
        return False


__all__ = [
    "infer_user_memory_fact_write_policy",
    "normalize_user_memory_fact_payload",
    "upsert_user_memory_fact",
    "upsert_user_memory_fact_sync",
]
