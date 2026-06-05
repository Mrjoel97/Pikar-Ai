# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Read-side context packet renderer."""

from __future__ import annotations

from app.services.context_engine.models import ContextBlock, ContextPacket


class ContextEngine:
    """Assemble a deterministic system-instruction addition for one turn."""

    def render_blocks(
        self,
        packet: ContextPacket,
        *,
        existing_instruction: str = "",
    ) -> str:
        """Render packet blocks, skipping duplicates and already-injected blocks."""
        seen: set[str] = set()
        rendered: list[str] = []
        existing = existing_instruction or ""

        for block in packet.ordered_blocks():
            normalized = block.normalized()
            if not normalized or normalized in seen or normalized in existing:
                continue
            seen.add(normalized)
            rendered.append(block.content)

        return "".join(rendered)

    def apply_to_system_instruction(
        self,
        *,
        existing_instruction: str,
        packet: ContextPacket,
    ) -> str | None:
        """Return a new system instruction, or None when no mutation is needed.

        Root overrides intentionally replace the base instruction but still
        receive the context additions for this invocation.
        """
        existing = existing_instruction or ""
        override = (
            packet.root_instruction_override.strip()
            if isinstance(packet.root_instruction_override, str)
            else ""
        )

        if override:
            additions = self.render_blocks(packet)
            return override + additions

        additions = self.render_blocks(packet, existing_instruction=existing)
        if not additions:
            return None

        if existing:
            return existing + additions
        return additions.strip()


__all__ = ["ContextBlock", "ContextEngine", "ContextPacket"]
