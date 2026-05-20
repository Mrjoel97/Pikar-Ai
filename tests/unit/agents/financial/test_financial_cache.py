"""Unit tests for Financial Agent cache adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


def test_stripe_revenue_key_shape_matches_spec():
    """Cache key for Stripe revenue summary must be `stripe:revenue_summary:{period}`."""
    from app.agents.financial.cache import build_stripe_revenue_key

    assert (
        build_stripe_revenue_key("current_month")
        == "stripe:revenue_summary:current_month"
    )
    assert (
        build_stripe_revenue_key("last_3_months")
        == "stripe:revenue_summary:last_3_months"
    )


def test_stripe_disputes_key_shape_matches_spec():
    """Cache key for Stripe disputes must be `stripe:disputes:{period}`."""
    from app.agents.financial.cache import build_stripe_disputes_key

    assert build_stripe_disputes_key("current_month") == "stripe:disputes:current_month"


def test_shopify_orders_key_shape_matches_spec():
    """Cache key for Shopify orders must be `shopify:orders:{period}:{shop}`."""
    from app.agents.financial.cache import build_shopify_orders_key

    assert (
        build_shopify_orders_key("last_30_days", "pikar-store")
        == "shopify:orders:last_30_days:pikar-store"
    )


def test_shopify_orders_key_handles_none_shop():
    """When shop is None / missing, key uses 'default' as the suffix."""
    from app.agents.financial.cache import build_shopify_orders_key

    assert (
        build_shopify_orders_key("last_30_days", None)
        == "shopify:orders:last_30_days:default"
    )


def test_ttl_constants_match_spec():
    """TTLs MUST match the spec exactly."""
    from app.agents.financial.cache import (
        SHOPIFY_ORDERS_TTL_S,
        STRIPE_DISPUTES_TTL_S,
        STRIPE_REVENUE_TTL_S,
    )

    assert STRIPE_REVENUE_TTL_S == 300
    assert STRIPE_DISPUTES_TTL_S == 600
    assert SHOPIFY_ORDERS_TTL_S == 300


@pytest.mark.asyncio
async def test_cached_external_call_returns_cached_on_fresh():
    """When CacheDecision.verdict == 'fresh', skip fetcher and use cached value."""
    from app.agents.financial.cache import cached_external_call
    from app.services.intelligence.schemas import CacheDecision

    fetcher = AsyncMock()
    cache_value = {"revenue": 12345.67}

    with (
        patch(
            "app.agents.financial.cache.should_call_external",
            new=AsyncMock(
                return_value=CacheDecision(
                    tier="redis",
                    verdict="fresh",
                    freshness_hours=0.1,
                )
            ),
        ),
        patch(
            "app.agents.financial.cache._cache_get",
            new=AsyncMock(return_value=cache_value),
        ),
    ):
        payload, hit = await cached_external_call(
            cache_key="stripe:revenue_summary:current_month",
            ttl_seconds=300,
            fetcher=fetcher,
            metric_tag="stripe_revenue_summary",
        )

    assert payload == cache_value
    assert hit is True
    fetcher.assert_not_called()


@pytest.mark.asyncio
async def test_cached_external_call_falls_through_on_miss():
    """When verdict='miss', call the fetcher and cache.set the result."""
    from app.agents.financial.cache import cached_external_call
    from app.services.intelligence.schemas import CacheDecision

    fresh_value = {"revenue": 999.0}
    fetcher = AsyncMock(return_value=fresh_value)
    set_mock = AsyncMock()

    with (
        patch(
            "app.agents.financial.cache.should_call_external",
            new=AsyncMock(
                return_value=CacheDecision(
                    tier="redis",
                    verdict="miss",
                    freshness_hours=None,
                )
            ),
        ),
        patch(
            "app.agents.financial.cache._cache_set",
            new=set_mock,
        ),
    ):
        payload, hit = await cached_external_call(
            cache_key="stripe:revenue_summary:current_month",
            ttl_seconds=300,
            fetcher=fetcher,
            metric_tag="stripe_revenue_summary",
        )

    assert payload == fresh_value
    assert hit is False
    fetcher.assert_awaited_once()
    set_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_cached_external_call_swallows_cache_set_errors():
    """If cache.set fails after a fresh fetch, payload is still returned."""
    from app.agents.financial.cache import cached_external_call
    from app.services.intelligence.schemas import CacheDecision

    fetcher = AsyncMock(return_value={"v": 1})
    failing_set = AsyncMock(side_effect=RuntimeError("redis down"))

    with (
        patch(
            "app.agents.financial.cache.should_call_external",
            new=AsyncMock(
                return_value=CacheDecision(
                    tier="redis",
                    verdict="miss",
                    freshness_hours=None,
                )
            ),
        ),
        patch(
            "app.agents.financial.cache._cache_set",
            new=failing_set,
        ),
    ):
        payload, hit = await cached_external_call(
            cache_key="any:key",
            ttl_seconds=60,
            fetcher=fetcher,
            metric_tag="probe",
        )

    assert payload == {"v": 1}
    assert hit is False  # we did go upstream


@pytest.mark.asyncio
async def test_get_stripe_revenue_summary_hits_cache_on_repeat():
    """Second call within TTL returns the same payload without re-querying."""
    from unittest.mock import AsyncMock, patch

    from app.agents.tools.stripe_tools import get_stripe_revenue_summary

    fake_response = {
        "total_revenue": 1000.0,
        "transaction_count": 5,
        "period": "current_month",
        "avg_transaction_value": 200.0,
        "currency": "USD",
    }

    call_count = {"n": 0}

    async def fake_fetcher(**kwargs):
        call_count["n"] += 1
        return fake_response

    # Simulate Redis fresh on the SECOND call. First call: miss; second: fresh.
    from app.services.intelligence.schemas import CacheDecision

    decisions = iter(
        [
            CacheDecision(tier="redis", verdict="miss", freshness_hours=None),
            CacheDecision(tier="redis", verdict="fresh", freshness_hours=0.05),
        ]
    )

    async def fake_decision(**kw):
        return next(decisions)

    with (
        patch(
            "app.agents.financial.cache.should_call_external",
            new=fake_decision,
        ),
        patch(
            "app.agents.financial.cache._cache_get",
            new=AsyncMock(return_value=fake_response),
        ),
        patch(
            "app.agents.financial.cache._cache_set",
            new=AsyncMock(),
        ),
        patch(
            "app.agents.tools.stripe_tools._fetch_stripe_revenue_summary_uncached",
            side_effect=fake_fetcher,
        ),
        patch(
            "app.agents.tools.stripe_tools._get_user_id",
            return_value="user-abc",
        ),
    ):
        r1 = await get_stripe_revenue_summary(period="current_month")
        r2 = await get_stripe_revenue_summary(period="current_month")

    # `_cache_hit` differs (False on miss, True on hit) -- compare payload bodies.
    assert {k: v for k, v in r1.items() if k != "_cache_hit"} == {
        k: v for k, v in r2.items() if k != "_cache_hit"
    }
    assert r1["_cache_hit"] is False
    assert r2["_cache_hit"] is True
    assert call_count["n"] == 1, "Second call should have hit Redis, not the fetcher"


@pytest.mark.asyncio
async def test_get_shopify_orders_hits_cache_on_repeat():
    """Shopify orders cache: second call within TTL skips upstream."""
    from unittest.mock import AsyncMock, patch

    from app.agents.tools.shopify_tools import get_shopify_orders
    from app.services.intelligence.schemas import CacheDecision

    fake_response = {"orders": [{"id": "o1"}], "count": 1}
    call_count = {"n": 0}

    async def fake_fetcher(**kwargs):
        call_count["n"] += 1
        return fake_response

    decisions = iter(
        [
            CacheDecision(tier="redis", verdict="miss", freshness_hours=None),
            CacheDecision(tier="redis", verdict="fresh", freshness_hours=0.05),
        ]
    )

    async def fake_decision(**kw):
        return next(decisions)

    with (
        patch(
            "app.agents.financial.cache.should_call_external",
            new=fake_decision,
        ),
        patch(
            "app.agents.financial.cache._cache_get",
            new=AsyncMock(return_value=fake_response),
        ),
        patch(
            "app.agents.financial.cache._cache_set",
            new=AsyncMock(),
        ),
        patch(
            "app.agents.tools.shopify_tools._fetch_shopify_orders_uncached",
            side_effect=fake_fetcher,
        ),
        patch(
            "app.agents.tools.shopify_tools._get_user_id",
            return_value="user-abc",
        ),
        patch(
            "app.agents.tools.shopify_tools._get_user_shop_slug",
            return_value="pikar-store",
        ),
    ):
        r1 = await get_shopify_orders(period="last_30_days")
        r2 = await get_shopify_orders(period="last_30_days")

    r1_payload = {k: v for k, v in r1.items() if k != "_cache_hit"}
    r2_payload = {k: v for k, v in r2.items() if k != "_cache_hit"}
    assert r1_payload == r2_payload
    assert r1["_cache_hit"] is False
    assert r2["_cache_hit"] is True
    assert call_count["n"] == 1


@pytest.mark.asyncio
async def test_get_revenue_stats_returns_graph_claim_when_fresh():
    """When a fresh revenue_trend claim exists, skip recompute and return it."""
    from datetime import datetime, timezone
    from unittest.mock import AsyncMock, patch
    from uuid import uuid4

    from app.agents.financial.tools import get_revenue_stats
    from app.services.intelligence.schemas import (
        CacheDecision,
        Claim,
        ClaimSource,
    )

    entity = uuid4()
    fake_claim = Claim(
        id=uuid4(),
        entity_id=entity,
        edge_id=None,
        agent_id="financial",
        claim_type="revenue_trend",
        domain="financial",
        finding_text="Revenue trended +12% MoM in Q1.",
        confidence=0.82,
        sources=[ClaimSource(kind="stripe_row", ref="agg/q1")],
        contradicts=[],
        freshness_at=datetime.now(timezone.utc),
        expires_at=None,
        created_at=datetime.now(timezone.utc),
    )

    with (
        patch(
            "app.agents.financial.tools.get_or_create_entity",
            new=AsyncMock(return_value=entity),
        ),
        patch(
            "app.agents.financial.tools.should_query_graph",
            new=AsyncMock(
                return_value=CacheDecision(
                    tier="graph",
                    verdict="fresh",
                    freshness_hours=2.1,
                )
            ),
        ),
        patch(
            "app.agents.financial.tools.find_claims",
            new=AsyncMock(return_value=[fake_claim]),
        ),
    ):
        result = await get_revenue_stats(period="current_month", prefer_graph=True)

    assert result["success"] is True
    # When the graph short-circuits, surface the claim's narrative + confidence
    assert "Revenue trended" in str(result.get("revenue_trend") or "")
    assert result["confidence"] == pytest.approx(0.82, abs=1e-3)
    assert result.get("_source") == "graph_cache"


@pytest.mark.asyncio
async def test_get_revenue_stats_falls_through_on_stale_or_miss():
    """When verdict='stale' or 'miss', recompute via the existing path."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from uuid import uuid4

    from app.agents.financial.tools import get_revenue_stats
    from app.services.intelligence.schemas import CacheDecision

    entity = uuid4()
    fake_service = MagicMock()
    fake_service.get_revenue_stats = AsyncMock(
        return_value={
            "revenue": 1000.0,
            "currency": "USD",
            "transaction_count": 10,
            "source_breakdown": {"stripe": 10},
        }
    )

    with (
        patch(
            "app.agents.financial.tools.get_or_create_entity",
            new=AsyncMock(return_value=entity),
        ),
        patch(
            "app.agents.financial.tools.should_query_graph",
            new=AsyncMock(
                return_value=CacheDecision(
                    tier="graph",
                    verdict="miss",
                    freshness_hours=None,
                )
            ),
        ),
        patch(
            "app.services.financial_service.FinancialService",
            return_value=fake_service,
        ),
    ):
        result = await get_revenue_stats(period="current_month", prefer_graph=True)

    assert result["success"] is True
    assert result["revenue"] == 1000.0
    assert result.get("_source") != "graph_cache"


@pytest.mark.asyncio
async def test_get_revenue_stats_default_skips_graph_block():
    """Without prefer_graph=True, no graph-tier calls happen even if claims exist."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.agents.financial.tools import get_revenue_stats

    fake_service = MagicMock()
    fake_service.get_revenue_stats = AsyncMock(
        return_value={
            "revenue": 500.0,
            "currency": "USD",
            "transaction_count": 5,
            "source_breakdown": {"stripe": 5},
        }
    )

    should_query = AsyncMock()
    get_entity = AsyncMock()
    find_cl = AsyncMock()

    with (
        patch(
            "app.agents.financial.tools.should_query_graph",
            new=should_query,
        ),
        patch(
            "app.agents.financial.tools.get_or_create_entity",
            new=get_entity,
        ),
        patch(
            "app.agents.financial.tools.find_claims",
            new=find_cl,
        ),
        patch(
            "app.services.financial_service.FinancialService",
            return_value=fake_service,
        ),
    ):
        result = await get_revenue_stats(period="current_month")  # default

    assert result["success"] is True
    assert result["revenue"] == 500.0
    assert result.get("_source") != "graph_cache"
    # Critical: none of the graph helpers should have been called.
    should_query.assert_not_called()
    get_entity.assert_not_called()
    find_cl.assert_not_called()
