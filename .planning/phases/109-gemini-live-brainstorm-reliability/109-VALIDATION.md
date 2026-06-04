---
phase: 109
slug: gemini-live-brainstorm-reliability
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-22
---

# Phase 109 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x backend, vitest frontend |
| **Config file** | `pyproject.toml`, `frontend/vitest.config.mts` |
| **Quick run command** | `uv run pytest tests/unit/test_voice_session.py && cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts` |
| **Full suite command** | `make test` |
| **Estimated runtime** | ~60-180 seconds for quick voice suite, full suite varies |

---

## Sampling Rate

- **After every task commit:** Run the relevant plan-level command from the table below.
- **After every plan wave:** Run `uv run pytest tests/unit/test_voice_session.py && cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts`.
- **Before `$gsd-verify-work`:** Full suite should be green or documented with unrelated pre-existing failures.
- **Max feedback latency:** 180 seconds for the voice-focused checks.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 109-01-01 | 01 | 1 | LIVE-01 | unit | `uv run pytest tests/unit/test_voice_session.py -k "live_config or response_modalities or session_resumption"` | yes | pending |
| 109-01-02 | 01 | 1 | LIVE-02 | unit | `uv run pytest tests/unit/test_voice_session.py -k "go_away or resumption or reconnect"` | yes | pending |
| 109-01-03 | 01 | 1 | LIVE-04 | unit | `uv run pytest tests/unit/test_voice_session.py -k "generation_complete or interrupted or turn_complete"` | yes | pending |
| 109-02-01 | 02 | 1 | LIVE-03 | unit | `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts -t "coalesces mic frames"` | yes | pending |
| 109-02-02 | 02 | 1 | LIVE-04 | unit | `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts -t "barge-in"` | yes | pending |
| 109-02-03 | 02 | 1 | LIVE-05 | unit | `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts -t "turn_complete|generation_complete|interrupted"` | yes | pending |
| 109-02-04 | 02 | 1 | LIVE-03 | unit | `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts -t "plays Gemini 24kHz PCM output"` | yes | pending |
| 109-03-01 | 03 | 2 | LIVE-05 | unit | `uv run pytest tests/unit/test_voice_session.py -k "auto_save or finalize"` | yes | pending |
| 109-03-02 | 03 | 2 | LIVE-06 | manual | `.planning/phases/109-gemini-live-brainstorm-reliability/109-MANUAL-UAT.md` | yes | pending |
| 109-03-03 | 03 | 2 | LIVE-06 | static | `rg -n "GEMINI_LIVE_MODEL|ephemeral|Live API" .env.example docs deployment .planning/phases/109-gemini-live-brainstorm-reliability` | partial | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements:
- `tests/unit/test_voice_session.py`
- `frontend/__tests__/hooks/useVoiceSession.test.ts`
- Current FastAPI and Next/Vitest test setup

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real 4-turn brainstorm | LIVE-04, LIVE-05, LIVE-06 | Requires live Gemini audio and browser mic permissions | Start brainstorm, complete greeting -> user -> agent -> user -> agent, then end and confirm analysis/Vault save |
| User interruption | LIVE-04 | Requires real playback and browser AEC | Interrupt agent while speaking; confirm playback stops and user speech is captured |
| Refresh/reconnect | LIVE-02, LIVE-05 | Requires browser lifecycle | Refresh mid-session, continue from transcript, finalize |
| Mobile browser smoke | LIVE-03, LIVE-04 | Browser audio behavior differs | Run one start/speak/pause/reply/end flow on mobile |
| Provider reset/resumption | LIVE-02 | Hard to deterministically trigger in unit tests | Use fake/short timer where possible, or inspect logs for captured resumption handles and graceful GoAway handling |

---

## Validation Sign-Off

- [x] All tasks have automated verify or manual UAT dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all missing references
- [x] No watch-mode flags
- [x] Feedback latency target < 180s for focused checks
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending execution
