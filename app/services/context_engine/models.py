# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Typed context packet models.

The current ADK callback still owns source-specific loading. These models give
the read-side assembly step a stable contract so source loading, precedence,
and rendering can evolve independently.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContextBlock:
    """A renderable prompt block with ordering metadata."""

    key: str
    content: str
    priority: int
    source: str = "runtime"

    def normalized(self) -> str:
        """Return a value suitable for duplicate detection."""
        return (self.content or "").strip()

    def is_empty(self) -> bool:
        """Return True when the block contributes no prompt content."""
        return not self.normalized()


@dataclass
class ContextPacket:
    """All context assembled for a single model invocation."""

    blocks: list[ContextBlock] = field(default_factory=list)
    root_instruction_override: str | None = None

    def add(
        self,
        key: str,
        content: str,
        *,
        priority: int,
        source: str = "runtime",
    ) -> None:
        """Append a block when ``content`` is non-empty."""
        block = ContextBlock(
            key=key,
            content=content,
            priority=priority,
            source=source,
        )
        if not block.is_empty():
            self.blocks.append(block)

    def ordered_blocks(self) -> list[ContextBlock]:
        """Return blocks in deterministic render order."""
        return sorted(
            (block for block in self.blocks if not block.is_empty()),
            key=lambda block: block.priority,
        )
