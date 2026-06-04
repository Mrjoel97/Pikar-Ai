# Phase 109: Gemini Live Brainstorm Reliability - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning
**Source:** User request to adapt the brainstorm feature to the current Gemini Live API docs plus local code review.

<domain>
## Phase Boundary

This phase fixes the existing brain-dump/brainstorm voice experience. The user wants the current setup adapted to the official Gemini Live API setup instructions so the brainstorm feature works reliably.

What ships:
1. The existing FastAPI WebSocket bridge in `app/routers/voice_session.py` remains the production path and is aligned to current Live API setup semantics.
2. The browser capture/playback hook in `frontend/src/hooks/useVoiceSession.ts` sends doc-aligned PCM chunks, handles interruption and turn boundaries, and keeps the overlay state truthful.
3. Long or reset-prone sessions survive Live API lifecycle events through session-resumption handles and transcript-backed reconnect.
4. Existing finalization behavior remains intact: transcript and comprehensive brainstorm analysis save to the Knowledge Vault.
5. Automated tests and manual UAT prove the repaired path.

What does not ship unless explicitly escalated:
- Replacing the backend bridge with a direct browser-to-Gemini production path.
- Exposing a real API key to the browser.
- Rewriting the brainstorm UI as a new experience.
- Changing non-brainstorm chat dictation, Web Speech API dictation, or unrelated agent routing.

</domain>

<decisions>
## Implementation Decisions

### Keep the backend bridge first
- The existing server-to-server bridge is the safest repair path because it keeps Google credentials server-side, preserves Supabase auth, and avoids adding a new browser auth/token surface before the current feature is stable.
- Direct browser-to-Gemini Live can be designed as a follow-up behind ephemeral tokens, but it is not the first production fix.

### No browser API key
- If direct Live is later introduced, it must use short-lived ephemeral tokens minted by the backend and constrained to the specific Live model/config. The browser must never receive `GOOGLE_API_KEY` or broad Vertex credentials.

### Preserve brainstorm artifacts
- The current `/ws/voice/finalize`, auto-save-on-close, `braindump_sessions`, transcript markdown, and comprehensive analysis flow remain part of the contract. Reliability work cannot trade away saved artifacts.

### Use doc-aligned audio and lifecycle contracts
- Input audio must be raw 16-bit PCM mono at 16kHz.
- Output audio must be treated as raw PCM with MIME/rate metadata, usually 24kHz.
- Client chunks should be batched into roughly 20-40ms frames before base64 JSON WebSocket send.
- Backend Live setup should include audio-only response modality, system instruction, voice config, transcriptions, activity detection, context-window compression, and session resumption when the SDK exposes those types.

### Keep provider details configurable
- `GEMINI_LIVE_MODEL`, `GEMINI_VOICE_NAME`, Vertex vs API-key mode, silence thresholds, and chunking thresholds stay environment-configurable.
- The code should normalize old aliases but log the actual model/config used at session start.

### Claude's Discretion
- Exact helper names and refactor boundaries inside `voice_session.py`.
- Whether session reconnect lives as a small local helper or a private class, as long as the public WebSocket protocol remains compatible.
- Exact test fixture layout for frontend chunking and backend fake Live events.

</decisions>

<specifics>
## Specific Ideas

- Backend files likely touched: `app/routers/voice_session.py`, `tests/unit/test_voice_session.py`, `.env.example`.
- Frontend files likely touched: `frontend/src/hooks/useVoiceSession.ts`, `frontend/__tests__/hooks/useVoiceSession.test.ts`, `frontend/src/components/braindump/VoiceBrainstormOverlay.tsx` only if state labels need adjustment.
- Deployment/edge should be reviewed because `deployment/cloudflare/edge-api/src/index.ts` proxies WebSocket upgrades directly.
- Current repo has prior voice work in Phase 84; do not undo the noise-floor cutoff without replacing it with an equally tested turn-close mechanism.
- The older workflow-node-editor planning bundle was previously another Phase 109 and has been renumbered to `.planning/phases/123-workflow-node-editor-viewer`; this phase's roadmap-owned directory is `.planning/phases/109-gemini-live-brainstorm-reliability`.

</specifics>

<deferred>
## Deferred Ideas

- Full direct browser Live API implementation using ephemeral tokens.
- Multimodal screen/video input for brainstorm sessions.
- Voice selection UI.
- Mobile-specific redesign of the overlay.
- Replacing JSON-over-WebSocket audio frames with binary frames.

</deferred>

---

*Phase: 109-gemini-live-brainstorm-reliability*
*Context gathered: 2026-05-22 from user request, Gemini Live API docs review, and local code review*
