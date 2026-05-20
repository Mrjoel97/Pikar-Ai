"""Graph-tier acceptance: repeated revenue_trend queries hit >=60% within 24h."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not all(
            os.environ.get(var) for var in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
        ),
        reason="Supabase env not set",
    ),
]


@pytest.mark.asyncio
async def test_repeated_revenue_trend_query_graph_hit_rate_at_least_60_pct():
    """Seed a fresh revenue_trend claim; repeated reads must hit graph tier.

    Uses prefer_graph=True so get_revenue_stats consults kg_findings instead
    of going straight to FinancialService. Without prefer_graph=True the
    graph block is skipped entirely by design (callers that need numeric
    `revenue`/`currency` keys must default to False).
    """
    from app.agents.financial.tools import get_revenue_stats
    from app.services.intelligence import (
        get_or_create_entity,
        write_claim,
    )

    period = f"loadtest_{uuid4().hex[:8]}"

    # Seed: create the entity + a revenue_trend claim.
    entity = await get_or_create_entity(
        canonical_name=f"financial_revenue_{period}",
        entity_type="metric",
        domains=["financial"],
    )
    await write_claim(
        entity_id=entity,
        domain="financial",
        finding_text="Synthetic revenue trended +5% MoM for load testing.",
        confidence=0.78,
        sources=[{"kind": "stripe_row", "ref": "load-test"}],
        agent_id="financial",
        claim_type="revenue_trend",
        embed=False,
    )

    # 50 repeated calls -- each should detect the fresh graph claim and
    # return the _source='graph_cache' marker.
    hits = 0
    total = 50
    for _ in range(total):
        result = await get_revenue_stats(period=period, prefer_graph=True)
        if result.get("_source") == "graph_cache":
            hits += 1

    hit_rate = hits / total
    print(f"graph_tier hits={hits}/{total} rate={hit_rate:.2%}")
    assert hit_rate >= 0.60, f"Graph-tier hit rate {hit_rate:.2%} below 60% target."
