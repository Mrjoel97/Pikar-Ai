---
phase: 109-gemini-live-brainstorm-reliability
plan: 03
type: verification
wave: 2
depends_on:
  - 109-01-backend-live-bridge-alignment-PLAN.md
  - 109-02-frontend-audio-turn-taking-PLAN.md
files_modified:
  - .planning/phases/109-gemini-live-brainstorm-reliability/109-MANUAL-UAT.md
  - docs/deploy/voice-brainstorm-live-api.md
  - .env.example
  - deployment/cloudflare/edge-api/README.md
autonomous: true
requirements:
  - LIVE-02
  - LIVE-05
  - LIVE-06

must_haves:
  truths:
    - "Manual UAT covers real browser audio behavior that cannot be fully represented by unit tests."
    - "Deployment docs state the required env vars, WebSocket path, Cloudflare proxy behavior, and safe model/voice configuration."
    - "Direct browser-to-Gemini Live is documented only as a deferred feature-flagged path using ephemeral tokens; no browser API key is introduced."
    - "Phase execution ends with a clear verification checklist for 4-turn, interruption, refresh/reconnect, mobile, and final Vault save."
  artifacts:
    - path: ".planning/phases/109-gemini-live-brainstorm-reliability/109-MANUAL-UAT.md"
      provides: "Manual end-to-end verification checklist"
      contains: "4-turn brainstorm"
    - path: "docs/deploy/voice-brainstorm-live-api.md"
      provides: "Operator/deployment guide for Live API brainstorm configuration"
      contains: "GEMINI_LIVE_MODEL"
    - path: "deployment/cloudflare/edge-api/README.md"
      provides: "WebSocket proxy note for voice brainstorm"
      contains: "/ws/voice"
  key_links:
    - from: "Production operator"
      to: "Brainstorm Live API env/config"
      via: "docs/deploy/voice-brainstorm-live-api.md"
      pattern: "ephemeral token"
---

<objective>
Close Phase 109 with production-grade verification artifacts and deployment documentation, and document the safe future direct-live path without implementing it prematurely.
</objective>

<execution_context>
@C:/Users/expert/.codex/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/109-gemini-live-brainstorm-reliability/109-CONTEXT.md
@.planning/phases/109-gemini-live-brainstorm-reliability/109-RESEARCH.md
@.planning/phases/109-gemini-live-brainstorm-reliability/109-VALIDATION.md
@deployment/cloudflare/edge-api/src/index.ts
@deployment/cloudflare/edge-api/README.md
@docs/deploy/workflow-worker.md
@.env.example
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Create manual UAT checklist for real Live brainstorm behavior</name>
  <files>.planning/phases/109-gemini-live-brainstorm-reliability/109-MANUAL-UAT.md</files>
  <behavior>
  Complete the scaffolded checklist so QA can run it locally/staging after Plans 01 and 02 land.
  </behavior>
  <action>
  1. Open the existing `109-MANUAL-UAT.md` scaffold.
  2. Ensure it has sections for prerequisites, environment, test account, and log filters.
  3. Ensure it has checkboxes for:
     - desktop 4-turn brainstorm
     - user interruption
     - browser refresh/reconnect continuation
     - mobile smoke
     - session timeout/wrap-up
     - explicit finalize and Knowledge Vault save
     - auto-save on tab close/network drop
  4. Include expected server log patterns: session started, first user chunk, input transcript, generation/audio output, turn complete, reconnect/resumption if triggered, finalize save.
  </action>
  <verify>
    <automated>rg -n "LIVE-01|LIVE-02|LIVE-03|LIVE-04|LIVE-05|LIVE-06|4-turn brainstorm|interruption|refresh/reconnect|mobile|timeout|finalize|Knowledge Vault|auto-save" .planning/phases/109-gemini-live-brainstorm-reliability/109-MANUAL-UAT.md</automated>
  </verify>
  <done>
  - Manual UAT file exists and maps every LIVE requirement to at least one check.
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Document deployment configuration and Cloudflare WebSocket expectations</name>
  <files>docs/deploy/voice-brainstorm-live-api.md, .env.example, deployment/cloudflare/edge-api/README.md</files>
  <behavior>
  Make production configuration explicit so operators can deploy and diagnose the Live brainstorm path.
  </behavior>
  <action>
  1. Create `docs/deploy/voice-brainstorm-live-api.md`.
  2. Document required and optional env vars:
     - `GOOGLE_GENAI_USE_VERTEXAI`
     - `GOOGLE_CLOUD_PROJECT`
     - `GOOGLE_CLOUD_LOCATION`
     - `GOOGLE_API_KEY` local fallback only
     - `GEMINI_LIVE_MODEL`
     - `GEMINI_VOICE_NAME`
     - `GEMINI_LIVE_SILENCE_MS`
     - frontend voice tuning env vars
  3. Document the WebSocket path and Cloudflare edge behavior: `/ws/voice/{session_id}` upgrade is proxied to Cloud Run.
  4. Document common failures and what logs to inspect.
  5. Update `.env.example` only if Plan 01 did not already add all env comments.
  6. Update `deployment/cloudflare/edge-api/README.md` with a short note that WebSocket upgrades bypass body rewriting/rate-limit response shaping.
  </action>
  <verify>
    <automated>rg -n "GEMINI_LIVE_MODEL|/ws/voice|WebSocket|Gemini Live" docs/deploy/voice-brainstorm-live-api.md .env.example deployment/cloudflare/edge-api/README.md</automated>
  </verify>
  <done>
  - Docs mention all required env/config knobs and the Cloudflare upgrade path.
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Write deferred ephemeral-token direct-live design</name>
  <files>docs/deploy/voice-brainstorm-live-api.md</files>
  <behavior>
  Capture the official-docs direct-live path as a safe future option without changing production behavior in this phase.
  </behavior>
  <action>
  1. Add a "Deferred direct Live path" section.
  2. State that any browser direct Live connection must use backend-minted ephemeral tokens and must not expose `GOOGLE_API_KEY`.
  3. Define the future endpoint shape at a high level: authenticated request in, short-lived model/config-constrained token out.
  4. Document the extra work needed before enabling direct mode:
     - transcript/event mirror to backend
     - finalize compatibility
     - feature flag
     - rate limit and abuse controls
     - model/config constraint tests
  5. Add a note that server-to-server bridge remains the Phase 109 production path.
  </action>
  <verify>
    <automated>rg -n "ephemeral token|direct Live|GOOGLE_API_KEY|feature flag" docs/deploy/voice-brainstorm-live-api.md</automated>
  </verify>
  <done>
  - Direct path is documented as deferred and safe-by-design.
  - No production code path uses browser direct Live in this phase.
  </done>
</task>

</tasks>

<verification>
- `uv run pytest tests/unit/test_voice_session.py`
- `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts`
- `rg -n "GEMINI_LIVE_MODEL|/ws/voice|ephemeral token" docs .env.example deployment/cloudflare/edge-api/README.md .planning/phases/109-gemini-live-brainstorm-reliability`
- Manual UAT from `109-MANUAL-UAT.md`
</verification>

<success_criteria>
- LIVE-02, LIVE-05, and LIVE-06 have documented manual coverage.
- Operators have enough docs to configure and debug the Live brainstorm path.
- Future direct-live mode is captured without increasing current-phase risk.
</success_criteria>
