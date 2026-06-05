---
quick_task: 4
title: Context Engine Save User Context Persistence
date: 2026-06-05
mode: quick-full
status: planned
files_modified:
  - app/agents/context_extractor.py
  - app/services/context_engine/writer.py
  - app/services/context_engine/__init__.py
  - tests/unit/test_agent_memory_callback.py
  - tests/unit/test_context_engine_writer.py
must_haves:
  truths:
    - `save_user_context` still updates session state and returns the same visible response.
    - Saved facts are also persisted to durable `user_memory_facts` best-effort.
    - Failed durable writes never block or change the session save.
  artifacts:
    - Sync writer facade for ADK callback use.
    - After-tool callback wiring for `save_user_context`.
    - Tests for durable write calls and failure fallback.
  key_links:
    - app/agents/tools/context_memory.py
    - app/agents/context_extractor.py
    - app/services/context_engine/writer.py
---

<objective>
Promote facts saved with `save_user_context` into durable structured memory while preserving the existing session-state behavior and tool response contract.
</objective>

<tasks>
  <task id="1">
    <files>
      app/services/context_engine/writer.py
      app/services/context_engine/__init__.py
      tests/unit/test_context_engine_writer.py
    </files>
    <action>
      Add and export a sync `user_memory_facts` upsert facade for ADK after-tool callbacks.
    </action>
    <verify>
      Tests cover expected conflict target, invalid payload no-op, and database failure fallback.
    </verify>
    <done>
      Callback code can durable-write normalized memory facts without event-loop bridging.
    </done>
  </task>

  <task id="2">
    <files>
      app/agents/context_extractor.py
      tests/unit/test_agent_memory_callback.py
    </files>
    <action>
      Wire `_context_memory_save` handling to normalize and upsert a global structured fact, then clear structured-memory prompt caches on successful durable writes.
    </action>
    <verify>
      Tests prove session save behavior is unchanged, durable write receives the expected payload, cache invalidates on success, and write failures still return saved session context.
    </verify>
    <done>
      User-saved context facts now feed durable prompt memory for future turns and sessions.
    </done>
  </task>
</tasks>

<verification>
- `uv run pytest tests/unit/test_context_engine_writer.py tests/unit/test_agent_memory_callback.py`
- `uv run pytest tests/unit/test_context_engine.py tests/unit/test_context_engine_loaders.py tests/unit/test_context_engine_writer.py tests/unit/test_personalization_prompt_injection.py tests/unit/test_agent_memory_callback.py tests/unit/test_tool_progress_events.py`
- `.venv\Scripts\python.exe -m compileall app\services\context_engine app\agents\context_extractor.py tests\unit\test_context_engine_writer.py tests\unit\test_agent_memory_callback.py`
- `uv run ruff check app/agents/context_extractor.py app/services/context_engine tests/unit/test_context_engine_writer.py tests/unit/test_agent_memory_callback.py` attempted but Ruff is not installed/available in the active environment.
</verification>
