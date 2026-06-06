# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Context assembly primitives for agent prompt injection."""

from app.services.context_engine.engine import ContextEngine
from app.services.context_engine.loaders import (
    StructuredMemoryFact,
    load_structured_memory_facts,
    load_structured_memory_facts_sync,
    select_structured_memory_facts_for_prompt,
)
from app.services.context_engine.models import ContextBlock, ContextPacket
from app.services.context_engine.writer import (
    infer_user_memory_fact_write_policy,
    normalize_user_memory_fact_payload,
    upsert_user_memory_fact,
    upsert_user_memory_fact_sync,
)

__all__ = [
    "ContextBlock",
    "ContextEngine",
    "ContextPacket",
    "StructuredMemoryFact",
    "load_structured_memory_facts",
    "load_structured_memory_facts_sync",
    "select_structured_memory_facts_for_prompt",
    "infer_user_memory_fact_write_policy",
    "normalize_user_memory_fact_payload",
    "upsert_user_memory_fact",
    "upsert_user_memory_fact_sync",
]
