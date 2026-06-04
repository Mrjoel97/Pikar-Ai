# Financial Agent claim-type vocabulary

**Phase:** 114-03 · **Status:** Active

This document is the canonical reference for `kg_findings.claim_type` values
emitted by the Financial Agent. Other phases (Plan 121 Strategic,
`/admin/research/overview`, the cross-agent semantic search ADK tool) read
this vocabulary verbatim.

## Active claim types

| `claim_type` | Cardinality | `embed` | `expires_at` | Description |
|---|---|---|---|---|
| `revenue_trend` | one per (entity, period) | true | none | Directional revenue assertion ("Q1 revenue trended +12% MoM"). |
| `expense_pattern` | one per (category, period) | true | none | Category-level expense insight ("Payroll is 38% of monthly spend"). |
| `revenue_forecast_h1m` | one per (entity, generated_at) | true | now + 1 month | 1-month revenue forecast. Expires when stale. |
| `revenue_forecast_h3m` | one per (entity, generated_at) | true | now + 3 months | 3-month revenue forecast. |
| `revenue_forecast_h6m` | one per (entity, generated_at) | true | now + 6 months | 6-month revenue forecast. |
| `revenue_forecast_h12m` | one per (entity, generated_at) | true | now + 12 months | 12-month revenue forecast. |
| `margin_signal` | one per (entity, period) | true | none | Margin assertion ("Gross margin held at 64%"). |
| `financial_anomaly` | one per detection | true | none | Anomaly flag (sigma > 2 OR confidence band downgrade). |
| `reconciliation_finding` | one per material reconciliation | true | none | MATERIAL reconciliation result (residual >= 1% of cash OR >= $1000). |

## NOT claims (explicit rejection list)

| Output | Why not a claim | Where it lives |
|---|---|---|
| Period revenue total ("MRR = $48,234") | Transient aggregation; no epistemic content. | Redis only (`stripe:revenue_summary:{period}` per Plan 114-02). |
| Ad-hoc SQL / aggregation answer | Single-call response; not a recallable assertion. | Response payload only. |

## Entity-resolution convention

`canonical_name` patterns for `kg_entities`:
- Period-keyed metrics: `financial_<metric>_<period>` (e.g.,
  `financial_revenue_current_month`).
- Category-keyed expenses: `financial_expense_<category>_<period>`.

`entity_type` is always `metric` for Financial. Domains attached to entities
on first-write: `["financial"]`.

## Adding a new claim type (process)

1. PR to this file with the new row in BOTH tables (active + rejection rationale).
2. Update `app/agents/financial/claims.py` with a dedicated `emit_<type>` helper.
3. Update the per-phase MILESTONES line if the new type changes acceptance criteria.

## Cross-references

- Phase 114 spec: `docs/superpowers/specs/2026-05-19-shared-intelligence-infra-114-122-rolling-adoption-design.md`
- Phase 112/113 predecessor: `docs/superpowers/specs/2026-05-18-shared-intelligence-infra-design.md`
- Self-improvement audit: `docs/intelligence/financial-self-improvement-audit.md` (Plan 114-01)
