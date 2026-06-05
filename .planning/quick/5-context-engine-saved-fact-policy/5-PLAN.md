---
quick_task: 5
title: Context Engine Saved Fact Policy
date: 2026-06-05
mode: quick-full
status: planned
files_modified:
  - app/services/context_engine/writer.py
  - app/services/context_engine/__init__.py
  - app/agents/context_extractor.py
  - tests/unit/test_context_engine_writer.py
  - tests/unit/test_agent_memory_callback.py
must_haves:
  truths:
    - Saved context facts no longer always persist as generic `fact` memory.
    - Memory type inference is deterministic and conservative.
    - Ambiguous keys remain global facts.
  artifacts:
    - Write-policy helper for saved context keys.
    - Callback integration that applies the policy before durable upsert.
    - Tests for fact/preference/goal/constraint classification and agent scope prefix behavior.
  key_links:
    - app/services/context_engine/writer.py
    - app/agents/context_extractor.py
---

<objective>
Add a deterministic write policy for `save_user_context` so durable memory records carry useful `memory_type` and scope metadata without requiring an LLM classifier.
</objective>

<tasks>
  <task id="1">
    <files>
      app/services/context_engine/writer.py
      app/services/context_engine/__init__.py
      tests/unit/test_context_engine_writer.py
    </files>
    <action>
      Implement and export `infer_user_memory_fact_write_policy()` with conservative keyword-based classification for facts, preferences, goals, and constraints.
    </action>
    <verify>
      Tests cover default fact behavior, preference/goal/constraint keys, agent-scoped prefixes, and ambiguous agentless prefix fallback.
    </verify>
    <done>
      Durable writes have a reusable policy layer before payload normalization.
    </done>
  </task>

  <task id="2">
    <files>
      app/agents/context_extractor.py
      tests/unit/test_agent_memory_callback.py
    </files>
    <action>
      Apply inferred policy inside `_try_persist_structured_user_memory()` before calling the normalized durable upsert.
    </action>
    <verify>
      Callback tests assert `preferred_tone` persists as `memory_type=preference` while session-state behavior remains unchanged.
    </verify>
    <done>
      `save_user_context` durable writes carry policy-derived metadata.
    </done>
  </task>
</tasks>

<verification>
- `.venv\Scripts\python.exe -m pytest tests\unit\test_context_engine_writer.py -vv`
- `.venv\Scripts\python.exe -m pytest tests\unit\test_agent_memory_callback.py -q`
- `.venv\Scripts\python.exe -m pytest tests\unit\test_context_engine.py tests\unit\test_context_engine_loaders.py tests\unit\test_context_engine_writer.py tests\unit\test_personalization_prompt_injection.py tests\unit\test_agent_memory_callback.py tests\unit\test_tool_progress_events.py -q`
- `.venv\Scripts\python.exe -m compileall app\services\context_engine app\agents\context_extractor.py tests\unit\test_context_engine_writer.py tests\unit\test_agent_memory_callback.py`
- `uv run ruff check app/agents/context_extractor.py app/services/context_engine tests/unit/test_context_engine_writer.py tests/unit/test_agent_memory_callback.py` attempted but Ruff is not installed/available in the active environment.
</verification>
