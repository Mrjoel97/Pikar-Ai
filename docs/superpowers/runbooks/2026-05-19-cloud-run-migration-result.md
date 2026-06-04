# Cloud Run new-project migration — result runbook

**Date:** 2026-05-19
**Source spec:** [`docs/superpowers/specs/2026-05-19-cloud-run-new-project-migration-design.md`](../specs/2026-05-19-cloud-run-new-project-migration-design.md) (commit `a0b540f0`)
**Source plan:** [`docs/superpowers/plans/2026-05-19-cloud-run-new-project-migration.md`](../plans/2026-05-19-cloud-run-new-project-migration.md) (commit `e385d413`)
**Executed by:** Claude Opus 4.7 + user, task-by-task with user gating at critical points

## Outcome

✅ **Cloud Run workload migrated from `pikar-ai-project` to `project-c3a75795-f866-4b37-8ec`.**
Users hitting `api.pikar-ai.com` now talk to the new GCP project's Cloud Run. Cloudflare DNS / routes / Worker code are unchanged — only the Workers' backend-origin secrets were updated.

## New project state (canonical reference)

| Resource | Value |
|---|---|
| Project ID | `project-c3a75795-f866-4b37-8ec` |
| Project number | `708231827042` |
| Billing account | `01E81C-67E384-CEE282` |
| Cloud Run service | `pikar-ai`, region `us-central1` |
| Cloud Run revision (initial) | `pikar-ai-00001-ks4` (100% traffic) |
| Service URLs | `https://pikar-ai-708231827042.us-central1.run.app` (project-number form) and `https://pikar-ai-hvy5nlgwaa-uc.a.run.app` (regional alias) |
| App service account | `pikar-ai@project-c3a75795-f866-4b37-8ec.iam.gserviceaccount.com` (Owner + 7 parity roles + secretAccessor) |
| Image digest | `sha256:3013958a3fbd30eb8d72034104ed8fd7e049b3834d72fe91b4175d63927488b1` |
| Image registry | `us-central1-docker.pkg.dev/project-c3a75795-f866-4b37-8ec/cloud-run-source-deploy/pikar-ai` |
| Memorystore Redis | `pikar-ai-cache`, BASIC tier, 1 GB, REDIS_7_0, host `10.255.118.67:6379` |
| Networking | **Direct VPC Egress** on `default` VPC, `default` subnet, `private-ranges-only` (substitute for VPC connector — see deviations) |
| Logs bucket | `gs://pikar-ai-c3a75-logs` |
| Secret Manager secrets | 16 secrets, all populated byte-exactly (no trailing whitespace) |
| Cloud Scheduler jobs | 5 jobs, all ENABLED (see below) |
| Cloudflare edge Worker | `pikar-edge-api` version `ce589957-157d-41de-9cd7-edbc14243fcb` |
| Cloudflare public-api Worker | `pikar-public-api` version `6e0e2bc3-3fc9-4e70-ad55-d761223bb08d` |

## Cloud Scheduler jobs (Task 20)

All 5 ENABLED, time-zone `Etc/UTC`, authentication via `X-Scheduler-Secret` header against the SCHEDULER_SECRET in Secret Manager.

| Job name | Schedule | Target POST |
|---|---|---|
| `pikar-ai-daily-report` | `0 7 * * *` (07:00 UTC daily) | `/scheduled/daily-report` |
| `pikar-ai-weekly-digest` | `0 9 * * 1` (Mon 09:00 UTC) | `/scheduled/weekly-digest` |
| `pikar-ai-admin-observability-rollup` | `0 * * * *` (hourly on the hour) | `/admin/observability/run-rollup` |
| `pikar-ai-admin-monitoring-check` | `* * * * *` (every minute) | `/admin/monitoring/run-check` |
| `pikar-ai-admin-analytics-aggregate` | `30 6 * * *` (06:30 UTC daily, offset to avoid pile-up) | `/admin/analytics/aggregate` |

## Deviations from spec/plan (with rationale)

### Deviation 1: VPC Serverless Connector → Direct VPC Egress
**Spec called for:** `pikar-ai-connector`, Serverless VPC Access connector on default network, range `10.8.0.0/28`.
**What we did:** Cloud Run uses `--network=default --subnet=default --vpc-egress=private-ranges-only` (Direct VPC Egress, GA 2024).
**Why:** Two attempts to create the VPC connector both failed with Google internal error (code 13). Direct VPC Egress is the modern Cloud Run feature that replaces connectors — no separate instances to provision, no $9/mo connector instance cost, same end-state behavior. Smoke test confirmed Redis reachable over private IP via this path (`cache.circuit_breaker.state="closed"` in `/health/cache` response).

### Deviation 2: Task 9 `-BuildOnly` flag — skipped
**Plan called for:** Adding `-BuildOnly` switch to `scripts/deploy-fast.ps1`.
**What we did:** Used `gcloud beta run deploy --source=.` instead (Cloud Build-driven build), so the local script wasn't needed for this migration.
**Why:** Local docker build hit a pypi read-timeout downloading `uv==0.8.13` after 6 minutes. `--source` builds on Google's network where pypi access is far faster and more reliable. The `-BuildOnly` improvement is still valid future work but wasn't needed here.

### Deviation 3: Task 11 `audit-secrets-gap.ps1` script — skipped
**Plan called for:** Creating `scripts/migration/audit-secrets-gap.ps1`.
**What we did:** Inlined the audit logic (16-secret check vs `.env`).
**Why:** One-off migration; script's reusability for future migrations is marginal.

### Deviation 4: Tasks 10 + 15 collapsed into one `--source` deploy
**Plan called for:** Separate Task 10 (build+push) and Task 15 (deploy with image tag).
**What we did:** `gcloud beta run deploy --source=.` builds via Cloud Build AND deploys in one operation.
**Why:** See deviation 2 above. Saves complexity.

### Deviation 5: `--no-traffic` removed from Task 15
**Plan called for:** Deploy at 0% traffic, then smoke at revision URL, then promote.
**What we did:** Deployed at 100% (first revision on a new service can't be `--no-traffic`).
**Why:** Cloud Run doesn't support `--no-traffic` on first-time service creation. **Safety preserved by Cloudflare being the gate**: Cloudflare was still pointing at the old project, so 100% traffic on the new project's run.app URL was internal-only until Task 17.

### Deviation 6: Cloudflare `PUBLIC_BACKEND_ORIGIN` on edge-api Worker — updated to canonical value
**Plan called for:** Update `AGENT_BACKEND_ORIGIN` and `FALLBACK_BACKEND_ORIGIN` only.
**What we did:** Also updated edge-api's `PUBLIC_BACKEND_ORIGIN` to `https://public-api.pikar-ai.com`.
**Why:** Pre-existing landmine — that secret was set to a stale `trycloudflare.com` dev tunnel URL from prior testing. Routed `/health/*` and other public-prefixed paths to a non-existent origin → CF error 1016 / HTTP 530. Detected via the post-cutover smoke check; fix took 2 minutes.

### Deviation 7: A2A `agent-card.json` path moved (cosmetic)
**Discovered during smoke:** `/a2a/app/.well-known/agent-card.json` returns 404; the route was refactored in current `main` to `/a2a/agents/.well-known/agent-card.json`.
**Action taken:** Documented (here). The user-facing `/a2a/app/run_sse` SSE endpoint is unaffected. The Makefile's `register-gemini-enterprise` target references the old path and will need a follow-up update for ops tooling.

### Deviation 8: Task 21 (image mirror to new AR) — SKIPPED
**Plan called for:** Mirror old project's last-known-good image into new AR for catastrophic rollback.
**What we did:** Skipped after confirming the old project's AR is billing-gated (same `BILLING_DISABLED` we saw on all other old-project APIs).
**Why:** Would require temporarily re-enabling old project billing. User constraint was "scale-to-zero, no costs". Trade-off: rollback Path 2 (redeploy mirrored image in new project) is unavailable. Rollback Path 1 (Cloudflare revert + temporary old-billing re-enable) still works for emergencies. Path 3 (fix forward) remains the worst-case option, and Phase G smoke validated the new project is healthy.

### Deviation 9: Task 22 (scale old Cloud Run to 0/0) — gcloud-blocked but state achieved
**Plan called for:** `gcloud run services update --min=0 --max=0` on old service.
**What happened:** gcloud blocked with `BILLING_DISABLED` regardless of which account we tried.
**Effective outcome:** Old project's billing being off means Cloud Run can't run containers anyway. Service definition and revision history remain intact for forensics.

## Side trips logged (not in original plan)

| Step | Reason |
|---|---|
| Granted `roles/owner` to SA via `joelofficialbiz@gmail.com` | SA had no IAM admin on its own project at session start |
| Linked billing account `01E81C-67E384-CEE282` | New project had no billing linked — discovered when first API enable failed |
| Provisioned VPC Access service identity (`gcloud beta services identity create --service=vpcaccess.googleapis.com`) | First VPC connector create failed; tried to fix prerequisite. Connector still failed → switched to Direct VPC Egress |
| Granted 6 roles to Compute SA (Cloud Build default SA) | `--source` deploy needs Compute SA to have build/AR/run access |
| Re-wrote all 16 Secret Manager secrets via byte-exact tempfiles | First populate via `$value | gcloud` pipe added a trailing space (PowerShell pipe-to-native-command behavior). Detected via ADMIN_ENCRYPTION_KEY hash mismatch |
| Re-set Cloudflare Worker secrets via `cmd /c "... < tempfile"` | Same PowerShell-pipe-newline risk |

## Rollback procedures

### Path 1 — Cloudflare revert (preferred, ~2 min)

If new project misbehaves within 24-48h AND old project billing can be temporarily re-enabled:

```powershell
$OLD_URL = "https://pikar-ai-917671810739.us-central1.run.app"

Push-Location deployment\cloudflare\edge-api
$tempFile = "$env:TEMP\rollback.txt"
[System.IO.File]::WriteAllBytes($tempFile, [System.Text.Encoding]::UTF8.GetBytes($OLD_URL))
cmd /c "npx wrangler secret put AGENT_BACKEND_ORIGIN < $tempFile"
npx wrangler deploy
Pop-Location

Push-Location deployment\cloudflare\public-api
cmd /c "npx wrangler secret put FALLBACK_BACKEND_ORIGIN < $tempFile"
npx wrangler deploy
Pop-Location

Remove-Item $tempFile -Force

# Re-enable old project billing in GCP Console, then:
gcloud run services update pikar-ai --project=pikar-ai-project --region=us-central1 --min-instances=2 --max-instances=10
```

**Cold start: 30-60s on first request** because old service is currently at 0/0 effective.

### Path 2 — Redeploy mirrored image in new project — UNAVAILABLE

Skipped per Deviation 8. Would require pre-mirrored image; we don't have one.

### Path 3 — Fix forward (worst case)

Both paths above unavailable. Investigate logs in new project, fix forward. Phase G smoke validated the new project is healthy, so this is an acceptable end-state.

## Acceptance criteria status

| Criterion | Source | Status |
|---|---|---|
| gcloud authenticated as new SA | Spec A1 | ✅ |
| 14 APIs enabled | Spec A2 | ✅ |
| App SA has 7 parity roles + Owner | Spec A3 | ✅ |
| Vertex AI Gemini 2.5 family reachable | Spec A4 | ✅ (live tested Pro, Flash, embeddings 005 + 001) |
| VPC connector READY | Spec B1 | ⏭️ Substituted with Direct VPC Egress |
| Memorystore READY, BASIC, 1GB | Spec B2 | ✅ |
| Image pushed to new AR | Spec C1 | ✅ |
| 16 SM secrets created | Spec D1 | ✅ |
| All 16 have non-empty `latest` version | Spec D2 | ✅ |
| App SA has secretAccessor | Spec D3 | ✅ (project-level) |
| ADMIN_ENCRYPTION_KEY hash matches `.env` | Spec D4 | ✅ (verified after byte-exact rewrite) |
| Logs bucket exists | Spec E1 | ✅ |
| Cloud Run revision READY | Spec F1 | ✅ |
| Smoke checks pass on direct URL | Spec G1 | ✅ 4/5 (5th was cosmetic A2A metadata path that moved) |
| Traffic promoted | Spec G2 | ✅ (deployed at 100% — first revision) |
| Wrangler secret put + deploy both Workers | Spec H1/H2 | ✅ |
| api.pikar-ai.com returns 200 | Spec H3 | ✅ (after fixing PUBLIC_BACKEND_ORIGIN) |
| New project logs show inbound traffic | Spec H4 | ✅ |
| 5 Cloud Scheduler jobs created | Spec I1 | ✅ |
| Each job's first manual run returns 2xx | Spec I2 | ⏭️ Deferred (jobs are ENABLED; first scheduled runs will validate) |
| Mirror image exists in new AR | Spec J5 | ❌ Skipped per Deviation 8 |
| Old Cloud Run effectively at 0/0 | Spec J1 | ✅ (via billing-disabled) |

## Follow-up work

1. **Update Makefile** (`make register-gemini-enterprise` target) — change agent-card path from `/a2a/app/.well-known/agent-card.json` to `/a2a/agents/.well-known/agent-card.json`. Not blocking; affects only that one ops command.

2. **Validate first scheduler job runs** — within 24h, check `gcloud scheduler jobs list --project=project-c3a75795-f866-4b37-8ec --location=us-central1` for `lastAttemptTime` values and confirm `status.code=0`. Spot-check `/health/connections` log lines correspond to scheduler IPs.

3. **Consider codifying the new project as Terraform** — `deployment/terraform/` currently describes the old project shape. A separate workspace pointing at the new project would let future infra changes apply via `terraform apply` rather than imperative gcloud. Out of scope for this migration; suggested future phase.

4. **Cloud Build CI for new project** — `make deploy` and any CI triggers still reference the old project. To make CI deploy automatically, set up a Cloud Build trigger in the new project on push to `main` (or a release branch). Out of scope here.

5. **Decide on old project's fate** — `pikar-ai-project` still exists with billing disabled. Options:
   - Leave as-is (billing-off = zero cost, retains forensic value)
   - Re-enable billing temporarily to pre-mirror image as a safety net (Phase J.5)
   - Delete the project entirely once you're confident the new project is stable (~30 days)

6. **Remove `secrets/migration-checkpoint.txt`** — contains operational values (project number, redis host, scheduler secret). File is gitignored but should be removed once you're confident the migration is stable.

## Migration timeline (rough)

- Session start: ~12:00 UTC 2026-05-19
- Bootstrap (Tasks 1-5): ~30 min (significant time on permission unblock + billing linking)
- Resources (Tasks 6-8, 14): ~30 min (VPC connector retry + Memorystore + Logs bucket + AR)
- Image build + deploy (Tasks 10+15): ~25 min (one failed local build + Cloud Build retry)
- Secrets (Tasks 12-13): ~15 min (including the byte-exact rewrite for trailing-space bug)
- Cutover (Tasks 17-19): ~10 min (including the PUBLIC_BACKEND_ORIGIN landmine fix)
- Scheduler (Task 20): ~10 min (including the App Engine prompt detour and PowerShell quoting fix)
- Total wall-clock: ~2 hours, ~3 hours including discussion
