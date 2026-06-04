---
phase: 109-gemini-live-brainstorm-reliability
plan: 01
type: tdd
wave: 1
depends_on: []
files_modified:
  - app/routers/voice_session.py
  - tests/unit/test_voice_session.py
  - .env.example
autonomous: true
requirements:
  - LIVE-01
  - LIVE-02
  - LIVE-04
  - LIVE-05

must_haves:
  truths:
    - "Backend Live setup uses audio-only response modality and preserves input/output transcription events rather than adding TEXT as a second response modality."
    - "Live config includes context-window compression and session-resumption fields when the installed google-genai SDK exposes them, while remaining compatible with fake/older SDK objects."
    - "Session-resumption updates and GoAway/reset notices are handled without losing the browser WebSocket transcript state."
    - "Explicit finalize and auto-save-on-close still persist captured transcript turns."
  artifacts:
    - path: "app/routers/voice_session.py"
      provides: "Doc-aligned Live config builder, lifecycle event handling, and reconnect/resume helpers"
      contains: "session_resumption"
    - path: "tests/unit/test_voice_session.py"
      provides: "Fake Live SDK coverage for config, resumption, GoAway/reset, generation_complete, and transcript persistence"
      contains: "go_away"
    - path: ".env.example"
      provides: "Recommended Gemini Live model/env configuration and comments for production"
      contains: "GEMINI_LIVE_MODEL"
  key_links:
    - from: "Gemini Live response lifecycle"
      to: "browser WebSocket protocol"
      via: "server messages: ready, audio, transcript, user_transcript, interrupted, generation_complete, turn_complete, time_warning, session_timeout"
      pattern: "send_json"
---

<objective>
Align the FastAPI brainstorm voice bridge with the current Gemini Live API setup and lifecycle contract while preserving the existing browser WebSocket protocol and Knowledge Vault finalization behavior.
</objective>

<execution_context>
@C:/Users/expert/.codex/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/109-gemini-live-brainstorm-reliability/109-CONTEXT.md
@.planning/phases/109-gemini-live-brainstorm-reliability/109-RESEARCH.md
@.planning/phases/109-gemini-live-brainstorm-reliability/109-VALIDATION.md

@app/routers/voice_session.py
@tests/unit/test_voice_session.py
@.env.example

<contracts>
- Keep route `@router.websocket("/voice/{session_id}")`.
- Keep first client message `{type:"auth", token, start_mode, resume_transcript?}`.
- Keep response modality `["AUDIO"]`; transcriptions are separate Live transcription events.
- Keep explicit `/ws/voice/finalize`.
- Do not require browser changes for backend-only lifecycle messages except stable optional events such as `generation_complete` and `live_reconnecting`.
</contracts>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1 (RED): Add backend tests for Live config and lifecycle events</name>
  <files>tests/unit/test_voice_session.py</files>
  <behavior>
  Add failing tests that describe the desired backend contract before implementation.
  </behavior>
  <action>
  1. Extend fake SDK types in `tests/unit/test_voice_session.py` with optional config classes for context-window compression, session resumption, GoAway, generation-complete, and session-resumption update responses.
  2. Add tests asserting the Live config builder includes audio-only response modality, speech config, transcription config, automatic activity detection, context-window compression, and session-resumption options when the fake SDK exposes those classes.
  3. Add a fake response stream that yields:
     - session-resumption update with a new handle
     - GoAway/reset notice
     - generation_complete
     - normal turn_complete plus transcript/audio events
  4. Assert the router stores/uses the resumption handle, forwards stable browser messages for lifecycle events, and preserves accumulated transcript turns.
  5. Run `uv run pytest tests/unit/test_voice_session.py -k "live_config or go_away or generation_complete or resumption"` and confirm the new tests fail for missing implementation.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_voice_session.py -k "live_config or go_away or generation_complete or resumption"</automated>
  </verify>
  <done>
  - New tests fail for missing lifecycle/config implementation, not for syntax/import errors.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2 (GREEN): Implement doc-aligned Live config builder and event extraction</name>
  <files>app/routers/voice_session.py, .env.example</files>
  <behavior>
  Add compatibility helpers around `google.genai.types.LiveConnectConfig` so current SDK features are used when available, and missing SDK features degrade without breaking local tests.
  </behavior>
  <action>
  1. Extract the Live setup construction into a private helper such as `_build_live_connect_config(types, live_voice_instruction)`.
  2. Preserve existing fields: response modalities, system instruction, speech config, input/output audio transcription, realtime input config, automatic activity detection.
  3. Add optional context-window compression config if the SDK exposes it.
  4. Add optional session-resumption config if the SDK exposes it.
  5. Add helper functions that read lifecycle fields from response objects using both snake_case and camelCase names:
     - session resumption update/new handle
     - go_away/goAway/time_left
     - generation_complete/generationComplete
  6. Forward stable browser JSON events:
     - `{type:"generation_complete"}`
     - `{type:"live_reconnecting", reason:"go_away", remaining_seconds?}` when reconnect starts
     - `{type:"live_reconnected"}` when reconnect succeeds
     - `{type:"live_reconnect_failed", message}` if reconnect fails but transcript auto-save remains active
  7. Update `.env.example` with `GEMINI_LIVE_MODEL`, `GEMINI_VOICE_NAME`, `GEMINI_LIVE_SILENCE_MS`, and a note that current docs should be checked before changing the default model in production.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_voice_session.py -k "live_config or go_away or generation_complete or resumption"</automated>
  </verify>
  <done>
  - New backend lifecycle/config tests pass.
  - Existing voice-session tests still pass.
  - Env comments document the model/voice knobs without exposing secrets.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3 (GREEN): Reconnect Live sessions without losing browser transcript state</name>
  <files>app/routers/voice_session.py, tests/unit/test_voice_session.py</files>
  <behavior>
  Implement a minimal reconnect loop that can reopen Gemini Live using the latest resumption handle or active transcript context while keeping the browser WebSocket open.
  </behavior>
  <action>
  1. Refactor the `async with client.aio.live.connect(...)` block only as much as needed to allow reconnect after a lifecycle notice.
  2. Keep `accumulated_turns`, pending transcript state, timers, and browser WebSocket state outside the inner Live session lifetime.
  3. On GoAway/reset:
     - send `live_reconnecting`
     - close/cancel only the inner Live receive/send tasks
     - reopen Live with latest session-resumption handle when available
     - if no handle is available, seed the new session with compact active transcript context
     - send `live_reconnected`
  4. If reconnect fails, send `live_reconnect_failed`, keep accumulated turns, and allow explicit finalize/auto-save to work.
  5. Add tests proving reconnect does not drop user/agent transcript turns and does not close the browser socket on the happy path.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_voice_session.py</automated>
  </verify>
  <done>
  - `uv run pytest tests/unit/test_voice_session.py` passes.
  - The implementation keeps graceful close/finalize behavior intact.
  - No broad rewrite of unrelated finalize or Supabase code.
  </done>
</task>

</tasks>

<verification>
- `uv run pytest tests/unit/test_voice_session.py`
- `uv run python -m compileall app/routers/voice_session.py`
</verification>

<success_criteria>
- LIVE-01, LIVE-02, LIVE-04, and LIVE-05 are covered by tests.
- Backend emits stable lifecycle messages and preserves transcript persistence.
- Env docs are updated for production operators.
</success_criteria>
