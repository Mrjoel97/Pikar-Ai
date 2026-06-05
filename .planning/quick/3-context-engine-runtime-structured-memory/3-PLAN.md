---
quick_task: 3
title: Context Engine Runtime Structured Memory
date: 2026-06-05
mode: quick-full
status: planned
files_modified:
  - app/agents/context_extractor.py
  - app/services/context_engine/loaders.py
  - app/services/context_engine/__init__.py
  - tests/unit/test_agent_memory_callback.py
  - tests/unit/test_context_engine_loaders.py
must_haves:
  truths:
    - Runtime prompt assembly injects durable `user_memory_facts` when available.
    - Structured memory is best-effort and cached per session/agent.
    - Structured memory renders before legacy `agent_memory` so durable profile facts have stable precedence.
  artifacts:
    - Sync loader facade for ADK callback use.
    - Structured-memory prompt block integration.
    - Unit tests for sync loading, caching, and prompt ordering.
  key_links:
    - app/services/context_engine/loaders.py
    - app/agents/context_extractor.py
---

<objective>
Wire the durable structured-memory loader into the existing before-model callback so agents can receive canonical `user_memory_facts` in their system prompt without blocking a model turn.
</objective>

<tasks>
  <task id="1">
    <files>
      app/services/context_engine/loaders.py
      app/services/context_engine/__init__.py
      tests/unit/test_context_engine_loaders.py
    </files>
    <action>
      Add and export a sync loader facade that mirrors the async `user_memory_facts` query for ADK callback use.
    </action>
    <verify>
      Tests cover sync row mapping and invalid-user no-op behavior.
    </verify>
    <done>
      Synchronous callback code can read durable structured facts without introducing an event-loop bridge.
    </done>
  </task>

  <task id="2">
    <files>
      app/agents/context_extractor.py
      tests/unit/test_agent_memory_callback.py
    </files>
    <action>
      Add cached structured-memory block rendering and inject it into `ContextPacket` priority 35.
    </action>
    <verify>
      Tests cover formatted block caching and final prompt ordering before legacy `agent_memory`.
    </verify>
    <done>
      Runtime prompt assembly now includes durable structured memory between brand DNA and legacy per-agent memory.
    </done>
  </task>

  <task id="3">
    <files>
      app/agents/context_extractor.py
    </files>
    <action>
      Remove the duplicate `agent_memory` helper definition discovered beside the integration point.
    </action>
    <verify>
      Existing agent-memory callback tests continue to pass.
    </verify>
    <done>
      The callback has one effective `agent_memory` helper and a separate structured-memory helper.
    </done>
  </task>
</tasks>

<verification>
- `uv run pytest tests/unit/test_context_engine.py tests/unit/test_context_engine_loaders.py tests/unit/test_context_engine_writer.py tests/unit/test_personalization_prompt_injection.py tests/unit/test_agent_memory_callback.py`
- `.venv\Scripts\python.exe -m compileall app\services\context_engine app\agents\context_extractor.py tests\unit\test_context_engine_loaders.py tests\unit\test_agent_memory_callback.py`
- `uv run ruff check app/agents/context_extractor.py app/services/context_engine tests/unit/test_context_engine_loaders.py tests/unit/test_agent_memory_callback.py` attempted but Ruff is not installed/available in the active environment.
</verification>
