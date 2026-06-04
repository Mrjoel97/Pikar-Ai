from __future__ import annotations

import enum
import inspect

from app.agents.tools.base import agent_tool, sanitize_tools


class NumericToolState(enum.IntEnum):
    IDLE = 0
    ACTIVE = 1


def test_agent_tool_serializes_numeric_enum_return_to_string():
    @agent_tool
    def choose_state() -> NumericToolState:
        return NumericToolState.ACTIVE

    assert choose_state() == "active"
    assert choose_state.__annotations__["return"] is str
    assert inspect.signature(choose_state).return_annotation is str


def test_sanitize_tools_deduplicates_by_declaration_name():
    def get_shopify_orders() -> dict:
        return {"source": "full"}

    def duplicate() -> dict:
        return {"source": "subset"}

    duplicate.__name__ = "get_shopify_orders"

    tools = sanitize_tools([get_shopify_orders, duplicate])

    assert [tool.__name__ for tool in tools] == ["get_shopify_orders"]
    assert tools[0]() == {"source": "full"}
