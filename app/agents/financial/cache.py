"""Financial Agent cache adapter — Phase 114 Plan 02.

Wraps the Phase 112 Redis-tier adaptive cache (`should_call_external` +
`CacheService.{get_with_age,set_with_age}`) so the Financial Agent's
external integrations (Stripe, Shopify) share a single helper.

Cache key shapes (caller passes period / shop, this module builds the key):
- Stripe revenue summary: ``stripe:revenue_summary:{period}``
- Stripe disputes:        ``stripe:disputes:{period}``
- Shopify orders:         ``shopify:orders:{period}:{shop}``

TTLs (seconds):
- STRIPE_REVENUE_TTL_S  = 300  (5 min)
- STRIPE_DISPUTES_TTL_S = 600  (10 min — disputes change less frequently)
- SHOPIFY_ORDERS_TTL_S  = 300  (5 min)

The cache adapter is intentionally tiny — it exists so the per-tool wrappers
in Tasks 2/3 can share a single, well-tested code path for "consult Redis,
fetch on miss, write-back best-effort".
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.services.cache import get_cache_service
from app.services.intelligence.cache import should_call_external

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TTL constants
# ---------------------------------------------------------------------------

STRIPE_REVENUE_TTL_S: int = 300
STRIPE_DISPUTES_TTL_S: int = 600
SHOPIFY_ORDERS_TTL_S: int = 300


# ---------------------------------------------------------------------------
# Cache key builders
# ---------------------------------------------------------------------------


def build_stripe_revenue_key(period: str) -> str:
    """Build the Redis key for a Stripe revenue-summary call.

    Args:
        period: Period identifier (e.g. ``"current_month"``, ``"last_3_months"``).

    Returns:
        Redis key of the form ``stripe:revenue_summary:{period}``.
    """
    return f"stripe:revenue_summary:{period}"


def build_stripe_disputes_key(period: str) -> str:
    """Build the Redis key for a Stripe disputes call.

    Args:
        period: Period identifier (e.g. ``"current_month"``).

    Returns:
        Redis key of the form ``stripe:disputes:{period}``.
    """
    return f"stripe:disputes:{period}"


def build_shopify_orders_key(period: str, shop: str | None) -> str:
    """Build the Redis key for a Shopify orders call.

    A missing or empty ``shop`` collapses to ``'default'`` so callers without
    multi-store context still get a stable, namespaced key.

    Args:
        period: Period identifier (e.g. ``"last_30_days"``).
        shop: Shop identifier, or ``None`` when no multi-store context exists.

    Returns:
        Redis key of the form ``shopify:orders:{period}:{shop}``.
    """
    shop_segment = shop.strip() if isinstance(shop, str) else ""
    if not shop_segment:
        shop_segment = "default"
    return f"shopify:orders:{period}:{shop_segment}"


# ---------------------------------------------------------------------------
# Internal cache I/O — patched in unit tests via the module-level names
# ---------------------------------------------------------------------------


async def _cache_get(cache_key: str) -> Any | None:
    """Pull a value from the cache, stripping the set_with_age envelope.

    Returns:
        The stored value on hit, or ``None`` on miss / Redis failure.
    """
    try:
        cache = get_cache_service()
        value, _age_seconds = await cache.get_with_age(cache_key)
    except Exception as exc:  # pragma: no cover -- get_with_age is itself defensive
        logger.debug("financial cache: get failed for %s: %s", cache_key, exc)
        return None
    return value


async def _cache_set(cache_key: str, value: Any, ttl_seconds: int) -> None:
    """Write a value into the cache with an age-trackable envelope.

    We use ``set_with_age`` (not the plain ``set``) so that the matching
    ``should_call_external`` / ``get_with_age`` consumer can compute the age
    of the cached value. A plain ``set`` would silently break the freshness
    check — ``get_with_age`` would return ``(value, None)`` on the next call,
    and ``should_call_external`` would then return ``verdict='miss'`` forever.
    See ``app/services/cohort_analysis_service.py`` for the canonical
    set_with_age / get_with_age pairing in production code.

    Args:
        cache_key: Redis key (already namespaced by the caller).
        value: Any JSON-serializable payload to cache.
        ttl_seconds: Time-to-live for the cached entry, in seconds.
    """
    cache = get_cache_service()
    await cache.set_with_age(cache_key, value, ttl=ttl_seconds)


# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------


async def cached_external_call(
    *,
    cache_key: str,
    ttl_seconds: int,
    fetcher: Callable[[], Awaitable[Any]],
    metric_tag: str,
) -> tuple[Any, bool]:
    """Consult the Redis-tier cache, fetch upstream on miss, cache the result.

    Flow:
        1. Ask ``should_call_external`` whether we have a fresh-enough value.
        2. On verdict='fresh', read the value via ``_cache_get`` and return it.
           If that read races and comes back ``None``, fall through to the
           fetcher (do not return a None payload as if it were a hit).
        3. On verdict in {'stale','miss'} (or after a stale 'fresh' race),
           await the fetcher, best-effort ``_cache_set`` the result, and
           return ``(payload, hit=False)``.

    Cache-write failures are swallowed (logged at debug) so the caller still
    gets the fresh payload.

    Args:
        cache_key: Fully-built Redis key.
        ttl_seconds: Freshness threshold for the Redis-tier decision, in seconds.
        fetcher: Async no-arg callable returning the upstream payload.
        metric_tag: Short label used in log messages (eg. ``"stripe_revenue_summary"``).

    Returns:
        Tuple of ``(payload, cache_hit)`` where ``cache_hit`` is ``True`` only
        when the payload came from the cache without calling ``fetcher``.
    """
    decision = await should_call_external(
        cache_key=cache_key,
        ttl_seconds=ttl_seconds,
    )

    if decision.verdict == "fresh":
        cached = await _cache_get(cache_key)
        if cached is not None:
            logger.debug(
                "financial cache HIT [%s] key=%s age_h=%.4f",
                metric_tag,
                cache_key,
                decision.freshness_hours or 0.0,
            )
            return cached, True
        # Race: should_call_external said 'fresh' but the value vanished
        # between the freshness check and the read. Fall through to fetcher.
        logger.debug(
            "financial cache RACE [%s] key=%s fresh verdict but _cache_get returned None",
            metric_tag,
            cache_key,
        )

    # Cache miss / stale / race — go upstream.
    payload = await fetcher()

    try:
        await _cache_set(cache_key, payload, ttl_seconds)
    except Exception as exc:
        logger.debug(
            "financial cache: set failed for %s (%s): %s",
            cache_key,
            metric_tag,
            exc,
        )

    logger.debug(
        "financial cache MISS [%s] key=%s verdict=%s",
        metric_tag,
        cache_key,
        decision.verdict,
    )
    return payload, False


__all__ = [
    "SHOPIFY_ORDERS_TTL_S",
    "STRIPE_DISPUTES_TTL_S",
    "STRIPE_REVENUE_TTL_S",
    "build_shopify_orders_key",
    "build_stripe_disputes_key",
    "build_stripe_revenue_key",
    "cached_external_call",
]
