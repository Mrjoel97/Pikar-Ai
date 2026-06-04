---
phase: 109-gemini-live-brainstorm-reliability
plan: 02
type: tdd
wave: 1
depends_on: []
files_modified:
  - frontend/src/hooks/useVoiceSession.ts
  - frontend/__tests__/hooks/useVoiceSession.test.ts
  - frontend/src/components/braindump/VoiceBrainstormOverlay.tsx
autonomous: true
requirements:
  - LIVE-03
  - LIVE-04
  - LIVE-05

must_haves:
  truths:
    - "Browser mic audio is sent as base64 PCM16 mono at 16kHz in roughly 20-40ms chunks, not arbitrary AudioWorklet render quanta."
    - "Gemini audio output with `audio/pcm;rate=24000` is decoded and queued for playback without stalling, and missing/malformed MIME falls back to the safe 24kHz PCM path."
    - "Existing noise-floor cutoff remains in place so silence after user speech can close the server-side turn."
    - "Interruption/barge-in is possible for high-confidence user speech while agent audio is playing, but low-level speaker echo is not forwarded as user speech."
    - "Frontend state handles ready, audio, transcript, user_transcript, waiting_for_input, generation_complete, turn_complete, interrupted, live_reconnecting, live_reconnected, and close/error without trapping the overlay."
  artifacts:
    - path: "frontend/src/hooks/useVoiceSession.ts"
      provides: "Coalesced mic frame sender, explicit idle turn-end behavior, barge-in/interruption handling, lifecycle message handling"
      contains: "VOICE_MIC_CHUNK_MS"
    - path: "frontend/__tests__/hooks/useVoiceSession.test.ts"
      provides: "Vitest coverage for chunking, 24kHz playback decode, silence floor, barge-in, and lifecycle state"
      contains: "plays Gemini 24kHz PCM output"
    - path: "frontend/src/components/braindump/VoiceBrainstormOverlay.tsx"
      provides: "Optional reconnect/status copy if lifecycle messages expose a new transient state"
      contains: "reconnecting"
  key_links:
    - from: "AudioWorklet Float32 chunks"
      to: "Gemini Live realtime audio input"
      via: "20-40ms PCM16 base64 JSON payloads"
      pattern: "type: 'audio'"
---

<objective>
Bring the browser side of the brainstorm voice session into alignment with the Live API audio and turn-taking contract: stable PCM chunking, explicit idle turn-end, and interruption support without losing transcript/finalize state.
</objective>

<execution_context>
@C:/Users/expert/.codex/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/109-gemini-live-brainstorm-reliability/109-CONTEXT.md
@.planning/phases/109-gemini-live-brainstorm-reliability/109-RESEARCH.md
@.planning/phases/109-gemini-live-brainstorm-reliability/109-VALIDATION.md

@frontend/src/hooks/useVoiceSession.ts
@frontend/__tests__/hooks/useVoiceSession.test.ts
@frontend/src/components/braindump/VoiceBrainstormOverlay.tsx
@frontend/public/audio/mic-capture-worklet.js

<contracts>
- Do not affect `useSpeechRecognition.ts`; chat dictation is separate.
- Keep `connect(sessionId, {startMode, initialTurns, resumeTranscript})` API shape.
- Keep transcript turn accumulation and `buildVoiceTranscriptText()` consumers compatible.
- Preserve `VOICE_NOISE_FLOOR_RMS` behavior from Phase 84.
</contracts>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1 (RED): Add frontend tests for chunking and lifecycle state</name>
  <files>frontend/__tests__/hooks/useVoiceSession.test.ts</files>
  <behavior>
  Add failing tests that define doc-aligned browser behavior before changing the hook.
  </behavior>
  <action>
  1. Add a helper to synthesize AudioWorklet-sized Float32 chunks and count resulting `{type:"audio"}` WebSocket sends.
  2. Add specs:
     - `coalesces mic frames into 20-40ms PCM payloads before sending`
     - `keeps sub-noise-floor chunks out of the outgoing audio stream`
     - `sends audio_stream_end only after idle speech, not after every small frame`
     - `plays Gemini 24kHz PCM output without decode stalls`
     - `falls back to 24kHz PCM playback when audio MIME is missing or malformed`
     - `allows high-RMS barge-in while agent audio is playing`
     - `suppresses low-RMS playback echo while agent audio is playing`
     - `handles generation_complete and live reconnect lifecycle messages`
  3. Run the targeted vitest command and confirm tests fail for missing chunking/barge-in/lifecycle behavior.
  </action>
  <verify>
    <automated>cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts -t "coalesces mic frames|24kHz PCM output|barge-in|generation_complete|live reconnect"</automated>
  </verify>
  <done>
  - Tests are present and fail for behavior, not for test harness setup.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2 (GREEN): Implement 20-40ms PCM chunk batching</name>
  <files>frontend/src/hooks/useVoiceSession.ts</files>
  <behavior>
  Buffer Float32 mic samples after noise-floor filtering and send PCM16 payloads in 20-40ms windows.
  </behavior>
  <action>
  1. Add configurable constants near existing audio constants:
     - `VOICE_MIC_CHUNK_MS` default 40
     - `VOICE_BARGE_IN_RMS` default 0.02 or similarly conservative threshold
  2. Add a mic sample accumulator ref that stores post-filter Float32 input.
  3. Convert and send only when the accumulator reaches the target frame size at 16kHz.
  4. Flush remaining buffered speech before sending `audio_stream_end` and during `disconnect`.
  5. Keep existing base64 JSON protocol unchanged.
  6. Add or preserve test-covered playback handling for backend `{type:"audio", mime_type:"audio/pcm;rate=24000"}` messages. If current `decodeAgentAudioChunk` already passes the new tests, do not rewrite it; lock the behavior with tests.
  7. Ensure missing or malformed audio MIME falls back to the safe 24kHz PCM path instead of throwing or stalling playback.
  8. Ensure cleanup clears the accumulator.
  </action>
  <verify>
    <automated>cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts -t "coalesces mic frames|audio_stream_end|sub-noise-floor|24kHz PCM output"</automated>
  </verify>
  <done>
  - Chunking tests pass.
  - Existing voice tests continue to pass.
  - Audio payload MIME expectations remain server-compatible.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3 (GREEN): Add interruption/barge-in and lifecycle state handling</name>
  <files>frontend/src/hooks/useVoiceSession.ts, frontend/src/components/braindump/VoiceBrainstormOverlay.tsx</files>
  <behavior>
  Let deliberate user speech interrupt agent playback while keeping echo/ambient noise suppressed.
  </behavior>
  <action>
  1. While agent playback is active, continue suppressing low-RMS chunks.
  2. If chunk RMS exceeds `VOICE_BARGE_IN_RMS`, flush/send it, call local `interruptPlayback()`, and allow server-side `interrupted` to confirm/settle.
  3. Handle backend lifecycle messages:
     - `generation_complete`
     - `live_reconnecting`
     - `live_reconnected`
     - `live_reconnect_failed`
  4. Add a minimal UI state only if useful: for example "Reconnecting..." during `live_reconnecting`. Keep visible text short and avoid feature explanations.
  5. Ensure explicit end/finalize still works if reconnect fails after some transcript turns.
  </action>
  <verify>
    <automated>cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts</automated>
  </verify>
  <done>
  - Full `useVoiceSession` vitest file passes.
  - User interruption and lifecycle events do not strand `isAgentSpeaking`, `isAwaitingGreeting`, or `error` state.
  - Brainstorm finalization still receives transcript turns.
  </done>
</task>

</tasks>

<verification>
- `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts`
- `cd frontend && npm run lint`
</verification>

<success_criteria>
- LIVE-03 and LIVE-04 are covered by focused frontend tests.
- Existing Phase 84 turn-close/noise-floor behavior remains intact.
- The UI can recover from Live reconnect and interruption states.
</success_criteria>
