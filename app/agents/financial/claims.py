"""Financial Agent claim emission helpers.

Best-effort wrappers over `app.services.intelligence.write_claim` that
encode the Plan 114-03 claim-type vocabulary and Financial-Agent defaults
(agent_id='financial', domain='financial'). Every helper returns the new
claim UUID on success or None on failure -- callers must never crash a
user-facing response because a graph write failed.

The canonical vocabulary lives in
`docs/intelligence/financial-claim-vocabulary.md`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.services.intelligence import get_or_create_entity, write_claim

logger = logging.getLogger(__name__)

CLAIM_TYPE_REVENUE_TREND = "revenue_trend"
CLAIM_TYPE_EXPENSE_PATTERN = "expense_pattern"
CLAIM_TYPE_MARGIN_SIGNAL = "margin_signal"
CLAIM_TYPE_FINANCIAL_ANOMALY = "financial_anomaly"
CLAIM_TYPE_RECONCILIATION_FINDING = "reconciliation_finding"

_MATERIAL_PCT = 0.01
_MATERIAL_ABS = 1000.0


def revenue_forecast_claim_type(months_ahead: int) -> str:
    """Return the canonical `revenue_forecast_h{N}m` string."""
    return f"revenue_forecast_h{int(months_ahead)}m"


async def emit_financial_claim(
    *,
    canonical_name: str,
    entity_type: str = "metric",
    claim_type: str,
    finding_text: str,
    confidence: float,
    sources: list[dict],
    expires_at: datetime | None = None,
    embed: bool = True,
) -> UUID | None:
    """Best-effort write to kg_findings with Financial-Agent defaults."""
    try:
        entity_id = await get_or_create_entity(
            canonical_name=canonical_name,
            entity_type=entity_type,
            domains=["financial"],
        )
        return await write_claim(
            entity_id=entity_id,
            domain="financial",
            finding_text=finding_text,
            confidence=confidence,
            sources=sources,
            agent_id="financial",
            claim_type=claim_type,
            embed=embed,
            expires_at=expires_at,
        )
    except Exception as e:
        logger.warning(
            "emit_financial_claim failed (canonical_name=%s, claim_type=%s): %s",
            canonical_name,
            claim_type,
            e,
        )
        return None


async def emit_revenue_trend(
    *,
    period: str,
    finding_text: str,
    confidence: float,
    sources: list[dict],
) -> UUID | None:
    """Emit a `revenue_trend` claim for the given period."""
    return await emit_financial_claim(
        canonical_name=f"financial_revenue_{period}",
        claim_type=CLAIM_TYPE_REVENUE_TREND,
        finding_text=finding_text,
        confidence=confidence,
        sources=sources,
    )


async def emit_expense_pattern(
    *,
    category: str,
    period: str,
    finding_text: str,
    confidence: float,
    sources: list[dict],
) -> UUID | None:
    """Emit an `expense_pattern` claim for a category and period."""
    safe_category = category.strip().lower() or "uncategorized"
    return await emit_financial_claim(
        canonical_name=f"financial_expense_{safe_category}_{period}",
        claim_type=CLAIM_TYPE_EXPENSE_PATTERN,
        finding_text=finding_text,
        confidence=confidence,
        sources=sources,
    )


async def emit_margin_signal(
    *,
    period: str,
    finding_text: str,
    confidence: float,
    sources: list[dict],
) -> UUID | None:
    """Emit a `margin_signal` claim for the given period."""
    return await emit_financial_claim(
        canonical_name=f"financial_margin_{period}",
        claim_type=CLAIM_TYPE_MARGIN_SIGNAL,
        finding_text=finding_text,
        confidence=confidence,
        sources=sources,
    )


async def emit_financial_anomaly(
    *,
    probe: str,
    finding_text: str,
    confidence: float,
    sources: list[dict],
) -> UUID | None:
    """Emit a `financial_anomaly` claim identified by a detector probe name."""
    safe_probe = probe.strip().lower() or "unspecified"
    return await emit_financial_claim(
        canonical_name=f"financial_anomaly_{safe_probe}",
        claim_type=CLAIM_TYPE_FINANCIAL_ANOMALY,
        finding_text=finding_text,
        confidence=confidence,
        sources=sources,
    )


async def emit_revenue_forecast(
    *,
    months_ahead: int,
    finding_text: str,
    confidence: float,
    sources: list[dict],
) -> UUID | None:
    """Emit a `revenue_forecast_h{N}m` claim with a horizon expiry."""
    if months_ahead <= 0:
        logger.warning(
            "emit_revenue_forecast skipped: months_ahead must be > 0, got %s",
            months_ahead,
        )
        return None

    expires_at = datetime.now(timezone.utc) + timedelta(days=30 * months_ahead)
    return await emit_financial_claim(
        canonical_name=f"financial_revenue_forecast_h{int(months_ahead)}m",
        claim_type=revenue_forecast_claim_type(months_ahead),
        finding_text=finding_text,
        confidence=confidence,
        sources=sources,
        expires_at=expires_at,
    )


def _is_material(residual: float, cash_position: float) -> bool:
    """Return whether a reconciliation residual meets the materiality rule."""
    abs_residual = abs(float(residual))
    if abs_residual >= _MATERIAL_ABS:
        return True
    base = max(1.0, abs(float(cash_position)))
    return (abs_residual / base) >= _MATERIAL_PCT


async def emit_reconciliation_finding(
    *,
    period: str,
    residual: float,
    cash_position: float,
    finding_text: str,
    confidence: float,
    sources: list[dict],
) -> UUID | None:
    """Emit `reconciliation_finding` only when residual is material."""
    if not _is_material(residual=residual, cash_position=cash_position):
        return None
    return await emit_financial_claim(
        canonical_name=f"financial_reconciliation_{period}",
        claim_type=CLAIM_TYPE_RECONCILIATION_FINDING,
        finding_text=finding_text,
        confidence=confidence,
        sources=sources,
    )


__all__ = [
    "CLAIM_TYPE_EXPENSE_PATTERN",
    "CLAIM_TYPE_FINANCIAL_ANOMALY",
    "CLAIM_TYPE_MARGIN_SIGNAL",
    "CLAIM_TYPE_RECONCILIATION_FINDING",
    "CLAIM_TYPE_REVENUE_TREND",
    "emit_expense_pattern",
    "emit_financial_anomaly",
    "emit_financial_claim",
    "emit_margin_signal",
    "emit_reconciliation_finding",
    "emit_revenue_forecast",
    "emit_revenue_trend",
    "revenue_forecast_claim_type",
]
