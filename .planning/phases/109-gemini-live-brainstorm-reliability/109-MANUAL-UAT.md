# Phase 109 - Manual UAT Checklist

Use this checklist after Plans 109-01 and 109-02 land. Record browser, device, deployment target, session id, and relevant Cloud Run/edge log excerpts for each run.

## Prerequisites

- [ ] Backend has valid Google Gemini/Vertex credentials for the selected `GEMINI_LIVE_MODEL`.
- [ ] Frontend points at the backend/edge origin that serves `/ws/voice/{session_id}`.
- [ ] Test user can start a brainstorm session and access the Knowledge Vault.
- [ ] Browser microphone permission is granted.

## Environment

- Deployment target:
- Backend revision:
- Frontend build:
- Cloudflare Worker deployment:
- Browser/device:
- `GEMINI_LIVE_MODEL`:
- `GEMINI_VOICE_NAME`:

## Test Account

- User id:
- Workspace/persona:
- Session id:
- Existing Knowledge Vault context present: yes/no

## Log Filters

Use these patterns while running UAT:

- `voice_session_started`
- `voice_first_user_audio_chunk`
- `voice_input_transcript`
- `voice_gemini_audio_out`
- `voice_turn_complete`
- `voice_live_resumption_handle`
- `voice_live_go_away`
- `Auto-saved brain-dump transcript on close`

## Requirement Coverage

- LIVE-01: backend Live setup and configuration are visible in startup logs.
- LIVE-02: reconnect/resumption behavior is covered by the refresh/reconnect and lifecycle log checks.
- LIVE-03: 16kHz input and 24kHz output behavior is covered by desktop/mobile audio playback checks.
- LIVE-04: turn-taking and interruption are covered by the 4-turn brainstorm and interruption checks.
- LIVE-05: transcript durability is covered by explicit finalize, Knowledge Vault save, and auto-save checks.
- LIVE-06: this checklist plus automated tests provide production verification coverage.

## Core Flows

- [ ] Desktop 4-turn brainstorm: agent greets, user speaks, agent replies, user speaks again, agent replies again, and no stuck silence occurs.
- [ ] User interruption: begin speaking while the agent is talking; playback stops or is interrupted, user speech is captured, and the agent responds to the interruption.
- [ ] Refresh/reconnect: refresh mid-session after at least two turns, continue from active transcript, then end and save.
- [ ] Mobile smoke: start a session, speak, pause, receive reply, end, and save on a mobile browser.
- [ ] timeout/wrap-up: verify warning state appears near session limit and finalization still works.
- [ ] Explicit finalize: click End Session and confirm transcript plus analysis are saved.
- [ ] Knowledge Vault save: confirm the saved transcript and analysis are visible in Brain Dumps or the Knowledge Vault.
- [ ] Auto-save safety: close tab or drop network after captured turns and confirm at least transcript auto-save occurs.

## Expected Logs

- [ ] Session started with model/config fields.
- [ ] First user audio chunk logged.
- [ ] Input transcript appears after user speech.
- [ ] Agent generation/audio output appears after user pause.
- [ ] Turn completion alternates with user/agent turns.
- [ ] Reconnect/resumption logs appear if a lifecycle reset is triggered.
- [ ] Finalize or auto-save logs include transcript/analysis document ids when available.
