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


__all__ = [
    "normalize_user_memory_fact_payload",
    "upsert_user_memory_fact",
]
