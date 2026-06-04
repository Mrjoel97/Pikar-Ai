"""Spec acceptance: semantic search interleaves Financial + peer agent claims."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not all(
            os.environ.get(var)
            for var in [
                "SUPABASE_URL",
                "SUPABASE_SERVICE_ROLE_KEY",
                "SUPABASE_DB_URL",
            ]
        ),
        reason="Supabase / pgvector env not set",
    ),
]


@pytest.mark.asyncio
async def test_q1_revenue_query_returns_all_three_agents():
    """Seed one claim per agent; top_k=10 returns Financial and a peer agent."""
    from app.agents.financial.claims import emit_revenue_trend
    from app.services.intelligence import (
        get_or_create_entity,
        search_claims_semantic,
        write_claim,
    )

    suffix = uuid4().hex[:8]

    await emit_revenue_trend(
        period=f"q1_{suffix}",
        finding_text=(
            "Q1 revenue grew 12 percent month-over-month at our company "
            "driven by enterprise contract expansion."
        ),
        confidence=0.82,
        sources=[{"kind": "stripe_row", "ref": f"q1/{suffix}"}],
    )

    data_entity = await get_or_create_entity(
        canonical_name=f"q1_data_{suffix}",
        entity_type="metric",
        domains=["data"],
    )
    await write_claim(
        entity_id=data_entity,
        domain="data",
        finding_text=(
            "Q1 cohort retention held at 71 percent across enterprise customers, "
            "supporting the revenue growth observed."
        ),
        confidence=0.78,
        sources=[{"kind": "supabase_row", "ref": f"cohort/{suffix}"}],
        agent_id="data",
        claim_type="cohort_retention_m1",
        embed=True,
    )

    research_entity = await get_or_create_entity(
        canonical_name=f"q1_research_{suffix}",
        entity_type="metric",
        domains=["research"],
    )
    await write_claim(
        entity_id=research_entity,
        domain="research",
        finding_text=(
            "Industry Q1 revenue benchmark averaged 9 percent growth across "
            "comparable SaaS providers per public filings."
        ),
        confidence=0.7,
        sources=[{"kind": "url", "ref": f"https://example.com/q1/{suffix}"}],
        agent_id="research",
        claim_type="research_finding",
        embed=True,
    )

    results = await search_claims_semantic(query="Q1 revenue", top_k=10)
    agent_ids = {claim.agent_id for claim, _ in results}

    assert "financial" in agent_ids, (
        f"Financial claim missing from top-10 agents: {agent_ids}"
    )
    assert len(agent_ids) >= 2, (
        f"Expected interleaved results across agents; got only: {agent_ids}"
    )
