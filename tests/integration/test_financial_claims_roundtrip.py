"""Integration: Financial claim types write and read back via find_claims."""

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
async def test_revenue_trend_roundtrip():
    """write_claim via emit_revenue_trend; find_claims returns it."""
    from app.agents.financial.claims import emit_revenue_trend
    from app.services.intelligence import find_claims, get_or_create_entity

    period = f"rt_{uuid4().hex[:8]}"
    claim_id = await emit_revenue_trend(
        period=period,
        finding_text=f"Revenue trend test {period}: +5% MoM observed.",
        confidence=0.75,
        sources=[{"kind": "stripe_row", "ref": f"rt/{period}"}],
    )
    assert claim_id is not None

    entity = await get_or_create_entity(
        canonical_name=f"financial_revenue_{period}",
        entity_type="metric",
        domains=["financial"],
    )
    claims = await find_claims(
        entity_id=entity,
        claim_type="revenue_trend",
        limit=5,
    )
    assert any(c.id == claim_id for c in claims)


@pytest.mark.asyncio
async def test_revenue_forecast_expires_at_set():
    """emit_revenue_forecast sets expires_at; round-trip preserves it."""
    from app.agents.financial.claims import emit_revenue_forecast
    from app.services.intelligence import find_claims, get_or_create_entity

    claim_id = await emit_revenue_forecast(
        months_ahead=6,
        finding_text=(
            "Forecast h6m: revenue projected to grow 5% / month over the next "
            "six months based on weighted regression."
        ),
        confidence=0.55,
        sources=[{"kind": "stripe_row", "ref": "fc/h6m"}],
    )
    assert claim_id is not None

    entity = await get_or_create_entity(
        canonical_name="financial_revenue_forecast_h6m",
        entity_type="metric",
        domains=["financial"],
    )
    claims = await find_claims(
        entity_id=entity,
        claim_type="revenue_forecast_h6m",
        limit=5,
    )
    target = next((c for c in claims if c.id == claim_id), None)
    assert target is not None
    assert target.expires_at is not None


@pytest.mark.asyncio
async def test_material_reconciliation_emitted_immaterial_not():
    """Material residual writes; immaterial residual returns None."""
    from app.agents.financial.claims import emit_reconciliation_finding

    immaterial = await emit_reconciliation_finding(
        period=f"rec_imm_{uuid4().hex[:6]}",
        residual=2.0,
        cash_position=10000.0,
        finding_text="Immaterial residual probe.",
        confidence=0.9,
        sources=[],
    )
    assert immaterial is None

    material = await emit_reconciliation_finding(
        period=f"rec_mat_{uuid4().hex[:6]}",
        residual=250.0,
        cash_position=10000.0,
        finding_text="Material reconciliation drift of $250.",
        confidence=0.9,
        sources=[{"kind": "supabase_row", "ref": "rec/material"}],
    )
    assert material is not None
