# Pikar AI Live User QA Plan

Date created: 2026-06-03

This plan is the working checklist for testing Pikar AI like a real user. It covers the public app, authenticated dashboard, admin surfaces, agent/business logic, integrations, and live browser testing. The goal is not just to click pages. The goal is to prove that every important user promise works end to end, with evidence.

## Testing Principles

- Test as named personas, not as anonymous developers.
- Start with the highest-value user journeys, then expand into edge cases.
- Every live test must record: user role, browser URL, action, expected result, actual result, network/API failures, console errors, screenshots, and follow-up issue.
- A workflow only passes when the UI state, backend state, and user-facing output agree.
- Business logic must be tested at three levels: unit/API behavior, browser behavior, and persistence/event behavior.
- External integrations should be tested with sandbox accounts or clearly documented mock mode.
- Do not treat "page loads" as success. Success means the user can finish the job they came to do.

## Test Environments

- Local frontend: `npm run dev --prefix frontend`
- Local backend: `make local-backend`
- Local full app: `make playground`
- Admin app if tested separately: `npm run dev --prefix admin`
- Production/staging, when available: use the deployed URL and document the exact date/time tested.

## Test Users And Roles

- Visitor: unauthenticated user.
- New user: signs up and completes onboarding.
- Solopreneur persona.
- Startup persona.
- SME persona.
- Enterprise persona.
- Team member: invited user with limited access.
- Team admin/owner.
- Pikar admin/operator.
- Impersonating admin.
- Integration-connected user.
- User with missing/expired integration credentials.
- User with failed payment or restricted billing state.

## Evidence Log Template

Use this format for every manual/browser test:

```text
Test ID:
Date/time:
Environment:
Browser/session:
User/role:
Starting URL:
Preconditions:
Steps:
Expected:
Actual:
Pass/fail:
Screenshots/videos:
Console errors:
Network/API failures:
Backend/log evidence:
Data created:
Cleanup needed:
Issue link:
```

## Release Gates

- No critical or high bugs open in authentication, onboarding, chat, agent execution, billing, integrations, approvals, vault, or admin impersonation.
- No broken primary navigation routes for authenticated users.
- No browser console errors during critical journeys unless documented as harmless.
- No failed API calls on critical journeys unless the UI gives a clear recoverable state.
- All generated artifacts can be opened, downloaded, or revisited after page refresh.
- All user-owned data remains scoped to the correct user/team.
- Admin-only pages are inaccessible to non-admin users.
- Approvals, audit logs, and destructive actions leave traceable evidence.

## Phase 1: Product Surface Inventory

- [ ] List all frontend routes from `frontend/src/app`.
- [ ] List all admin routes from `frontend/src/app/admin` and `admin/src/app`.
- [ ] List all backend routers from `app/routers`.
- [ ] List all agent tools from `app/agents/tools`.
- [ ] List all services that contain business logic from `app/services`.
- [ ] Map each route to a user role.
- [ ] Map each route to backend endpoints it calls.
- [ ] Mark each route as public, authenticated, team-scoped, admin-only, or token-only.
- [ ] Mark each route as critical, important, or low-risk.
- [ ] Identify routes that are currently unreachable from navigation.
- [ ] Identify duplicate admin surfaces between `frontend/src/app/admin` and `admin/src/app`.

## Phase 2: Smoke And Infrastructure Checks

- [ ] Start backend locally.
- [ ] Start frontend locally.
- [ ] Confirm `/health/live` returns healthy.
- [ ] Confirm `/health/connections` reports Supabase/cache status.
- [ ] Confirm `/health/cache` behavior when Redis is available or unavailable.
- [ ] Confirm `/health/embeddings` reports embedding readiness.
- [ ] Confirm `/health/video` reports Veo and Remotion readiness.
- [ ] Run backend unit tests for touched critical services.
- [ ] Run frontend unit tests.
- [ ] Run frontend build.
- [ ] Run admin build if admin app is tested separately.
- [ ] Check application logs during startup for warnings that affect user testing.

## Phase 3: Public And Auth Workflows

- [ ] Public home page loads without authentication.
- [ ] Persona pages load: solopreneur, startup, SME, enterprise.
- [ ] Privacy, terms, and data deletion pages load.
- [ ] Login accepts valid credentials.
- [ ] Login rejects invalid credentials with clear messaging.
- [ ] Signup creates a new account or cleanly handles disabled signup.
- [ ] Forgot password flow sends or simulates reset.
- [ ] Reset password flow accepts a valid token.
- [ ] Auth callback handles success.
- [ ] Auth callback handles invalid state/token.
- [ ] Session persists after refresh.
- [ ] Session expires safely.
- [ ] Logout clears user state and protected data from the UI.
- [ ] Protected dashboard pages redirect unauthenticated users.

## Phase 4: New User Onboarding

- [ ] New user lands on onboarding.
- [ ] Business-context step saves user inputs.
- [ ] Agent-setup step saves selected agent/persona preferences.
- [ ] Preferences step saves notifications, goals, or settings.
- [ ] Processing step transitions to dashboard.
- [ ] Onboarding can resume after refresh.
- [ ] Onboarding handles missing required fields.
- [ ] Onboarding handles backend/API failure.
- [ ] Completed onboarding does not repeat unexpectedly.
- [ ] Dashboard reflects onboarding choices.

## Phase 5: Core Dashboard Workflows

- [ ] Dashboard loads personalized summary.
- [ ] Command center shows relevant actions and agent state.
- [ ] Departments page lists departments.
- [ ] Department detail page loads for a valid department.
- [ ] Finance page loads metrics, actions, and agent controls.
- [ ] Sales page loads pipeline/follow-up surfaces.
- [ ] Content page loads planning/generation surfaces.
- [ ] Compliance page loads health and task surfaces.
- [ ] Reports page loads report cards/history.
- [ ] Community page loads without breaking authenticated session.
- [ ] Learning page loads training/recommendations.
- [ ] Portfolio page loads governance/project state.
- [ ] History page shows prior activity.
- [ ] Settings pages load and save changes.
- [ ] Billing page shows current plan/state.
- [ ] Team page lists members.
- [ ] Team join flow accepts a valid invite.
- [ ] Invalid team invite gives a useful error.

## Phase 6: Chat, Agent, And Streaming Workflows

- [ ] Start a fresh chat session.
- [ ] Send a simple prompt and receive a streamed response.
- [ ] Send a prompt that triggers a known tool.
- [ ] Confirm tool progress is visible to the user.
- [ ] Confirm final answer reflects tool result.
- [ ] Refresh during a session and confirm history recovery.
- [ ] Switch or select persona and confirm runtime behavior changes.
- [ ] Confirm model fallback behavior is user-safe when primary model fails.
- [ ] Confirm SSE stream handles reconnects.
- [ ] Confirm long-running response does not freeze the UI.
- [ ] Confirm failed tool call creates clear user-facing error or retry path.
- [ ] Confirm action history records agent actions.
- [ ] Confirm generated widgets render correctly in chat.

## Phase 7: Brain Dump And Voice Workflows

- [ ] Open brain dump page.
- [ ] Enter text brain dump and submit.
- [ ] Start voice brainstorming session.
- [ ] Stop voice brainstorming session.
- [ ] Confirm transcript or summary appears.
- [ ] Confirm generated tasks/ideas are saved.
- [ ] Confirm voice permission denial is handled.
- [ ] Confirm backend voice session route handles session creation.
- [ ] Confirm reconnect after interruption.
- [ ] Confirm no duplicate sessions after repeated starts.

## Phase 8: Workspace And Vault Workflows

- [ ] Workspace page loads.
- [ ] Workspace events stream connects.
- [ ] Upload a document.
- [ ] Upload an image.
- [ ] Upload a video or media file if supported.
- [ ] Confirm uploaded item appears in vault.
- [ ] Open vault item detail/viewer.
- [ ] Download vault item.
- [ ] Rename or update metadata if supported.
- [ ] Delete or archive item if supported.
- [ ] Confirm deleted item cannot be accessed by direct URL.
- [ ] Confirm vault actions work after refresh.
- [ ] Confirm team/user scoping prevents cross-user access.
- [ ] Confirm knowledge-vault embeddings or processing status appears.
- [ ] Confirm failed upload gives progress/error feedback.

## Phase 9: Documents, Images, Video, And Generated Artifacts

- [ ] Generate a document through chat/tool flow.
- [ ] Confirm document widget renders.
- [ ] Open/download generated document.
- [ ] Confirm document text extraction works on upload.
- [ ] Confirm OCR works for supported image/PDF input.
- [ ] Generate an image if image service is configured.
- [ ] Confirm image widget renders and persists.
- [ ] Generate a short video if Veo is configured.
- [ ] Confirm video widget renders and persists.
- [ ] Generate or render longer video if Remotion is configured.
- [ ] Confirm video/audio policy behavior.
- [ ] Confirm failed generation shows recoverable status.
- [ ] Confirm artifacts can be found from history/vault after refresh.

## Phase 10: Workflows And Approvals

- [ ] Workflows dashboard lists templates.
- [ ] Generate workflow from prompt.
- [ ] Open workflow editor for a template.
- [ ] Start a workflow.
- [ ] Confirm active workflow appears.
- [ ] Confirm workflow progress updates.
- [ ] Confirm completed workflow appears in completed list.
- [ ] Confirm workflow status is consistent between UI and backend.
- [ ] Trigger workflow requiring approval.
- [ ] Approval queue shows pending approval.
- [ ] Approve from dashboard.
- [ ] Reject from dashboard.
- [ ] Open token-based approval page.
- [ ] Confirm invalid/expired approval token fails safely.
- [ ] Confirm approval audit entry is created.
- [ ] Confirm workflow resumes after approval.

## Phase 11: App Builder Workflows

- [ ] Open app builder landing page.
- [ ] Create new app/project.
- [ ] Complete design brief or prompt enhancement.
- [ ] Confirm research phase starts.
- [ ] Confirm building phase starts.
- [ ] Confirm verifying phase starts.
- [ ] Confirm shipping phase starts or gives clear unavailable state.
- [ ] Open existing project.
- [ ] Refresh during build and confirm state recovery.
- [ ] Confirm generated screens/assets persist.
- [ ] Confirm errors do not orphan a project.

## Phase 12: Initiatives, Governance, And Org Workflows

- [ ] Create a new initiative.
- [ ] Open initiative detail.
- [ ] Update initiative status or metadata.
- [ ] Confirm governance portfolio reflects initiative.
- [ ] Confirm org chart loads.
- [ ] Confirm team settings affect role/access behavior.
- [ ] Confirm governance audit logs record important actions.
- [ ] Confirm restricted users cannot edit owner-only data.

## Phase 13: Integrations And External Services

- [ ] Open integrations settings.
- [ ] Configure API connection.
- [ ] Configure webhook.
- [ ] Connect Google Workspace if sandbox credentials exist.
- [ ] Connect Gmail if sandbox credentials exist.
- [ ] Connect calendar if sandbox credentials exist.
- [ ] Connect social provider if sandbox credentials exist.
- [ ] Connect Stripe or billing provider if sandbox exists.
- [ ] Connect HubSpot/CRM if sandbox exists.
- [ ] Confirm expired credentials show reconnect path.
- [ ] Confirm disconnected integrations do not leak old credentials.
- [ ] Confirm integration health endpoint/status reflects reality.
- [ ] Confirm webhook signature verification.
- [ ] Confirm outbound webhook delivery/retry behavior.

## Phase 14: Billing And Plan Logic

- [ ] Billing page shows correct plan.
- [ ] Upgrade action works or cleanly routes to billing provider.
- [ ] Downgrade/cancel action works or cleanly routes to provider.
- [ ] Failed payment state restricts only intended features.
- [ ] Usage or plan limits are enforced.
- [ ] BYOK/API provider settings save correctly.
- [ ] Missing provider key produces clear user guidance.
- [ ] Admin billing dashboard reflects customer state.

## Phase 15: Admin And Operator Workflows

- [ ] Admin login works.
- [ ] Non-admin cannot access admin pages.
- [ ] Admin dashboard loads.
- [ ] Admin users list loads.
- [ ] Admin user detail loads.
- [ ] Admin impersonation starts.
- [ ] Impersonation banner is visible.
- [ ] Admin exits impersonation.
- [ ] Admin analytics page loads.
- [ ] Admin approvals page loads.
- [ ] Admin audit log loads.
- [ ] Admin billing page loads.
- [ ] Admin config page loads and validates changes.
- [ ] Admin integrations page loads.
- [ ] Admin knowledge page upload/list actions work.
- [ ] Admin monitoring page loads current status.
- [ ] Admin observability page loads if available.
- [ ] Admin settings page enforces role permissions.

## Phase 16: Business Logic API Probes

- [ ] Account/session APIs enforce authentication.
- [ ] Team APIs enforce role-based access.
- [ ] Vault APIs enforce user/team scoping.
- [ ] Workspace event APIs send heartbeat and updates.
- [ ] Workflow APIs validate workflow inputs.
- [ ] Workflow execution APIs reject invalid transitions.
- [ ] Approval APIs validate tokens and permissions.
- [ ] Configuration APIs validate provider settings.
- [ ] Integration APIs protect secrets and credentials.
- [ ] Billing APIs enforce plan limits.
- [ ] Admin APIs reject non-admin users.
- [ ] File APIs reject unsafe paths and unauthorized files.
- [ ] Health APIs do not expose secrets.
- [ ] Data export/deletion APIs are scoped to the correct user.

## Phase 17: Negative And Abuse Cases

- [ ] Directly open protected URLs while logged out.
- [ ] Directly open another user's object URL.
- [ ] Submit empty forms.
- [ ] Submit oversized text prompts.
- [ ] Upload unsupported file type.
- [ ] Upload large file near configured limit.
- [ ] Click submit buttons repeatedly.
- [ ] Navigate away during long-running operation.
- [ ] Refresh during streaming.
- [ ] Simulate offline/network failure.
- [ ] Test expired sessions during active workflow.
- [ ] Test browser back/forward through auth and onboarding.
- [ ] Test malformed approval/invite tokens.
- [ ] Test prompt injection attempts against tools with external actions.

## Phase 18: Accessibility, Responsive, And Usability

- [ ] Keyboard navigation works for critical flows.
- [ ] Focus states are visible.
- [ ] Modals trap and restore focus.
- [ ] Forms have labels and errors.
- [ ] Important buttons have accessible names.
- [ ] Mobile viewport works for auth, onboarding, dashboard, chat, vault, approvals.
- [ ] Tablet viewport works for dashboard/admin tables.
- [ ] Desktop viewport works for dense admin and workflow pages.
- [ ] No text overlaps or clips in critical views.
- [ ] Loading states are visible and do not shift layout badly.
- [ ] Empty states explain what the user can do next.

## Phase 19: Live Browser Test Runs

Each run should use the in-app Browser and capture screenshots on failures.

- [ ] Run visitor journey: home, persona page, signup/login entry.
- [ ] Run new user journey: signup/login, onboarding, first dashboard.
- [ ] Run solopreneur journey: onboarding persona, chat, first generated action.
- [ ] Run team journey: owner invites member, member joins, permissions checked.
- [ ] Run content journey: generate content, create artifact, review in vault/history.
- [ ] Run finance journey: finance dashboard, agent prompt, report/action output.
- [ ] Run workflow journey: generate/start workflow, approve/reject, completion.
- [ ] Run vault journey: upload, process, open, download, delete/archive.
- [ ] Run voice journey: brain dump, voice session, summary/action creation.
- [ ] Run admin journey: login, inspect user, impersonate, exit, audit log.
- [ ] Run failure journey: expired credentials, failed upload, invalid token, interrupted stream.

## Phase 20: Bug Triage And Fix Loop

- [ ] Create an issue for every failed test with evidence.
- [ ] Assign severity: critical, high, medium, low.
- [ ] Mark whether failure is UI, API, data, business logic, integration, performance, or permissions.
- [ ] Add reproduction steps.
- [ ] Add expected vs actual behavior.
- [ ] Add screenshots/log excerpts.
- [ ] Fix highest severity issues first.
- [ ] Re-run the exact failed test after fix.
- [ ] Re-run neighboring workflows that share the same code path.
- [ ] Update this plan when a new workflow or feature is discovered.

## Suggested First Test Session

1. Start local backend and frontend.
2. Confirm health endpoints.
3. Open the app as a visitor.
4. Log in as a normal user.
5. Complete or verify onboarding state.
6. Send one chat prompt that should trigger a real tool.
7. Upload one file to vault.
8. Start one workflow and complete one approval.
9. Open admin as an admin user and test impersonation.
10. Record every failure in the evidence log.

## Definition Of Done

- Every critical route has at least one live-browser pass.
- Every critical backend router has at least one permission/business-logic check.
- Every critical agent tool has at least one success and one failure-path test.
- Every workflow that mutates data leaves visible, correct persisted state.
- Every admin-only function is proven blocked for normal users.
- Every release-blocking issue has been fixed and re-tested.
