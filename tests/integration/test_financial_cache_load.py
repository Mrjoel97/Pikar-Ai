"""Synthetic load test: Stripe call rate reduction with two-tier cache.

Acceptance: >= 40% reduction in upstream Stripe fetcher calls when running
1000 requests over a small set of unique periods.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.skipif(
        not all(
            os.environ.get(var) for var in ["REDIS_HOST", "REDIS_PORT"]
        ),
        reason="Redis env not set",
    ),
]


@pytest.mark.asyncio
async def test_stripe_call_rate_reduced_by_at_least_40_pct():
    """1000 requests, 7 unique periods: caching cuts fetcher calls by >=40%."""
    import random

    from app.agents.tools.stripe_tools import get_stripe_revenue_summary

    periods = [
        "current_month", "last_month", "last_3_months", "last_6_months",
        "last_year", "all_time", "current_month",  # weight 'current_month' a bit higher
    ]

    call_count = {"n": 0}

    async def fake_fetcher(*, user_id, period):
        call_count["n"] += 1
        return {
            "total_revenue": 1234.5,
            "transaction_count": 10,
            "period": period,
            "avg_transaction_value": 123.45,
            "currency": "USD",
        }

    rng = random.Random(42)

    with patch(
        "app.agents.tools.stripe_tools._fetch_stripe_revenue_summary_uncached",
        side_effect=fake_fetcher,
    ), patch(
        "app.agents.tools.stripe_tools._get_user_id",
        return_value="user-load",
    ):
        for _ in range(1000):
            await get_stripe_revenue_summary(period=rng.choice(periods))

    # Baseline (no cache) would be 1000 fetcher calls.
    reduction = 1.0 - (call_count["n"] / 1000.0)
    print(f"fetcher_calls={call_count['n']} reduction={reduction:.2%}")
    assert reduction >= 0.40, (
        f"Cache only reduced fetcher calls by {reduction:.2%}; "
        f"target >=40% (1000 reqs, {len(set(periods))} unique periods)."
    )
