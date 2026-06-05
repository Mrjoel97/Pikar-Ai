---
quick_task: 001
title: Context Engine Read-Side Foundation
date: 2026-06-05
mode: quick-full
status: planned
files_modified:
  - app/services/context_engine/__init__.py
  - app/services/context_engine/models.py
  - app/services/context_engine/engine.py
  - app/agents/context_extractor.py
  - tests/unit/test_context_engine.py
must_haves:
  truths:
    - Context prompt assembly is represented by a typed packet rather than ad hoc string appends inside the callback.
    - Existing context extractor behavior remains compatible for personalization, remembered user context, agent memory, handoff blocks, cross-agent context, action logs, and root prompt overrides.
    - Duplicate context blocks are not re-appended when the existing system instruction already contains the same block.
  artifacts:
    - A reusable context-engine package exists under app/services/context_engine.
    - Unit tests cover ordering, deduplication, and callback override behavior.
  key_links:
    - app/agents/context_extractor.py
    - app/services/context_engine/engine.py
---

<objective>
Create the first implementation slice of a context engine by extracting read-side prompt assembly from the overloaded ADK context callback into a typed, testable context packet and renderer.
</objective>

<tasks>
  <task id="1">
    <files>
      app/services/context_engine/__init__.py
      app/services/context_engine/models.py
      app/services/context_engine/engine.py
    </files>
    <action>
      Add a small context-engine package with ContextBlock, ContextPacket, and ContextEngine. The engine should order blocks by priority, dedupe empty/duplicate blocks, and apply root prompt overrides consistently.
    </action>
    <verify>
      Unit tests can instantiate the engine without Google ADK dependencies and assert stable prompt assembly.
    </verify>
    <done>
      Context assembly policy lives in the service package and can be reused beyond the current callback.
    </done>
  </task>

  <task id="2">
    <files>
      app/agents/context_extractor.py
    </files>
    <action>
      Replace the callback's inline final string assembly with ContextEngine while preserving all existing block-gathering helpers and root override semantics.
    </action>
    <verify>
      Existing callback tests continue to pass.
    </verify>
    <done>
      context_memory_before_model_callback delegates final prompt assembly to the context engine.
    </done>
  </task>

  <task id="3">
    <files>
      tests/unit/test_context_engine.py
      tests/unit/test_personalization_prompt_injection.py
      tests/unit/test_agent_memory_callback.py
    </files>
    <action>
      Add focused tests for ContextEngine ordering/dedupe/root override and run the existing callback tests that guard personalization and agent memory.
    </action>
    <verify>
      pytest passes for the focused test set.
    </verify>
    <done>
      The first context-engine slice is protected by unit coverage.
    </done>
  </task>
</tasks>

<verification>
- `uv run pytest tests/unit/test_context_engine.py tests/unit/test_personalization_prompt_injection.py tests/unit/test_agent_memory_callback.py`
</verification>
