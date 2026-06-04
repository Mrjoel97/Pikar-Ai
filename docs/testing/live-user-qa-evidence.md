# Live User QA Evidence Log

## 2026-06-03 Session 1

Environment:
- Workspace: `C:\Users\expert\Documents\PKA\Pikar-Ai`
- Frontend: `http://localhost:3000`
- Backend: `http://127.0.0.1:8000`
- Browser: Codex in-app browser
- Logs: `tmp/qa-live/frontend.log`, `tmp/qa-live/frontend.err.log`, `tmp/qa-live/backend.err.log`, `tmp/qa-live/backend-noreload.err.log`

### Infrastructure And Health

- PASS: Frontend dev server started on `http://localhost:3000`.
- PASS: Backend eventually reached `/health/live` with HTTP 200.
- PASS: `/health/connections` returned HTTP 200 and Supabase pools reported created clients.
- DEGRADED: `/health/cache` returned HTTP 200 with `status: degraded`, `connected: false`; startup logs show Redis connection failure.
- PASS: `/health/embeddings` returned HTTP 200 on a 45-second timeout window with Gemini embedding model `text-embedding-004`.
- PASS: `/health/video` returned HTTP 200 with Vertex/Veo and Remotion configured.

Notes:
- Initial backend probes to `/health/live` were refused before application startup completed.
- Backend logs show `ERROR:app.services.cache:Failed to connect to Redis`, then `Application startup complete`.

### Browser Auth Route Checks

Test: Login page
- Starting URL: `http://localhost:3000/auth/login`
- Result: PARTIAL PASS
- Evidence: Page eventually rendered with Pikar AI branding, `Welcome Back`, email/password fields, forgot link, sign-in button, Google button, signup link, and cookie consent.
- Issue: Browser navigation timed out before page settled.

Test: Signup page
- Starting URL: `http://localhost:3000/auth/signup`
- Result: PARTIAL PASS
- Evidence: Page rendered with `Create Account`, full name, email, password, confirm password, create account, Google signup, and sign-in link.
- Issue: Load state timed out; first compile in Next logs took 97 seconds.

Test: Protected dashboard redirect
- Starting URL: `http://localhost:3000/dashboard`
- Result: PASS with performance warning
- Evidence: Unauthenticated user redirected to `http://localhost:3000/auth/login?next=%2Fdashboard`.
- Issue: Load state timed out; rendered login page was visible.

Test: Forgot password page
- Starting URL: `http://localhost:3000/auth/forgot-password`
- Result: PARTIAL PASS
- Evidence: Page rendered with `Forgot Password?`, email textbox, send reset link button, and back-to-login link.
- Issue: Browser navigation timed out before completion. Dev overlay indicated one issue badge on this route.

Test: Invalid login
- Result: BLOCKED BY TEST HARNESS
- Evidence: Browser automation failed filling the `type=email` field with: `setRangeText` not supported for input type `email`.
- Follow-up: Re-test with an alternate input method or Playwright test runner before marking app behavior.

### Public Route Checks

HTTP route pass:
- PASS: `/` returned HTTP 200 with large HTML payload around 415 KB.
- PASS: `/solopreneur` returned HTTP 200.
- PASS: `/startup` returned HTTP 200.
- PASS: `/sme` returned HTTP 200.
- PASS: `/enterprise` returned HTTP 200.
- PASS: `/privacy` returned HTTP 200.
- PASS: `/terms` returned HTTP 200.

Browser route pass:
- PARTIAL PASS: `/privacy` reached `http://localhost:3000/privacy` and rendered `Privacy Policy`, `Last updated: March 30, 2026`, navigation, and policy sections.
- Issue: Browser navigation timed out before page load completed.
- BLOCKED: Public browser batch starting at `/` failed with low-level browser loading error `(-3) loading 'http://localhost:3000/'`.

### Performance Findings

- Auth route cold starts are too slow for live QA:
  - `/auth/signup`: HTTP 200 in 97s on first compile.
  - `/auth/forgot-password`: HTTP 200 in 49s on first compile.
  - `/auth/login?next=%2Fdashboard`: HTTP 200 in 11s on one run.
- Warm runs improved substantially, but live browser tests still saw load-state timeouts.
- Home route returned a large HTML payload around 415 KB and logged `GET / 200 in 6.5s`.

### Open Issues From Session 1

- [HIGH] Redis/cache is degraded locally; confirm whether local QA expects Redis running or graceful degraded mode.
- [HIGH] First route compiles are extremely slow under Next/Turbopack dev server, causing browser test timeouts.
- [MEDIUM] Auth pages render visibly but do not reliably reach browser load state during live QA.
- [MEDIUM] Public pages can return HTTP 200 but still trigger browser navigation timeouts.
- [MEDIUM] Forgot-password route shows a Next dev issue badge; inspect overlay details in a focused follow-up.
- [LOW] Browser automation `fill` failed on email input; verify with another input strategy before treating as app issue.

### Next Recommended Tests

- Run public/persona route browser pass.
- Inspect the forgot-password dev overlay issue.
- Run authenticated journey with a known test user.
- Re-test invalid login with a direct Playwright or alternate browser input method.
- Start Redis locally or document that degraded cache is expected for local QA.

## 2026-06-03 Session 2

Goal: fix issues found in Session 1 and continue live browser testing.

### Fixes Applied

- Fixed forgot-password page:
  - Removed inline `fonts.googleapis.com` `@import`.
  - Replaced Material Symbols text icons with inline SVG icons.
  - Added an accessible email label.
- Fixed unauthenticated auth-page prefetching:
  - Removed login prefetch to `/dashboard/command-center`.
  - Removed signup prefetch to `/onboarding`.
- Fixed password visibility controls:
  - Login password visibility button now has `Show password` / `Hide password` labels and toggles the input type.
  - Signup password and confirm-password visibility buttons now have accessible labels and toggle their fields.
- Improved Redis local QA behavior:
  - Added configurable Redis socket/connect timeouts with faster defaults.
  - Updated Docker Compose Redis so it does not require a default password when `REDIS_PASSWORD` is unset.

### Verification

Automated:
- PASS: `npm run lint --prefix frontend -- src/app/auth/login/LoginPage.tsx src/app/auth/signup/SignupPage.tsx src/app/auth/forgot-password/page.tsx`
- PASS: `uv run pytest tests/unit/test_cache_redis_scaling.py tests/unit/test_health_endpoints.py`
- BLOCKED: `tests/unit/services/test_cache_with_age.py` requires a real Redis instance. Docker Desktop is not running, so local Redis could not be started.

Health:
- PASS: `/health/live` returned HTTP 200.
- DEGRADED BUT FASTER: `/health/cache` still reports Redis degraded because no Redis process is running, but response time improved from about 9.2s to about 2.1s.
- PASS: `/health/embeddings` returned HTTP 200.
- PASS: `/health/video` returned HTTP 200.

Browser retest:
- PASS: `/auth/login` reached load state in about 7.1s, rendered correctly, and had no dev issue badge.
- PASS: `/auth/signup` reached load state in about 4.9s, rendered correctly, and had no dev issue badge.
- PASS: `/auth/forgot-password` reached load state in about 5.8s, rendered correctly, had no dev issue badge, and no Material Symbols text leakage.
- PASS: `/dashboard` as an unauthenticated user redirected to `/auth/login?next=%2Fdashboard` in about 3.7s.
- PASS: `/privacy` reached load state in about 6.1s.
- PASS: `/terms` reached load state in about 4.2s.
- PASS: `/` reached load state in about 6.8s.
- PASS: Login password visibility control changed from `Show password` to `Hide password` after click.

Remaining blockers:
- Redis is still unavailable locally because Docker Desktop is not running and no standalone Redis server is listening.
- Invalid-login browser test remains blocked by the in-app browser `fill` behavior on `type=email`; use a dedicated Playwright runner or provide manual input for that one path.
- Authenticated dashboard/onboarding/chat/vault/workflow journeys need a known safe test user or an approved signup flow.

## 2026-06-03 Session 3

Goal: continue safe unauthenticated testing and fix newly surfaced route issues.

### Additional Routes Tested

- PASS: `/settings` as unauthenticated user redirects to `/auth/login?next=%2Fsettings`.
- PASS: `/admin` as unauthenticated user redirects to `/auth/login?next=%2Fadmin`.
- PASS: `/data-deletion` renders public deletion information.
- PASS: `/data-deletion/status` renders `Request Not Found` for a missing request id.
- PASS: `/auth/reset-password` renders reset form.
- FAIL THEN FIXED: `/invite/not-a-real-token` initially rendered no useful visible state, then `Failed to fetch`.

### Fixes Applied

- Fixed reset-password page:
  - Replaced Material Symbols text icons with inline SVG icons.
  - Added working password and confirm-password visibility toggles.
  - Added accessible `Show new password` / `Show confirm password` labels.
- Fixed public invite details backend contract:
  - Added `WorkspaceService.get_invite_details`.
  - Invalid invite tokens now return HTTP 404 instead of HTTP 500.
- Fixed invite page local-browser API path:
  - Added same-origin Next API proxy at `/api/teams/invites/details`.
  - Updated `/invite/[token]` to call the same-origin proxy instead of direct `localhost:8000`, which the in-app browser blocks.
  - Added accessible loading text and mapped backend `message` errors.

### Verification

Automated:
- PASS: `npm run lint --prefix frontend -- src/app/invite/[token]/page.tsx src/app/api/teams/invites/details/route.ts src/app/auth/reset-password/ResetPasswordPage.tsx src/app/auth/login/LoginPage.tsx src/app/auth/signup/SignupPage.tsx src/app/auth/forgot-password/page.tsx`
- PASS: `uv run pytest tests/unit/app/routers/test_teams_public.py tests/unit/test_cache_redis_scaling.py tests/unit/test_health_endpoints.py`

Backend/API:
- PASS: `GET /teams/invites/details?token=not-a-real-token` returns HTTP 404 with `Invite token not found or has already been used.`
- PASS: `GET /api/teams/invites/details?token=not-a-real-token` returns HTTP 404 through the frontend proxy.

Browser:
- PASS: `/auth/reset-password` reaches load state, has no dev issue badge, no Material Symbols leakage, and exposes named password controls.
- PASS: `/invite/not-a-real-token` renders `Invite token not found or has already been used.`
- PASS: `/invite/not-a-real-token` has no `Failed to fetch` alert after proxy fix.
- PASS: `/invite/not-a-real-token` has no dev issue badge after proxy fix.

Remaining blockers:
- Redis remains degraded until Docker Desktop or a standalone Redis server is running.
- Authenticated app journeys still require a known safe test user or approval to create/use a test account.
- Browser automation still cannot fill `type=email` inputs in this in-app browser runtime, so invalid-login form submission needs a different runner or manual input.

## 2026-06-04 Session 5

Goal: use an approved live QA user to test authenticated flows, fix issues found, and prepare deployable evidence.

### Test User

- Created and confirmed a dedicated Supabase QA user for live browser testing.
- Used Playwright CLI for auth form input because the in-app browser runtime cannot reliably fill `type=email` fields.

### New Issues Found

- FAIL THEN FIXED: local frontend was calling the production API from `frontend/.env`, causing localhost CORS failures for onboarding status calls.
- FAIL THEN FIXED: onboarding sometimes rendered a blank first step in React Strict Mode because the initial greeting was scheduled in a timeout that could be cleaned up before it committed.
- FAIL THEN FIXED: onboarding completion could redirect to dashboard before the session/proxy layer knew the user was onboarded, causing a bounce back to `/onboarding`.
- REMAINING: command-center dashboard shell renders after onboarding, but dashboard summary/KPI data can time out and fall back to the loading/timeout state.
- REMAINING ENVIRONMENT BLOCKER: Redis tests pass when Docker Redis is healthy, but the local Docker daemon later stopped exposing port `6379` and returned an internal server error while inspecting `redis:alpine`.

### Fixes Applied

- Added ignored local QA overrides in `frontend/.env.local` so localhost frontend calls localhost backend during testing.
- Changed onboarding chat to add the first assistant message synchronously.
- Removed the fragile onboarding page readiness gate so non-completed users render the onboarding chat after status resolution.
- Set onboarding completion cookies before dashboard redirect to avoid the post-complete bounce.
- Increased default Redis socket/connect timeouts to reduce Docker Desktop flakiness while keeping health checks bounded.

### Verification

Automated:
- PASS: `npm run lint --prefix frontend -- src/app/onboarding/page.tsx src/app/onboarding/components/OnboardingChat.tsx src/app/onboarding/components/OnboardingTransition.tsx src/hooks/useSessionMonitor.ts src/app/invite/[token]/page.tsx src/app/api/teams/invites/details/route.ts src/app/auth/login/LoginPage.tsx src/app/auth/signup/SignupPage.tsx src/app/auth/forgot-password/page.tsx src/app/auth/reset-password/ResetPasswordPage.tsx`
- PASS: `python -m pytest tests/unit/app/routers/test_teams_public.py`
- BLOCKED: Redis integration tests could not complete after Docker Desktop stopped exposing local Redis on `127.0.0.1:6379` and `docker compose up -d redis` returned a Docker daemon 500 error.

Browser:
- PASS: QA user login succeeds against Supabase.
- PASS: onboarding agent naming step renders and accepts input.
- PASS: discovery answers submit and `/onboarding/extract-context` returns HTTP 200.
- PASS: persona reveal renders `Solopreneur`.
- PASS: onboarding preferences render and submit.
- PASS: `/onboarding/business-context`, `/onboarding/preferences`, `/onboarding/agent-setup`, and `/onboarding/complete` return HTTP 200.
- PASS: after completion, direct navigation to `/dashboard/command-center` renders the dashboard shell and quick actions.
- PARTIAL: dashboard data endpoints can time out; UI shows the timeout fallback instead of blocking the whole shell.

### Follow-Up Queue

- Investigate `/briefing/dashboard-summary` and `/kpis/persona` latency for newly onboarded users.
- Restart or repair Docker Desktop before rerunning Redis-backed local integration tests.
- Add a repeatable Playwright auth/onboarding spec now that the live-user path is known.

## 2026-06-03 Session 4

Goal: retest the invite fix after a clean frontend rebuild and continue browser QA.

### New Issue Found

- FAIL THEN FIXED: after clearing `.next` and restarting the frontend, `/invite/not-a-real-token` was briefly redirected to `/auth/login` / unavailable before the route finished compiling.
- Root cause: the global session monitor did not include `/invite` in its public-page allowlist, so unauthenticated invite recipients could be redirected away after hydration.
- Additional lint issue found while editing the same hook: `Date.now()` was called during render in `useSessionMonitor`.

### Fixes Applied

- Added `/invite` to the session monitor public-path allowlist.
- Moved the session monitor initial activity timestamp from render-time `Date.now()` into the browser effect.

### Verification

Automated:
- PASS: `npm run lint --prefix frontend -- src/app/invite/[token]/page.tsx src/app/api/teams/invites/details/route.ts src/hooks/useSessionMonitor.ts`

Backend/API:
- PASS: `GET /teams/invites/details?token=not-a-real-token` returns HTTP 404 with `Invite token not found or has already been used.`
- PASS: `GET /api/teams/invites/details?token=not-a-real-token` returns HTTP 404 through the frontend proxy.

Browser:
- PASS: `/invite/not-a-real-token` stays on the invite URL.
- PASS: `/invite/not-a-real-token` renders `Invite token not found or has already been used.`
- PASS: `/invite/not-a-real-token` has no visible `Failed to fetch` text.
- PASS: final browser sweep confirmed `/auth/login` and `/auth/reset-password` have no Material Symbols text leakage and expose working password visibility controls.
- PASS: final browser sweep confirmed `/dashboard` redirects unauthenticated visitors to `/auth/login?next=%2Fdashboard`.

Remaining blockers:
- Redis remains degraded until Docker Desktop or a standalone Redis server is running.
- Authenticated app journeys still require a known safe test user or approval to create/use a test account.
- Browser automation still cannot fill `type=email` inputs in this in-app browser runtime, so invalid-login form submission needs a different runner or manual input.
