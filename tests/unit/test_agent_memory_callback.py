# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for per-agent memory injection inside context_memory_before_model_callback."""

from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

# Stub the google.adk + google.genai surface the same way other unit tests do
# so importing app.agents.context_extractor does not require the real ADK.
sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.agents.callback_context", MagicMock())
sys.modules.setdefault("google.genai", MagicMock())
sys.modules.setdefault("google.genai.types", MagicMock())


def _make_callback_context(user_id: str, agent_name: str) -> MagicMock:
    """Build a CallbackContext-shaped mock with a real dict for state."""
    ctx = MagicMock()
    ctx.state = {"user_id": user_id}
    ctx.agent_name = agent_name
    return ctx


def _make_llm_request_with_user_text(text: str) -> MagicMock:
    """Build an llm_request mock containing one user content turn and a config."""
    part = MagicMock()
    part.text = text
    content = MagicMock()
    content.role = "user"
    content.parts = [part]

    config = MagicMock()
    config.system_instruction = ""

    request = MagicMock()
    request.contents = [content]
    request.config = config
    return request


def test_try_load_agent_memory_injects_facts_block():
    from app.agents import context_extractor

    ctx = _make_callback_context("user-abc", "FinancialAnalysisAgent")
    canned_facts = {"preferred_currency": "USD", "fiscal_year_end": "Dec 31"}

    with patch(
        "app.services.agent_memory.get_agent_memory_sync",
        return_value=canned_facts,
    ):
        block = context_extractor._try_load_agent_memory(ctx)

    assert block, "expected a non-empty block when facts exist"
    assert "[AGENT MEMORY" in block
    assert "FinancialAnalysisAgent" in block
    assert "preferred_currency" in block
    assert "USD" in block
    # The cache key must be set so a second call short-circuits.
    cache_keys = [k for k in ctx.state if k.startswith("_agent_memory_loaded::")]
    assert cache_keys, "loader must cache its result in session state"


def test_try_load_agent_memory_returns_empty_when_no_facts():
    from app.agents import context_extractor

    ctx = _make_callback_context("user-abc", "FinancialAnalysisAgent")

    with patch(
        "app.services.agent_memory.get_agent_memory_sync",
        return_value={},
    ):
        block = context_extractor._try_load_agent_memory(ctx)

    assert block == ""


def test_try_load_agent_memory_caches_per_session():
    from app.agents import context_extractor

    ctx = _make_callback_context("user-abc", "FinancialAnalysisAgent")
    canned_facts = {"x": 1}

    with patch(
        "app.services.agent_memory.get_agent_memory_sync",
        return_value=canned_facts,
    ) as mocked:
        first = context_extractor._try_load_agent_memory(ctx)
        second = context_extractor._try_load_agent_memory(ctx)

    assert first == second
    assert first  # not empty
    # Sync loader must only be hit once per session per agent.
    assert mocked.call_count == 1


def test_try_load_agent_memory_skips_without_user_or_agent():
    from app.agents import context_extractor

    no_user = _make_callback_context("", "FinancialAnalysisAgent")
    no_agent = _make_callback_context("user-abc", "")

    with patch(
        "app.services.agent_memory.get_agent_memory_sync",
        return_value={"x": 1},
    ) as mocked:
        assert context_extractor._try_load_agent_memory(no_user) == ""
        assert context_extractor._try_load_agent_memory(no_agent) == ""
        mocked.assert_not_called()


def test_try_load_agent_memory_swallows_loader_errors():
    from app.agents import context_extractor

    ctx = _make_callback_context("user-abc", "FinancialAnalysisAgent")

    with patch(
        "app.services.agent_memory.get_agent_memory_sync",
        side_effect=RuntimeError("boom"),
    ):
        block = context_extractor._try_load_agent_memory(ctx)

    assert block == ""


def test_before_model_callback_extends_system_instruction_with_agent_memory():
    """End-to-end: the public callback must inject the agent_memory block
    into llm_request.config.system_instruction when facts exist.
    """
    from app.agents import context_extractor

    ctx = _make_callback_context("user-abc", "FinancialAnalysisAgent")
    request = _make_llm_request_with_user_text("hello")

    canned_facts = {"preferred_currency": "USD"}

    with (
        patch(
            "app.services.agent_memory.get_agent_memory_sync",
            return_value=canned_facts,
        ),
        # Avoid touching cross-session vault / brand profile in this test.
        patch.object(context_extractor, "_try_load_cross_session_context"),
        patch.object(context_extractor, "_try_load_brand_profile", return_value=""),
    ):
        result = context_extractor.context_memory_before_model_callback(ctx, request)

    # Callback returns None and mutates the request's system_instruction in place.
    assert result is None
    si = request.config.system_instruction
    assert isinstance(si, str)
    assert "[AGENT MEMORY" in si
    assert "preferred_currency" in si
    assert json.dumps(canned_facts, indent=2)[:20] in si or "USD" in si


def test_try_load_structured_user_memory_formats_and_caches():
    from app.agents import context_extractor
    from app.services.context_engine import StructuredMemoryFact

    ctx = _make_callback_context(
        "11111111-1111-1111-1111-111111111111",
        "FinancialAnalysisAgent",
    )
    facts = [
        StructuredMemoryFact(
            key="preferred_currency",
            value_json={"code": "USD"},
            memory_type="preference",
            scope="global",
            confidence=0.95,
        )
    ]

    with patch.object(
        context_extractor,
        "load_structured_memory_facts_sync",
        return_value=facts,
    ) as mocked:
        first = context_extractor._try_load_structured_user_memory(ctx)
        second = context_extractor._try_load_structured_user_memory(ctx)

    assert first == second
    assert "[STRUCTURED USER MEMORY" in first
    assert "preferred_currency" in first
    assert '"code": "USD"' in first
    assert mocked.call_count == 1
    cache_keys = [k for k in ctx.state if k.startswith("_structured_memory_loaded::")]
    assert cache_keys


def test_before_model_callback_injects_structured_memory_before_legacy_agent_memory():
    from app.agents import context_extractor
    from app.services.context_engine import StructuredMemoryFact

    ctx = _make_callback_context(
        "11111111-1111-1111-1111-111111111111",
        "FinancialAnalysisAgent",
    )
    request = _make_llm_request_with_user_text("hello")

    structured_facts = [
        StructuredMemoryFact(
            key="preferred_currency",
            value_json="USD",
            memory_type="preference",
            scope="global",
        )
    ]

    with (
        patch.object(context_extractor, "_try_load_cross_session_context"),
        patch.object(context_extractor, "_try_load_brand_profile", return_value=""),
        patch.object(
            context_extractor,
            "load_structured_memory_facts_sync",
            return_value=structured_facts,
        ),
        patch(
            "app.services.agent_memory.get_agent_memory_sync",
            return_value={"legacy_fact": True},
        ),
    ):
        result = context_extractor.context_memory_before_model_callback(ctx, request)

    assert result is None
    si = request.config.system_instruction
    assert isinstance(si, str)
    assert "[STRUCTURED USER MEMORY" in si
    assert "[AGENT MEMORY" in si
    assert si.index("[STRUCTURED USER MEMORY") < si.index("[AGENT MEMORY")


def test_after_tool_callback_persists_save_user_context_to_structured_memory():
    from app.agents import context_extractor

    ctx = _make_callback_context(
        "11111111-1111-1111-1111-111111111111",
        "FinancialAnalysisAgent",
    )
    ctx.state["_structured_memory_loaded::FinancialAnalysisAgent"] = "stale"
    tool = MagicMock()
    tool.__name__ = "save_user_context"

    with (
        patch.object(context_extractor, "tool_progress_after_tool_callback"),
        patch.object(
            context_extractor,
            "upsert_user_memory_fact_sync",
            return_value=True,
        ) as upsert,
    ):
        result = context_extractor.context_memory_after_tool_callback(
            tool,
            {},
            ctx,
            {
                "_context_memory_save": True,
                "key": "company_name",
                "value": "Pikar AI",
            },
        )

    assert result == {
        "status": "saved",
        "message": "Remembered: company_name = Pikar AI",
        "total_facts": 1,
    }
    assert ctx.state["user_context"] == {"company_name": "Pikar AI"}
    assert "_structured_memory_loaded::FinancialAnalysisAgent" not in ctx.state
    payload = upsert.call_args.args[0]
    assert payload["user_id"] == "11111111-1111-1111-1111-111111111111"
    assert payload["key"] == "company_name"
    assert payload["value_json"] == "Pikar AI"
    assert payload["source_kind"] == "tool"
    assert payload["source_ref"] == "save_user_context"


def test_after_tool_callback_keeps_session_save_when_structured_memory_fails():
    from app.agents import context_extractor

    ctx = _make_callback_context("user-abc", "FinancialAnalysisAgent")
    tool = MagicMock()
    tool.__name__ = "save_user_context"

    with (
        patch.object(context_extractor, "tool_progress_after_tool_callback"),
        patch.object(
            context_extractor,
            "upsert_user_memory_fact_sync",
            side_effect=RuntimeError("boom"),
        ),
    ):
        result = context_extractor.context_memory_after_tool_callback(
            tool,
            {},
            ctx,
            {
                "_context_memory_save": True,
                "key": "industry",
                "value": "Manufacturing",
            },
        )

    assert result == {
        "status": "saved",
        "message": "Remembered: industry = Manufacturing",
        "total_facts": 1,
    }
    assert ctx.state["user_context"] == {"industry": "Manufacturing"}
