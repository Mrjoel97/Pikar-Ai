---
quick_task: 2
title: Context Engine Durable Memory Slice
date: 2026-06-05
mode: quick-full
status: planned
files_modified:
  - app/services/context_engine/loaders.py
  - app/services/context_engine/writer.py
  - app/services/context_engine/__init__.py
  - tests/unit/test_context_engine_loaders.py
  - tests/unit/test_context_engine_writer.py
must_haves:
  truths:
    - Durable user memory has a best-effort read API for `user_memory_facts`.
    - Durable user memory has a best-effort write payload/upsert API that respects migration constraints.
    - Runtime callback behavior is not changed until the durable APIs are covered by focused tests.
  artifacts:
    - Context-engine loader module.
    - Context-engine writer module.
    - Unit tests for loader and writer behavior.
  key_links:
    - supabase/migrations/20260302090100_create_user_memory_facts.sql
    - app/services/context_engine/models.py
---

<objective>
Add durable-memory loader and writer primitives to the context engine so a future integration slice can move beyond session-only context without changing runtime behavior yet.
</objective>

<tasks>
  <task id="1">
    <files>
      app/services/context_engine/loaders.py
      tests/unit/test_context_engine_loaders.py
    </files>
    <action>
      Implement a best-effort async loader for `user_memory_facts`, returning normalized structured memory rows for global scope and optional matching agent scope.
    </action>
    <verify>
      Tests cover empty user id, successful row mapping, and failure fallback.
    </verify>
    <done>
      Context engine can read durable structured user facts behind a tested API.
    </done>
  </task>

  <task id="2">
    <files>
      app/services/context_engine/writer.py
      tests/unit/test_context_engine_writer.py
    </files>
    <action>
      Implement pure payload normalization plus best-effort async upsert into `user_memory_facts`, honoring allowed `scope` and `memory_type` values.
    </action>
    <verify>
      Tests cover enum fallback, JSON value handling, invalid no-op payloads, and mocked upsert calls.
    </verify>
    <done>
      Context engine has durable write-side primitives ready for callback wiring in a later slice.
    </done>
  </task>

  <task id="3">
    <files>
      app/services/context_engine/__init__.py
    </files>
    <action>
      Export the loader/writer public symbols without altering existing imports.
    </action>
    <verify>
      Existing context-engine tests still import successfully.
    </verify>
    <done>
      The context-engine package exposes a coherent public surface.
    </done>
  </task>
</tasks>

<verification>
- `uv run pytest tests/unit/test_context_engine.py tests/unit/test_context_engine_loaders.py tests/unit/test_context_engine_writer.py`
- `.venv\Scripts\python.exe -m compileall app\services\context_engine tests\unit\test_context_engine_loaders.py tests\unit\test_context_engine_writer.py`
</verification>
