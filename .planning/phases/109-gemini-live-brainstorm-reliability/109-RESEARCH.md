# Phase 109: Gemini Live Brainstorm Reliability - Research

**Researched:** 2026-05-22
**Domain:** Gemini Live API, FastAPI WebSocket bridge, WebAudio PCM streaming, brainstorm transcript persistence
**Confidence:** HIGH for current-code gaps; MEDIUM for exact model defaults because model availability can vary by Google API surface/region.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LIVE-01 | Backend Live setup matches current API contract | Docs require explicit Live setup with model, config, response modality, voice config, and audio transcription. Current bridge mostly has this but needs lifecycle and compression/resumption coverage. |
| LIVE-02 | Long sessions handle reset/resumption | Live API docs describe session duration limits, `GoAway`, and session resumption handles. Current code has a local 15-minute timer but no provider lifecycle reconnect. |
| LIVE-03 | Browser audio chunks are doc-aligned | Docs recommend 16-bit PCM mono at 16kHz input and 24kHz output handling; best practice is small realtime chunks. Current code captures PCM but forwards AudioWorklet-sized chunks through JSON immediately. |
| LIVE-04 | Turn-taking and interruption work | Live supports realtime audio, activity detection, `interrupted`, generation completion, and explicit turn end. Current code handles some events but does not fully use generation-complete/go-away/session-resumption events and half-duplex behavior limits interruption. |
| LIVE-05 | Finalization remains durable | Existing `voice_session.py` saves transcripts on explicit finalize and auto-saves accumulated turns on close. Any reconnect work must preserve this safety net. |
| LIVE-06 | Tests and UAT prove behavior | Existing tests cover second-turn streaming and some helper behavior. Missing: resumption/go-away, generation-complete, doc-shaped config, frontend chunk sizing, and real 4-turn UAT. |

## Current Architecture

The brainstorm feature currently uses this path:

1. `frontend/src/hooks/useVoiceSession.ts` captures microphone Float32 audio through AudioWorklet or ScriptProcessor.
2. The hook downsamples to 16kHz PCM16, base64 encodes it, and sends `{type:"audio"}` JSON frames to `buildAgentWebSocketUrl('/ws/voice/{sessionId}')`.
3. `app/routers/voice_session.py` authenticates the first WebSocket message, creates a `google.genai.Client`, opens `client.aio.live.connect(...)`, and bridges audio to Gemini Live.
4. Gemini audio parts return to the browser as base64 PCM; input/output transcriptions are accumulated into `TranscriptTurn` records.
5. `/ws/voice/finalize` generates transcript markdown plus comprehensive brainstorm analysis and saves artifacts to the Knowledge Vault.

This is a valid server-to-server topology. It should stay the first repair path because it keeps credentials server-side and fits existing auth/finalization code.

## Official Docs Findings

### Setup and model/config

The Live API docs show a Live session opened with a model and Live config. The docs examples currently use the Gemini Live preview model family, including `gemini-3.1-flash-live-preview` in WebSocket/ephemeral-token examples, and configure audio responses separately from transcriptions.

Practical implication for this repo:
- Keep `GEMINI_LIVE_MODEL` as the source of truth.
- Normalize legacy aliases.
- Update docs/env examples to recommend the current Live model, but do not hard-fail older explicitly configured model names unless Google rejects them.
- Log model/config at session start.

### Audio

Docs and examples use raw audio blobs with MIME metadata such as `audio/pcm;rate=16000` for input, and the Live API returns inline audio with MIME/rate metadata for output. Browser audio should be converted to 16-bit little-endian PCM mono.

Current code is close:
- `MIC_SAMPLE_RATE = 16000`
- `SPEAKER_SAMPLE_RATE = 24000`
- backend sends `types.Blob(..., mime_type="audio/pcm;rate=16000")`
- playback parses `rate=` from MIME.

Gap:
- AudioWorklet forwards small render-quanta frames immediately. Batch into 20-40ms chunks to match realtime best practice and reduce JSON/base64 overhead.

### Activity detection and turn boundaries

Current backend config uses `automatic_activity_detection` with high sensitivity, prefix padding, and `silence_duration_ms`. Phase 84 added a frontend noise-floor cutoff so server VAD can actually observe silence after user pauses.

Gaps:
- Explicit `audio_stream_end` should remain as a turn boundary fallback.
- The frontend should send it after a quiet idle period, not while chunks are still actively queued.
- Backend should tolerate repeated `audio_stream_end`.
- Backend should surface `generation_complete` when present so the client can separate "model has generated" from "audio playback drained."

### Interruption

Live supports interruption; server responses may include `interrupted`. Current backend forwards `interrupted`, and frontend clears playback on that message. But frontend half-duplex gating suppresses mic audio while agent audio is playing, which makes barge-in weak.

Recommended shape:
- Keep normal echo protection during agent playback.
- Add explicit barge-in detection: while agent audio is playing, only high-confidence user speech chunks above a separate barge-in RMS threshold pass through and locally interrupt playback.
- Do not let low-level playback echo reopen a user turn.

### Session management

The docs describe session resumption and lifecycle notices. Current code has:
- local wrap-up/final-warning/session-timeout timers
- resume transcript context from browser refresh
- auto-save in `finally`

Missing:
- Capture session resumption handles from Live responses.
- Handle `goAway`/reset notices.
- Reconnect to Live without closing the browser WebSocket when possible.
- Feed compact active transcript context into the new Live session after reconnect.
- Use context-window compression if SDK supports it.

## Recommended Plan Structure

1. Backend bridge alignment: config builder, session-resumption capture, GoAway/reset handling, generation-complete forwarding, tests.
2. Frontend audio and turn-taking: 20-40ms batching, stricter send cadence, barge-in/interruption, state handling, tests.
3. Production UAT and direct-live readiness: manual UAT artifact, env/deploy docs, edge WebSocket verification, and a deferred ephemeral-token design so a future latency phase does not start from zero.

## Validation Architecture

### Automated backend coverage

- `tests/unit/test_voice_session.py`:
  - Live config includes response modality AUDIO, speech config, transcription config, activity detection, and optional compression/resumption fields when fake SDK types expose them.
  - Fake Live response with session-resumption update stores the latest handle.
  - Fake GoAway response triggers reconnect workflow or at minimum browser warning plus graceful close if reconnect is unavailable.
  - Fake generation-complete event forwards a stable browser message.
  - Existing second-turn/transcript auto-save regression stays green.

### Automated frontend coverage

- `frontend/__tests__/hooks/useVoiceSession.test.ts`:
  - Captured mic frames are coalesced into 20-40ms PCM payloads before `ws.send`.
  - Sub-noise-floor chunks still drop.
  - Explicit `audio_stream_end` still fires after idle speech.
  - High-RMS user barge-in during playback sends user audio and calls interruption playback cleanup.
  - Low-RMS speaker echo during playback does not send user audio.
  - `generation_complete`, `turn_complete`, `waiting_for_input`, `interrupted`, and close paths update state without trapping the overlay in "Speaking..." or "Connecting...".

### Manual UAT

- Desktop Chrome: 4-turn brainstorm with natural pauses, then finalize. Confirm analysis widget and Vault documents.
- Desktop Chrome: interrupt the agent mid-sentence; confirm playback stops and the agent responds to the interruption.
- Mobile browser: start, speak, pause, receive reply, end and save.
- Refresh/reconnect: start a session, speak two turns, refresh browser, continue from active transcript, end and save.
- Provider lifecycle: if practical, lower a test-only timer/mock to force reconnect path and verify browser WebSocket stays open.

## Risks

1. SDK version drift: installed `google-genai` is locked in `uv.lock` as 1.56.0, but local global Python did not have `google.genai`. Use the project virtualenv/container and write compatibility helpers with `hasattr`/try blocks.
2. Vertex model availability: the docs' latest model name may not be available in the configured Vertex region. Keep env override and log the actual model.
3. Barge-in false positives: speaker echo could trigger interruption. Use separate barge-in RMS threshold and browser echo cancellation; test low-RMS echo suppression.
4. Reconnect complexity: reconnecting Live inside a single browser WebSocket is more complex than closing and asking the client to retry. Prefer transcript-safe reconnect, but if SDK/runtime blocks it, fail gracefully and auto-save.

## Deferred Direct-Live Path

The docs recommend ephemeral tokens for client-to-server deployments. This phase should not switch production to direct browser Live, but Plan 03 should document the shape:

- Backend endpoint mints short-lived ephemeral tokens constrained to the Live model/config.
- Frontend connects directly to Gemini only behind a feature flag.
- The backend still owns transcript/finalization, so the direct path needs a transcript/event mirror.
- No broad Google API key or Vertex service credentials ever leave the server.

## Sources

- Gemini Live API overview: https://ai.google.dev/gemini-api/docs/live-api
- GenAI SDK Live setup: https://ai.google.dev/gemini-api/docs/live-api/get-started-sdk
- WebSocket Live setup: https://ai.google.dev/gemini-api/docs/live-api/get-started-websocket
- Session management: https://ai.google.dev/gemini-api/docs/live-api/session-management
- Ephemeral tokens: https://ai.google.dev/gemini-api/docs/live-api/ephemeral-tokens
- Best practices: https://ai.google.dev/gemini-api/docs/live-api/best-practices
- Local backend bridge: `app/routers/voice_session.py`
- Local frontend hook: `frontend/src/hooks/useVoiceSession.ts`
- Prior voice phase: `.planning/phases/84-voice-gate-deadlock-fix/84-RESEARCH.md`

