"""Unit tests for Financial Agent claim emission helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_emit_financial_claim_routes_through_write_claim_with_financial_defaults():
    """The helper passes agent_id='financial' and domain='financial'."""
    from app.agents.financial.claims import emit_financial_claim

    captured = {}

    async def fake_get_or_create_entity(**kwargs):
        captured["entity_args"] = kwargs
        return uuid4()

    async def fake_write_claim(**kwargs):
        captured["write_args"] = kwargs
        return uuid4()

    with (
        patch(
            "app.agents.financial.claims.get_or_create_entity",
            new=fake_get_or_create_entity,
        ),
        patch(
            "app.agents.financial.claims.write_claim",
            new=fake_write_claim,
        ),
    ):
        result = await emit_financial_claim(
            canonical_name="financial_revenue_current_month",
            claim_type="revenue_trend",
            finding_text="Revenue trended +12% MoM in current month.",
            confidence=0.82,
            sources=[{"kind": "stripe_row", "ref": "agg/cm"}],
        )

    assert result is not None
    assert (
        captured["entity_args"]["canonical_name"] == "financial_revenue_current_month"
    )
    assert captured["entity_args"]["entity_type"] == "metric"
    assert "financial" in captured["entity_args"]["domains"]
    assert captured["write_args"]["agent_id"] == "financial"
    assert captured["write_args"]["domain"] == "financial"
    assert captured["write_args"]["claim_type"] == "revenue_trend"
    assert captured["write_args"]["embed"] is True


@pytest.mark.asyncio
async def test_emit_financial_claim_returns_none_on_failure():
    """Best-effort: write failure logs and returns None, does not raise."""
    from app.agents.financial.claims import emit_financial_claim

    with patch(
        "app.agents.financial.claims.get_or_create_entity",
        new=AsyncMock(side_effect=RuntimeError("supabase down")),
    ):
        result = await emit_financial_claim(
            canonical_name="x",
            claim_type="revenue_trend",
            finding_text="x" * 30,
            confidence=0.5,
            sources=[],
        )
    assert result is None


@pytest.mark.asyncio
async def test_emit_revenue_forecast_sets_expires_at_per_horizon():
    """revenue_forecast_h6m claim has expires_at ~6 months ahead."""
    from app.agents.financial.claims import emit_revenue_forecast

    captured = {}

    async def fake_write_claim(**kwargs):
        captured.update(kwargs)
        return uuid4()

    with (
        patch(
            "app.agents.financial.claims.get_or_create_entity",
            new=AsyncMock(return_value=uuid4()),
        ),
        patch(
            "app.agents.financial.claims.write_claim",
            new=fake_write_claim,
        ),
    ):
        before = datetime.now(timezone.utc)
        await emit_revenue_forecast(
            months_ahead=6,
            finding_text="Forecast: revenue grows 5% / month for next 6 months.",
            confidence=0.6,
            sources=[{"kind": "stripe_row", "ref": "fc/6m"}],
        )
        after = datetime.now(timezone.utc)

    assert captured["claim_type"] == "revenue_forecast_h6m"
    expires_at = captured["expires_at"]
    assert isinstance(expires_at, datetime)
    # Should be ~6 months ahead (we use 30 * N days as a stable approximation)
    expected_low = before + timedelta(days=30 * 6 - 1)
    expected_high = after + timedelta(days=30 * 6 + 1)
    assert expected_low <= expires_at <= expected_high


@pytest.mark.asyncio
async def test_emit_revenue_forecast_horizon_string_is_unpadded():
    """h1m, h3m, h12m — never h01m or h03m (regression guard for downstream greps)."""
    from app.agents.financial.claims import emit_revenue_forecast

    captured_types = []

    async def fake_write_claim(**kwargs):
        captured_types.append(kwargs["claim_type"])
        return uuid4()

    with (
        patch(
            "app.agents.financial.claims.get_or_create_entity",
            new=AsyncMock(return_value=uuid4()),
        ),
        patch(
            "app.agents.financial.claims.write_claim",
            new=fake_write_claim,
        ),
    ):
        for n in [1, 3, 6, 12]:
            await emit_revenue_forecast(
                months_ahead=n,
                finding_text="x" * 30,
                confidence=0.5,
                sources=[],
            )

    assert captured_types == [
        "revenue_forecast_h1m",
        "revenue_forecast_h3m",
        "revenue_forecast_h6m",
        "revenue_forecast_h12m",
    ]


@pytest.mark.asyncio
async def test_reconciliation_finding_skips_immaterial():
    """Below the material threshold, emit_reconciliation_finding returns None without writing."""
    from app.agents.financial.claims import emit_reconciliation_finding

    write_mock = AsyncMock()
    with (
        patch(
            "app.agents.financial.claims.write_claim",
            new=write_mock,
        ),
        patch(
            "app.agents.financial.claims.get_or_create_entity",
            new=AsyncMock(return_value=uuid4()),
        ),
    ):
        result = await emit_reconciliation_finding(
            period="current_month",
            residual=5.0,  # tiny
            cash_position=10000.0,  # 0.05% — immaterial
            finding_text="x" * 30,
            confidence=0.9,
            sources=[],
        )

    assert result is None
    write_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_reconciliation_finding_writes_on_material_residual():
    """Above threshold (>=1% of cash OR >= $1000), the claim is written."""
    from app.agents.financial.claims import emit_reconciliation_finding

    write_mock = AsyncMock(return_value=uuid4())
    with (
        patch(
            "app.agents.financial.claims.write_claim",
            new=write_mock,
        ),
        patch(
            "app.agents.financial.claims.get_or_create_entity",
            new=AsyncMock(return_value=uuid4()),
        ),
    ):
        result = await emit_reconciliation_finding(
            period="current_month",
            residual=250.0,
            cash_position=10000.0,  # 2.5% — material
            finding_text="Reconciliation drift of $250 in current_month.",
            confidence=0.7,
            sources=[],
        )

    assert result is not None
    write_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_emit_helpers_use_correct_claim_type_strings():
    """One sanity test: every emitter writes the EXACT vocabulary string."""
    from app.agents.financial.claims import (
        emit_expense_pattern,
        emit_financial_anomaly,
        emit_margin_signal,
        emit_revenue_trend,
    )

    seen = []

    async def fake_write_claim(**kwargs):
        seen.append(kwargs["claim_type"])
        return uuid4()

    common = {
        "finding_text": "x" * 30,
        "confidence": 0.6,
        "sources": [],
    }

    with (
        patch(
            "app.agents.financial.claims.get_or_create_entity",
            new=AsyncMock(return_value=uuid4()),
        ),
        patch(
            "app.agents.financial.claims.write_claim",
            new=fake_write_claim,
        ),
    ):
        await emit_revenue_trend(period="current_month", **common)
        await emit_expense_pattern(category="payroll", period="current_month", **common)
        await emit_margin_signal(period="current_month", **common)
        await emit_financial_anomaly(probe="revenue_dip", **common)

    assert seen == [
        "revenue_trend",
        "expense_pattern",
        "margin_signal",
        "financial_anomaly",
    ]


@pytest.mark.asyncio
async def test_get_revenue_stats_emits_revenue_trend_after_recompute():
    """When the graph tier misses, get_revenue_stats emits a revenue_trend claim."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.agents.financial.tools import get_revenue_stats
    from app.services.intelligence.schemas import CacheDecision

    fake_svc = MagicMock()
    fake_svc.get_revenue_stats = AsyncMock(
        return_value={
            "revenue": 12345.0,
            "currency": "USD",
            "transaction_count": 80,
            "source_breakdown": {"stripe": 80},
        }
    )
    emit_mock = AsyncMock(return_value=uuid4())

    with (
        patch(
            "app.agents.financial.tools.get_or_create_entity",
            new=AsyncMock(return_value=uuid4()),
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
            return_value=fake_svc,
        ),
        patch(
            "app.agents.financial.tools.emit_revenue_trend",
            new=emit_mock,
        ),
    ):
        result = await get_revenue_stats(
            period="current_month",
            prefer_graph=True,
        )

    assert result["success"] is True
    emit_mock.assert_awaited_once()
    kwargs = emit_mock.await_args.kwargs
    assert kwargs["period"] == "current_month"
    assert kwargs["confidence"] == result["confidence"]


@pytest.mark.asyncio
async def test_get_revenue_stats_skips_emit_on_graph_hit():
    """Graph-tier hit means no recompute, so no new claim is written."""
    from unittest.mock import AsyncMock, patch

    from app.agents.financial.tools import get_revenue_stats
    from app.services.intelligence.schemas import CacheDecision, Claim, ClaimSource

    entity = uuid4()
    fake_claim = Claim(
        id=uuid4(),
        entity_id=entity,
        edge_id=None,
        agent_id="financial",
        claim_type="revenue_trend",
        domain="financial",
        finding_text="Cached: revenue trended +12% MoM.",
        confidence=0.82,
        sources=[ClaimSource(kind="stripe_row", ref="cache")],
        contradicts=[],
        freshness_at=datetime.now(timezone.utc),
        expires_at=None,
        created_at=datetime.now(timezone.utc),
    )
    emit_mock = AsyncMock()

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
                    freshness_hours=1.0,
                )
            ),
        ),
        patch(
            "app.agents.financial.tools.find_claims",
            new=AsyncMock(return_value=[fake_claim]),
        ),
        patch(
            "app.agents.financial.tools.emit_revenue_trend",
            new=emit_mock,
        ),
    ):
        result = await get_revenue_stats(
            period="current_month",
            prefer_graph=True,
        )

    assert result.get("_source") == "graph_cache"
    emit_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_generate_financial_forecast_emits_revenue_forecast_with_correct_horizon():
    """Forecast call emits revenue_forecast_h{N}m matching months_ahead."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.agents.financial.tools import generate_financial_forecast

    fake_svc = MagicMock()
    fake_svc.generate_forecast = AsyncMock(
        return_value={
            "monthly_projections": [{"month": "2026-06", "revenue": 1000.0}],
            "methodology": "weighted_linear_regression",
            "sample_size": 200,
            "data_completeness": 0.9,
            "source_breakdown": {"stripe": 200},
        }
    )
    emit_mock = AsyncMock(return_value=uuid4())

    with (
        patch(
            "app.services.forecast_service.ForecastService",
            return_value=fake_svc,
        ),
        patch(
            "app.agents.financial.tools._get_current_user_id",
            return_value="user-abc",
        ),
        patch(
            "app.agents.financial.tools.emit_revenue_forecast",
            new=emit_mock,
        ),
    ):
        result = await generate_financial_forecast(months_ahead=3)

    assert result["success"] is True
    emit_mock.assert_awaited_once()
    assert emit_mock.await_args.kwargs["months_ahead"] == 3


@pytest.mark.asyncio
async def test_get_cash_position_emits_expense_pattern_when_reconciliation_clean():
    """Clean cash reconciliation emits one category-level expense_pattern."""
    from unittest.mock import AsyncMock, patch

    from app.agents.financial.tools import get_cash_position

    emit_mock = AsyncMock(return_value=uuid4())

    with (
        patch(
            "app.agents.financial.tools._query_financial_records",
            new=AsyncMock(
                return_value=[
                    {
                        "amount": 1000.0,
                        "transaction_type": "revenue",
                        "currency": "USD",
                    },
                    {"amount": 300.0, "transaction_type": "payroll", "currency": "USD"},
                    {"amount": 100.0, "transaction_type": "expense", "currency": "USD"},
                ]
            ),
        ),
        patch(
            "app.agents.financial.tools._get_current_user_id",
            return_value="user-abc",
        ),
        patch(
            "app.agents.financial.tools.emit_expense_pattern",
            new=emit_mock,
        ),
    ):
        result = await get_cash_position()

    assert result["success"] is True
    emit_mock.assert_awaited_once()
    kwargs = emit_mock.await_args.kwargs
    assert kwargs["category"] == "payroll"
    assert kwargs["period"] == "current_month"
    assert kwargs["confidence"] == result["confidence"]


@pytest.mark.asyncio
async def test_emit_failure_does_not_break_user_response():
    """If emit_revenue_trend raises, the user response still surfaces revenue."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.agents.financial.tools import get_revenue_stats
    from app.services.intelligence.schemas import CacheDecision

    fake_svc = MagicMock()
    fake_svc.get_revenue_stats = AsyncMock(
        return_value={
            "revenue": 999.0,
            "currency": "USD",
            "transaction_count": 5,
            "source_breakdown": {"stripe": 5},
        }
    )

    with (
        patch(
            "app.agents.financial.tools.get_or_create_entity",
            new=AsyncMock(return_value=uuid4()),
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
            return_value=fake_svc,
        ),
        patch(
            "app.agents.financial.tools.emit_revenue_trend",
            new=AsyncMock(side_effect=RuntimeError("write failed")),
        ),
    ):
        result = await get_revenue_stats(
            period="current_month",
            prefer_graph=True,
        )

    assert result["success"] is True
    assert result["revenue"] == 999.0
