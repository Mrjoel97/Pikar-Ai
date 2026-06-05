# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

from app.services.context_engine import ContextEngine, ContextPacket


def test_context_engine_orders_blocks_by_priority_and_dedupes() -> None:
    packet = ContextPacket()
    packet.add("late", "[LATE]", priority=30, source="test")
    packet.add("early", "[EARLY]", priority=10, source="test")
    packet.add("duplicate", "  [EARLY]  ", priority=20, source="test")
    packet.add("empty", "   ", priority=5, source="test")

    rendered = ContextEngine().apply_to_system_instruction(
        existing_instruction="",
        packet=packet,
    )

    assert rendered == "[EARLY][LATE]"


def test_context_engine_skips_blocks_already_in_system_instruction() -> None:
    packet = ContextPacket()
    packet.add("known", "\n[KNOWN]\n", priority=10, source="test")

    rendered = ContextEngine().apply_to_system_instruction(
        existing_instruction="BASE\n[KNOWN]\n",
        packet=packet,
    )

    assert rendered is None


def test_context_engine_appends_new_blocks_to_existing_instruction() -> None:
    packet = ContextPacket()
    packet.add("new", "\n[NEW]\n", priority=10, source="test")

    rendered = ContextEngine().apply_to_system_instruction(
        existing_instruction="BASE",
        packet=packet,
    )

    assert rendered == "BASE\n[NEW]\n"


def test_context_engine_root_override_replaces_base_but_keeps_context() -> None:
    packet = ContextPacket(root_instruction_override="CUSTOM ROOT")
    packet.add("context", "\n[CONTEXT]\n", priority=10, source="test")

    rendered = ContextEngine().apply_to_system_instruction(
        existing_instruction="BASE",
        packet=packet,
    )

    assert rendered == "CUSTOM ROOT\n[CONTEXT]\n"
