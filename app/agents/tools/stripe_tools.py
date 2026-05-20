# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Stripe agent tools -- revenue summary and manual sync trigger.

Provides two agent-callable functions that wire into the StripeSyncService
and financial_records table created in Phase 41 Plan 01.  Tools extract the
current user from request context and return structured dicts for the agent.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_user_id() -> str | None:
    """Extract the current user ID from the request-scoped context."""
    from app.services.request_context import get_current_user_id

    return get_current_user_id()


# ---------------------------------------------------------------------------
# Period date calculation
# ---------------------------------------------------------------------------

_PERIOD_OFFSETS: dict[str, int] = {
    "current_month": 30,
    "last_month": 60,
    "last_3_months": 90,
    "last_6_months": 180,
    "last_year": 365,
}


def _period_start_date(period: str) -> str | None:
    """Return an ISO-8601 date string for the start of *period*.

    Returns None for all_time.
    """
    days = _PERIOD_OFFSETS.get(period)
    if days is None:
        return None  # all_time
    return (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()


# ---------------------------------------------------------------------------
# Tool: get_stripe_revenue_summary
# ---------------------------------------------------------------------------


async def _fetch_stripe_revenue_summary_uncached(
    *,
    user_id: str,
    period: str,
) -> dict[str, Any]:
    """Raw upstream fetch; called only on a cache miss."""
    from app.services.base_service import BaseService
    from app.services.supabase_async import execute_async

    svc = BaseService()
    query = (
        svc.client.table("financial_records")
        .select("amount, currency, transaction_date")
        .eq("user_id", user_id)
        .eq("transaction_type", "revenue")
        .eq("source_type", "stripe")
    )
    start_date = _period_start_date(period)
    if start_date:
        query = query.gte("transaction_date", start_date)
    result = await execute_async(query, op_name="stripe_tools.revenue_summary")
    records = result.data or []

    total_revenue = sum(float(r.get("amount", 0)) for r in records)
    count = len(records)
    avg_value = round(total_revenue / count, 2) if count else 0
    return {
        "total_revenue": round(total_revenue, 2),
        "transaction_count": count,
        "period": period,
        "avg_transaction_value": avg_value,
        "currency": records[0].get("currency", "USD") if records else "USD",
    }


async def get_stripe_revenue_summary(
    period: str = "current_month",
) -> dict[str, Any]:
    """Get revenue summary from Stripe transactions, with two-tier caching.

    Cache: Redis tier, key=`stripe:revenue_summary:{period}`, TTL 300s.
    Period values: 'current_month', 'last_month', 'last_3_months',
    'last_6_months', 'last_year', or 'all_time'.

    Returns:
        Same shape as before plus an internal `_cache_hit` boolean
        useful for load testing (not exposed to LLMs).
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.agents.financial.cache import (
        STRIPE_REVENUE_TTL_S,
        build_stripe_revenue_key,
        cached_external_call,
    )

    try:
        payload, cache_hit = await cached_external_call(
            cache_key=build_stripe_revenue_key(period),
            ttl_seconds=STRIPE_REVENUE_TTL_S,
            fetcher=lambda: _fetch_stripe_revenue_summary_uncached(
                user_id=user_id,
                period=period,
            ),
            metric_tag="stripe_revenue_summary",
        )
        payload = dict(payload)
        payload["_cache_hit"] = cache_hit
        return payload
    except Exception as exc:
        logger.exception("stripe_tools.revenue_summary failed for user=%s", user_id)
        return {"error": f"Failed to retrieve Stripe revenue: {exc}"}


# ---------------------------------------------------------------------------
# Tool: get_stripe_disputes
# ---------------------------------------------------------------------------


async def _fetch_stripe_disputes_uncached(
    *,
    user_id: str,
    period: str,
) -> dict[str, Any]:
    """Fetch dispute / chargeback rows from financial_records.

    Disputes are stored as transaction_type='dispute' rows synced by
    StripeSyncService. Read-only -- returns counts and totals.
    """
    from app.services.base_service import BaseService
    from app.services.supabase_async import execute_async

    svc = BaseService()
    query = (
        svc.client.table("financial_records")
        .select("amount, currency, transaction_date")
        .eq("user_id", user_id)
        .eq("transaction_type", "dispute")
        .eq("source_type", "stripe")
    )
    start_date = _period_start_date(period)
    if start_date:
        query = query.gte("transaction_date", start_date)
    result = await execute_async(query, op_name="stripe_tools.disputes")
    rows = result.data or []
    total = sum(float(r.get("amount", 0)) for r in rows)
    return {
        "dispute_count": len(rows),
        "total_disputed": round(total, 2),
        "currency": rows[0].get("currency", "USD") if rows else "USD",
        "period": period,
    }


async def get_stripe_disputes(period: str = "current_month") -> dict[str, Any]:
    """Get Stripe disputes / chargebacks for the period, with cache.

    Cache: Redis tier, key=`stripe:disputes:{period}`, TTL 600s.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.agents.financial.cache import (
        STRIPE_DISPUTES_TTL_S,
        build_stripe_disputes_key,
        cached_external_call,
    )

    try:
        payload, cache_hit = await cached_external_call(
            cache_key=build_stripe_disputes_key(period),
            ttl_seconds=STRIPE_DISPUTES_TTL_S,
            fetcher=lambda: _fetch_stripe_disputes_uncached(
                user_id=user_id,
                period=period,
            ),
            metric_tag="stripe_disputes",
        )
        payload = dict(payload)
        payload["_cache_hit"] = cache_hit
        return payload
    except Exception as exc:
        logger.exception("stripe_tools.disputes failed for user=%s", user_id)
        return {"error": f"Failed to retrieve Stripe disputes: {exc}"}


# ---------------------------------------------------------------------------
# Tool: trigger_stripe_sync
# ---------------------------------------------------------------------------


async def trigger_stripe_sync() -> dict[str, Any]:
    """Trigger a manual sync of Stripe transaction history (last 12 months).

    Use when the user suspects missing transactions or wants to force
    a fresh import from Stripe.

    Returns:
        Dict with imported and skipped counts, or an error message.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.services.stripe_sync_service import StripeSyncService

    svc = StripeSyncService()

    try:
        result = await svc.sync_history(user_id)
        return {
            "status": "success",
            "imported": result.get("imported", 0),
            "skipped": result.get("skipped", 0),
            "message": (
                f"Stripe sync complete: {result.get('imported', 0)} new transactions "
                f"imported, {result.get('skipped', 0)} duplicates skipped."
            ),
        }
    except Exception as exc:
        logger.exception("trigger_stripe_sync failed for user=%s", user_id)
        return {"error": f"Stripe sync failed: {exc}"}


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

STRIPE_TOOLS = [get_stripe_revenue_summary, get_stripe_disputes, trigger_stripe_sync]
