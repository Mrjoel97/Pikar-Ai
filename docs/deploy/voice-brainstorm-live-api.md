# Voice Brainstorm Gemini Live API Deployment

Phase 109 keeps the production path as a server-to-server bridge:

Browser mic -> `/ws/voice/{session_id}` -> FastAPI -> Gemini Live -> FastAPI -> browser speaker.

The browser never receives `GOOGLE_API_KEY` or service account credentials. The
backend keeps transcript accumulation and final Knowledge Vault save authority.

## Required Backend Configuration

- `GOOGLE_GENAI_USE_VERTEXAI=1` for production Vertex AI access.
- `GOOGLE_CLOUD_PROJECT` set to the Vertex project that has Gemini Live access.
- `GOOGLE_CLOUD_LOCATION` set to the supported Vertex location, usually `us-central1`.
- `GOOGLE_APPLICATION_CREDENTIALS` or Cloud Run workload identity for server auth.
- `GEMINI_LIVE_MODEL=gemini-live-2.5-flash-native-audio` unless a current Gemini Live
  docs review and staging UAT approve a model change.
- `GEMINI_VOICE_NAME=Kore` or another supported Live API prebuilt voice.
- `GEMINI_LIVE_SILENCE_MS=500` for server-side automatic activity detection.
- `GEMINI_LIVE_PREFIX_PADDING_MS=120` so the first syllables of user speech are retained.

`GOOGLE_API_KEY` is acceptable only for local developer fallback. Do not configure
it in browser-visible environments and do not expose it through a frontend API route.

## Frontend Audio Knobs

- `NEXT_PUBLIC_VOICE_NOISE_FLOOR_RMS=0.003` drops ambient noise below speech level.
- `NEXT_PUBLIC_VOICE_MIC_CHUNK_MS=40` sends 16 kHz PCM16 mic audio in a 20-40 ms
  Gemini Live-compatible window.
- `NEXT_PUBLIC_VOICE_BARGE_IN_RMS=0.02` allows deliberate speech to interrupt agent
  playback while suppressing low-level speaker echo.
- `NEXT_PUBLIC_VOICE_TURN_IDLE_END_MS=500` sends `audio_stream_end` after speech idle.
- `NEXT_PUBLIC_VOICE_PLAYBACK_BUFFER_MS=60` keeps output smooth without adding a long
  client-side queue.
- `NEXT_PUBLIC_VOICE_AGENT_RESPONSE_DELAY_MS=10` gives the first audio chunk a tiny
  priming window before WebAudio schedules playback.
- `NEXT_PUBLIC_VOICE_TURN_END_ENABLED=1` keeps the explicit idle turn-end marker on.

## WebSocket Path

The frontend opens:

```text
/ws/voice/{session_id}
```

The Cloudflare Edge API Worker should proxy WebSocket upgrades for `/ws/voice/*`
directly to Cloud Run without JSON body rewriting or rate-limit response shaping.
The backend route handles its own auth as the first WebSocket message:

```json
{"type":"auth","token":"<supabase-jwt>","start_mode":"resume"}
```

## Expected Runtime Events

Backend-to-browser events include `ready`, `audio`, `transcript`,
`user_transcript`, `waiting_for_input`, `generation_complete`, `turn_complete`,
`interrupted`, `live_reconnecting`, `live_reconnected`, `live_reconnect_failed`,
`time_warning`, `session_timeout`, and `error`.

Production logs to inspect:

- `voice_session_started`
- `voice_first_user_audio_chunk`
- `voice_input_transcript`
- `voice_gemini_audio_out`
- `voice_turn_complete`
- `voice_live_resumption_handle`
- `voice_live_go_away`
- `Auto-saved brain-dump transcript on close`

## Common Failures

- No greeting: check Vertex auth, `GEMINI_LIVE_MODEL`, and Cloud Run egress.
- User transcript appears but agent never responds: check noise floor, idle
  `audio_stream_end`, and Live `AutomaticActivityDetection` values.
- Browser shows reconnecting: check `voice_live_go_away`, session resumption handle
  logs, and Cloud Run request timeout or instance restarts.
- Audio decode errors: verify backend emits `audio/pcm;rate=24000` for Live output.
- Finalize has no Knowledge Vault document: inspect `/ws/voice/finalize`, Supabase
  `braindump_sessions`, and auto-save logs on WebSocket close.

## Deferred Direct Live Path

Direct browser-to-Gemini Live remains deferred. If enabled later, it must use a
backend-minted ephemeral token and must never expose `GOOGLE_API_KEY` or service
account credentials in browser code.

Future endpoint shape:

```text
POST /api/voice/live-token
```

Authenticated request in, short-lived model/config-constrained ephemeral token out.
Before enabling direct Live, add:

- Transcript and lifecycle event mirroring back to the backend.
- Compatibility with `/ws/voice/finalize` and auto-save-on-close.
- A feature flag that defaults off in production.
- Rate limits and abuse controls for token minting.
- Tests proving model, voice, modality, and session config constraints cannot be widened.

The server-to-server bridge remains the Phase 109 production path.
