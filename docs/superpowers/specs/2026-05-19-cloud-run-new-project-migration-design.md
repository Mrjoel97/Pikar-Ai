# Cloud Run new-project migration — design

**Date:** 2026-05-19
**Branch:** `phase-112-01-kg-findings-broaden` (design only; execution branch TBD by writing-plans)
**Scope:** move the `pikar-ai` Cloud Run workload from the old GCP project (`pikar-ai-project`, billing disabled) to a brand-new project (`project-c3a75795-f866-4b37-8ec`) without changing Cloudflare, Vercel, or Supabase. Cut over via Cloudflare Worker origin swap.

---

## 1. Decisions (locked)

| # | Decision | Source |
|---|---|---|
| D1 | Recreate full parity in the new GCP project (not minimal, not Terraform) | User answer to Q1 |
| D2 | Memorystore = **Basic, 1 GB, redis 7.0**, region us-central1 — literal parity with old project | User answer to Q5 after correcting Q2 |
| D3 | Cutover = blue/green via Cloudflare Worker `wrangler secret put` + `wrangler deploy` (atomic origin swap, zero downtime) | User answer to Q3 |
| D4 | After cutover, **immediately** scale old Cloud Run to `min=0,max=0` (cold rollback acceptable) | User answer to Q4 |
| D5 | Move currently-plaintext `GOOGLE_WORKSPACE_CLIENT_SECRET` to Secret Manager during rebuild (CLIENT_ID and REDIRECT_URI stay plain) | User answer to Q6 |

---

## 2. Invariants — what must NOT change

- **Hostnames**: `api.pikar-ai.com`, `public-api.pikar-ai.com`, `pikar-ai.com`, `admin.pikar-ai.com` stay on the same Workers / Vercel projects.
- **Cloudflare Workers**: `pikar-edge-api` and `pikar-public-api` keep the same code, routes, and Durable Object class `EdgeRateLimiter`. Only their backend-origin **secrets** change.
- **Supabase**: same project (`https://rbdowedrdhtlbngapexj.supabase.co`), same RLS, same data, same Edge Functions.
- **Shared secrets that round-trip with Supabase or with encrypted DB rows must be byte-identical to the old values**:
  - `WORKFLOW_SERVICE_SECRET` — must match Supabase Edge Functions value (service-to-service auth)
  - `SUPABASE_JWT_SECRET`, `SUPABASE_SERVICE_ROLE_KEY` — from same Supabase project
  - `ADMIN_ENCRYPTION_KEY` — **rotation would brick all `integration_credentials` rows**
  - `SCHEDULER_SECRET` — must match what Cloud Scheduler jobs send in `X-Scheduler-Secret`

---

## 3. Topology

```
                                  Browser
                                     |
                                     v
                       +-----------------------------+
                       | Cloudflare DNS + Workers    |
                       |   api.pikar-ai.com          |
                       |     -> pikar-edge-api       |
                       |   public-api.pikar-ai.com   |
                       |     -> pikar-public-api     |
                       +--------------+--------------+
                                      |
              backend origin = wrangler secret (THIS is what we swap)
                                      |
                                      v
              +----------------------------------------------+
              |  GOOGLE CLOUD (target: new project)          |
              |                                              |
              |   Cloud Run service "pikar-ai" (us-central1) |
              |     - SA: pikar-ai@project-c3a75...          |
              |     - VPC connector -> Memorystore Redis     |
              |     - 16 Secret Manager secrets attached     |
              |     - 39 plain env vars                      |
              |                                              |
              |   Cloud Scheduler (5 jobs) ---X-Scheduler-Secret---> Cloud Run
              +----------------------------------------------+
```

**Decoupling property that makes blue/green work**: Cloudflare Workers read their backend URL from `wrangler secret` (not from `wrangler.toml`, not from DNS). So `wrangler secret put AGENT_BACKEND_ORIGIN <new_url>` + `wrangler deploy` is the entire cutover. There is no DNS change, no domain remapping, no route change.

---

## 4. Source and target inventory

### 4.1 Source (old project — read-only, mostly billing-gated)

- **Project**: `pikar-ai-project` (project number `917671810739`)
- **Billing**: DISABLED (confirmed 2026-05-19 via `gcloud redis instances list` returning `BILLING_DISABLED`)
- **Cloud Run service**: `pikar-ai`, region `us-central1`, current revision `pikar-ai-00131-k5r`
- **Service URLs (both valid)**:
  - `https://pikar-ai-917671810739.us-central1.run.app` (project-number form)
  - `https://pikar-ai-ddqwnqn5xq-uc.a.run.app` (regional alias)
- **App SA**: `agents@pikar-ai-project.iam.gserviceaccount.com`
- **Image**: `us-central1-docker.pkg.dev/pikar-ai-project/cloud-run-source-deploy/pikar-ai@sha256:0eecac59a74d5e24b09fe8107185466f4348084e4fa433135d268a2fe3b14d69` (record for emergency rollback)
- **Container resources**: cpu=2, memory=4Gi, port=8000
- **Autoscaling**: min=2, max=10, concurrency=250, timeout=1800s
- **CPU throttling**: disabled
- **Startup probe**: GET /health/live, initialDelay=10s, period=45s, timeout=30s, failureThreshold=8
- **Liveness probe**: GET /health/live, initialDelay=15s, period=30s, timeout=5s, failureThreshold=3
- **VPC**: connector `pikar-ai-connector`, range `10.8.0.0/28`, throughput 200/300, network `default`, **current state ERROR**
- **Memorystore**: `pikar-ai-cache`, Basic tier, 1 GB, REDIS_7_0, host `10.131.85.107`, port `6379`
- **Logs bucket**: `gs://pikar-ai-project-logs`
- **App SA bound roles (directly granted, may be incomplete)**: `roles/aiplatform.admin`, `roles/iam.serviceAccountAdmin`

### 4.2 Target (new project)

- **Project ID**: `project-c3a75795-f866-4b37-8ec`
- **Project number**: TBD (`gcloud projects describe project-c3a75795-f866-4b37-8ec --format='value(projectNumber)'`)
- **App SA (already created by user)**: `pikar-ai@project-c3a75795-f866-4b37-8ec.iam.gserviceaccount.com`
- **SA JSON key**: `secrets/project-c3a75795-f866-4b37-8ec-d48bbc59e196.json` (gitignored)
- **Service URL after deploy**: `https://pikar-ai-<NEW_PROJECT_NUMBER>.us-central1.run.app`
- **Logs bucket name**: `pikar-ai-c3a75-logs` (GCS bucket names are global; we add the `c3a75` shard from the project ID prefix to avoid collisions with the old `pikar-ai-project-logs`)

---

## 5. Phased execution plan

Each phase has a verification step before moving to the next. Steps marked **[manual]** require human input (entering values from `.env` or Cloudflare Worker into a secret); all others are automatable.

### Phase A — GCP project bootstrap (~10 min)

1. `gcloud auth activate-service-account --key-file=secrets/project-c3a75795-f866-4b37-8ec-d48bbc59e196.json`
2. `gcloud config configurations create pikar-ai-c3a75` (so we don't disturb the active config pointing at `pikar-ai-project`)
3. `gcloud config set project project-c3a75795-f866-4b37-8ec`
4. `gcloud config set run/region us-central1`
5. Capture project number: `$NEW_PROJECT_NUMBER = gcloud projects describe project-c3a75795-f866-4b37-8ec --format='value(projectNumber)'`
6. Enable APIs (single batched call):
   - `run`, `artifactregistry`, `secretmanager`, `aiplatform`, `redis`, `vpcaccess`, `compute`, `storage`, `cloudbuild`, `cloudscheduler`, `iamcredentials`, `logging`, `monitoring`, `cloudtrace`
7. Grant app SA the parity role set (matches `deployment/terraform/variables.tf:53-66`):
   - `roles/aiplatform.user`, `roles/discoveryengine.editor`, `roles/logging.logWriter`, `roles/cloudtrace.agent`, `roles/storage.admin`, `roles/serviceusage.serviceUsageConsumer`, `roles/secretmanager.secretAccessor`
8. Verify Vertex AI access: `gcloud ai models list --region=us-central1 --project=project-c3a75795-f866-4b37-8ec --filter='name:gemini-2.5'` returns Pro + Flash. If 403/quota — surface for human attention before any later phase.

**Exit gate:** `gcloud run services list --region=us-central1` succeeds (proves Run API + IAM are wired).

### Phase B — Networking and Redis (~15 min)

1. Create VPC connector `pikar-ai-connector`:
   - region `us-central1`, network `default`, range `10.8.0.0/28`, min-throughput 200, max-throughput 300
2. Create Memorystore Redis `pikar-ai-cache`:
   - tier `BASIC`, size `1` GB, version `REDIS_7_0`, region `us-central1`, zone `us-central1-a`, authorized network `default`
3. Capture `REDIS_HOST` and `REDIS_PORT` from the create call output

**Exit gate:** `gcloud redis instances describe pikar-ai-cache --region=us-central1 --format='value(host,port,state)'` returns READY.

### Phase C — Artifact Registry and image build (~10-15 min depending on cache state)

1. Create AR repo: `gcloud artifacts repositories create cloud-run-source-deploy --repository-format=docker --location=us-central1 --description="Cloud Run source deploy"`
2. `gcloud auth configure-docker us-central1-docker.pkg.dev`
3. Run `scripts/deploy-fast.ps1` build leg **only** (no deploy yet):
   - Since `deploy-fast.ps1` does build + push + deploy in one shot, we'll either (a) add a `-BuildOnly` flag in the implementation phase, or (b) run `docker build` + `docker push` manually for this round
   - Output: `us-central1-docker.pkg.dev/project-c3a75795-f866-4b37-8ec/cloud-run-source-deploy/pikar-ai:<git-sha>`

**Exit gate:** `gcloud artifacts docker images list us-central1-docker.pkg.dev/project-c3a75795-f866-4b37-8ec/cloud-run-source-deploy/pikar-ai` lists the new tag.

### Phase D — Secret Manager + secret population (~20 min)

1. Create 16 Secret Manager secrets in the new project, with `--replication-policy=automatic`:

| Env var name | Secret name |
|---|---|
| `SCHEDULER_SECRET` | `pikar-ai-scheduler-secret` |
| `SUPABASE_SERVICE_ROLE_KEY` | `pikar-ai-supabase-service-role-key` |
| `SUPABASE_JWT_SECRET` | `pikar-ai-supabase-jwt-secret` |
| `ADMIN_ENCRYPTION_KEY` | `pikar-ai-admin-encryption-key` |
| `TAVILY_API_KEY` | `pikar-ai-tavily-api-key` |
| `FIRECRAWL_API_KEY` | `pikar-ai-firecrawl-api-key` |
| `RESEND_API_KEY` | `pikar-ai-resend-api-key` |
| `RESEND_WEBHOOK_SECRET` | `pikar-ai-resend-webhook-secret` |
| `FACEBOOK_APP_SECRET` | `pikar-ai-facebook-app-secret` |
| `TIKTOK_CLIENT_SECRET` | `pikar-ai-tiktok-client-secret` |
| `LINKEDIN_CLIENT_SECRET` | `pikar-ai-linkedin-client-secret` |
| `LINKEDIN_WEBHOOK_SECRET` | `pikar-ai-linkedin-webhook-secret` |
| `HUBSPOT_CLIENT_SECRET` | `pikar-ai-hubspot-client-secret` |
| `SHOPIFY_CLIENT_SECRET` | `pikar-ai-shopify-client-secret` |
| `WORKFLOW_SERVICE_SECRET` | `pikar-ai-workflow-service-secret` |
| `GOOGLE_WORKSPACE_CLIENT_SECRET` (new) | `pikar-ai-google-workspace-client-secret` |

2. **[manual]** Populate each secret's first version. Sources, in priority order:
   - `.env` at repo root (4883 bytes) — most secrets are here
   - Cloudflare Worker `pikar-public-api` secrets (`npx wrangler secret list` from `deployment/cloudflare/public-api/`) — for any not in `.env`
   - User direct input — last resort
3. Grant per-secret accessor IAM to the app SA: `roles/secretmanager.secretAccessor` on each secret to `serviceAccount:pikar-ai@project-c3a75795-f866-4b37-8ec.iam.gserviceaccount.com`
4. Pre-deploy gap audit script: for each secret name, run `gcloud secrets versions access latest --secret=<name>` and confirm non-empty. Fail loudly if any secret is missing or empty.

**Exit gate:** all 16 secrets have at least one version and the app SA can access each. The audit script reports 16/16 OK.

### Phase E — Logs bucket and IAM (~5 min)

1. Create GCS bucket: `gcloud storage buckets create gs://pikar-ai-c3a75-logs --location=us-central1 --uniform-bucket-level-access`
2. Grant app SA `roles/storage.objectAdmin` on it (already has `roles/storage.admin` at project level from Phase A but per-bucket is explicit and safer)

**Exit gate:** `gcloud storage ls gs://pikar-ai-c3a75-logs` returns 200.

### Phase F — Cloud Run deploy (no traffic) (~5 min)

1. `gcloud beta run deploy pikar-ai` with these flags (full list):

```
--image           = us-central1-docker.pkg.dev/<new>/cloud-run-source-deploy/pikar-ai:<git-sha>
--region          = us-central1
--project         = project-c3a75795-f866-4b37-8ec
--service-account = pikar-ai@project-c3a75795-f866-4b37-8ec.iam.gserviceaccount.com
--port            = 8000
--cpu             = 2
--memory          = 4Gi
--no-cpu-throttling
--min-instances   = 2
--max-instances   = 10
--concurrency     = 250
--timeout         = 1800
--vpc-connector   = pikar-ai-connector
--vpc-egress      = private-ranges-only
--allow-unauthenticated
--no-traffic
--startup-probe   = httpGet.path=/health/live,httpGet.port=8000,initialDelaySeconds=10,timeoutSeconds=30,periodSeconds=45,failureThreshold=8
--liveness-probe  = httpGet.path=/health/live,httpGet.port=8000,initialDelaySeconds=15,timeoutSeconds=5,periodSeconds=30,failureThreshold=3
--labels          = created-by=adk
```

2. `--set-env-vars` (plain env, 39 total) — must use `^;^` delimiter for the comma-containing `ALLOWED_ORIGINS`:

| Name | Value |
|---|---|
| `ENVIRONMENT` | `production` |
| `APP_URL` | `https://pikar-ai-<NEW_PROJECT_NUMBER>.us-central1.run.app` |
| `BACKEND_API_URL` | `https://pikar-ai-<NEW_PROJECT_NUMBER>.us-central1.run.app` |
| `ALLOWED_ORIGINS` | `https://pikar-ai.com,https://www.pikar-ai.com,https://admin.pikar-ai.com,https://pikar-ai.vercel.app,https://pikar-ai-joelferuzi-gmailcoms-projects.vercel.app,https://pikar-ai-git-main-joelferuzi-gmailcoms-projects.vercel.app` |
| `LOGS_BUCKET_NAME` | `gs://pikar-ai-c3a75-logs` |
| `GOOGLE_CLOUD_PROJECT` | `project-c3a75795-f866-4b37-8ec` |
| `GOOGLE_CLOUD_LOCATION` | `us-central1` |
| `GOOGLE_GENAI_USE_VERTEXAI` | `1` |
| `GEMINI_AGENT_MODEL_PRIMARY` | `gemini-2.5-pro` |
| `GEMINI_AGENT_MODEL_FALLBACK` | `gemini-2.5-flash` |
| `SUPABASE_URL` | `https://rbdowedrdhtlbngapexj.supabase.co` |
| `SUPABASE_ANON_KEY` | (copy verbatim from old service describe) |
| `REQUIRE_STRICT_AUTH` | `1` |
| `ALLOW_ANONYMOUS_CHAT` | `0` |
| `ALLOW_ALL_FEATURES_FOR_TESTING` | `true` |
| `WORKFLOW_STRICT_TOOL_RESOLUTION` | `true` |
| `WORKFLOW_STRICT_CRITICAL_TOOL_GUARD` | `true` |
| `WORKFLOW_ALLOW_FALLBACK_SIMULATION` | `false` |
| `WORKFLOW_ENFORCE_READINESS_GATE` | `true` |
| `REDIS_HOST` | (from Phase B output) |
| `REDIS_PORT` | `6379` |
| `REDIS_DB` | `0` |
| `REDIS_ENABLED` | `1` |
| `REMOTION_RENDER_ENABLED` | `1` |
| `REMOTION_RENDER_DIR` | `/code/remotion-render` |
| `REMOTION_RENDER_TIMEOUT` | `300` |
| `WEB_CONCURRENCY` | `2` |
| `SKILL_EMBEDDING_WARMUP_ENABLED` | `0` |
| `EMBEDDING_QUOTA_COOLDOWN_SECONDS` | `900` |
| `AGENT_VERSION` | (from `pyproject.toml`) |
| `COMMIT_SHA` | (from `git rev-parse --short HEAD`) |
| `ADMIN_EMAILS` | `joel@pikar-ai.com` |
| `RESEND_FROM_EMAIL` | `noreply@pikar-ai.com` |
| `RESEND_FORWARD_TO` | `joel.feruzi@gmail.com` |
| `FACEBOOK_APP_ID` | `4064994950416607` |
| `TIKTOK_CLIENT_KEY` | `awktqc6pgvai54qe` |
| `LINKEDIN_CLIENT_ID` | `77f5eslppa1ips` |
| `HUBSPOT_CLIENT_ID` | `36832136` |
| `SHOPIFY_CLIENT_ID` | `735d58083996a927ae6095d41ae60e3a` |
| `GOOGLE_WORKSPACE_CLIENT_ID` | `706895462845-7kfuod6uh18csiu5lk70da2fpklruptn.apps.googleusercontent.com` |
| `GOOGLE_WORKSPACE_REDIRECT_URI` | `https://api.pikar-ai.com/integrations/google_workspace/callback` |

3. `--set-secrets` (16 secret references): `<ENV_NAME>=<secret-name>:latest` for each entry in the Phase D table.

**Exit gate:** revision deploys to `STATUS: Ready=True`, but at 0% traffic. Get the unique revision URL via `gcloud run revisions describe <rev-name> --format='value(status.url)'`.

### Phase G — Smoke verification (no Cloudflare change yet) (~10 min)

Direct-hit the run.app URL of the new revision (not via Cloudflare):

| Check | Expected |
|---|---|
| `GET /health/live` | 200, `{"status":"ok"}` |
| `GET /health/connections` | 200, Supabase + cache both healthy |
| `GET /health/cache` | 200, Redis circuit breaker closed |
| `GET /health/embeddings` | 200, Gemini embedding model reachable |
| `GET /a2a/app/.well-known/agent-card.json` | 200, valid JSON |
| Bearer-authed `POST /a2a/app/run_sse` with a known-good payload | 200, SSE stream with first chunk in <5s |

Then promote: `gcloud run services update-traffic pikar-ai --to-latest --project=project-c3a75795-f866-4b37-8ec`. The run.app URL now serves the new revision.

**Exit gate:** all 6 checks green. If any fail, we abort the migration here — Cloudflare is untouched and there's nothing to roll back.

### Phase H — Cloudflare cutover (the atomic flip) (~5 min)

For `deployment/cloudflare/edge-api/`:
```powershell
$newOrigin = "https://pikar-ai-$NEW_PROJECT_NUMBER.us-central1.run.app"
# Note: PUBLIC_BACKEND_ORIGIN already points at https://public-api.pikar-ai.com,
# which is itself a Cloudflare Worker hostname, so it does NOT change.
echo $newOrigin | npx wrangler secret put AGENT_BACKEND_ORIGIN
npx wrangler deploy
```

For `deployment/cloudflare/public-api/`:
```powershell
echo $newOrigin | npx wrangler secret put FALLBACK_BACKEND_ORIGIN
npx wrangler deploy
```

**Exit gate:** within 60 seconds of the second `wrangler deploy`, `curl https://api.pikar-ai.com/health/live` returns 200 and Cloud Run logs in the NEW project show inbound requests.

### Phase I — Cloud Scheduler jobs (~15 min)

Recreate the 5 jobs in the new project (`gcloud scheduler jobs create http`). Paths and crons resolved against the current code state at spec time (2026-05-19):

| Job name | Schedule | Target (POST) | Source |
|---|---|---|---|
| `pikar-ai-daily-report` | `0 7 * * *` (07:00 UTC) | `https://pikar-ai-<NEW_PROJECT_NUMBER>.us-central1.run.app/scheduled/daily-report` | `app/services/scheduled_endpoints.py:39` |
| `pikar-ai-weekly-digest` | `0 9 * * 1` (Mon 09:00 UTC) | `.../scheduled/weekly-digest` | `app/services/scheduled_endpoints.py:62` |
| `pikar-ai-admin-observability-rollup` | `0 * * * *` (every hour) | `.../admin/observability/run-rollup` | `app/routers/admin/observability.py:225` ("Triggered every hour by Cloud Scheduler") |
| `pikar-ai-admin-monitoring-check` | `* * * * *` (every minute) | `.../admin/monitoring/run-check` | `app/routers/admin/monitoring.py:149` ("Triggered every 60 seconds by Cloud Scheduler") |
| `pikar-ai-admin-analytics-aggregate` | `30 6 * * *` (06:30 UTC daily) | `.../admin/analytics/aggregate` | `app/routers/admin/analytics.py:278` ("daily aggregation") |

All five send `X-Scheduler-Secret: <SCHEDULER_SECRET>` in the request header — a single secret covers every scheduler-triggered endpoint (confirmed in `app/routers/admin/monitoring.py:14` docstring). No OIDC token required because authentication is handled at the application layer.

The `30 6` minute offset on the analytics aggregate is deliberate: it dodges the on-the-hour rush from the observability rollup and the every-minute monitoring check, so we don't pile three jobs into the same Cloud Run startup window at 07:00 UTC.

**Exit gate:** all 5 jobs report `ENABLED`. Trigger each with `gcloud scheduler jobs run <job>` and confirm 2xx in Cloud Run logs.

### Phase J.5 — Mirror old image to new AR (do BEFORE Phase J) (~5-10 min)

**Why this exists:** the old Artifact Registry is billing-gated (confirmed 2026-05-19: `gcloud artifacts docker images describe ...` returned `BILLING_DISABLED`). Once we scale the old Cloud Run service to zero in Phase J, any rollback that requires re-deploying the old service will fail at image pull. Mirroring the last-known-good image into the *new* project's AR gives us a deploy-from-known-good fallback that survives even if old project billing never returns.

**Prerequisite:** docker pull from the billing-disabled old AR. We have NOT yet verified docker-level pulls work when only the project-level billing API is gated. Two outcomes:
- **If pull works** (docker registry endpoint is separate from project-level billing checks): proceed without any billing change.
- **If pull fails** (registry honors the same gate): **temporarily re-enable billing on `pikar-ai-project`** for the duration of this phase only (~10 min). Re-disable immediately after the mirror push completes. This is the only step in the entire migration that may require touching old project billing.

**Steps:**
1. `gcloud auth configure-docker us-central1-docker.pkg.dev` (uses `africantouch.official@gmail.com` user credentials — NOT the new SA — because the new SA has no IAM on the old project)
2. Pull the last-known-good image by digest (immutable reference):
   ```
   docker pull us-central1-docker.pkg.dev/pikar-ai-project/cloud-run-source-deploy/pikar-ai@sha256:0eecac59a74d5e24b09fe8107185466f4348084e4fa433135d268a2fe3b14d69
   ```
3. Re-tag for the new project's AR:
   ```
   docker tag us-central1-docker.pkg.dev/pikar-ai-project/cloud-run-source-deploy/pikar-ai@sha256:0eecac59a74d5e24b09fe8107185466f4348084e4fa433135d268a2fe3b14d69 \
              us-central1-docker.pkg.dev/project-c3a75795-f866-4b37-8ec/cloud-run-source-deploy/pikar-ai:rollback-pre-cutover-0eecac59
   ```
4. Push to new AR:
   ```
   docker push us-central1-docker.pkg.dev/project-c3a75795-f866-4b37-8ec/cloud-run-source-deploy/pikar-ai:rollback-pre-cutover-0eecac59
   ```
5. Verify:
   ```
   gcloud artifacts docker images describe us-central1-docker.pkg.dev/project-c3a75795-f866-4b37-8ec/cloud-run-source-deploy/pikar-ai:rollback-pre-cutover-0eecac59
   ```

**Exit gate:** the `rollback-pre-cutover-0eecac59` tag exists in new AR with the same digest `sha256:0eecac59...`. If billing was temporarily re-enabled on the old project, it has been re-disabled.

**Bypass criteria:** if the user explicitly accepts "no rollback after Phase H succeeds" (i.e. Phase G smoke is the only safety net), this phase can be skipped. The implementation phase will surface the bypass option to the user before executing.

### Phase J — Decommission old (~2 min)

```
gcloud run services update pikar-ai \
  --project=pikar-ai-project --region=us-central1 \
  --min-instances=0 --max-instances=0
```

Old service is now cold. It still exists; revision history and image reference stay intact. Note: with billing disabled on old project, scaling it back up would fail at image pull *unless* Phase J.5 successfully mirrored the image — which is why J.5 runs before J, not after.

**Exit gate:** `gcloud run services describe pikar-ai --project=pikar-ai-project` shows `minScale=0, maxScale=0` and no active instances after ~5 min.

---

## 6. Rollback contract

**Window:** first 24-48 hours after Phase H.

We have **three** rollback paths, in order of preference:

### Path 1 — Cloudflare revert (preferred, ~2 min)

If the new project misbehaves AND old Cloud Run can still serve traffic (billing on old project is re-enabled, or never went off — check before relying on this path):

```powershell
# In deployment/cloudflare/edge-api/
echo "https://pikar-ai-917671810739.us-central1.run.app" | npx wrangler secret put AGENT_BACKEND_ORIGIN
npx wrangler deploy

# In deployment/cloudflare/public-api/
echo "https://pikar-ai-917671810739.us-central1.run.app" | npx wrangler secret put FALLBACK_BACKEND_ORIGIN
npx wrangler deploy
```

Then wake old Cloud Run:
```
gcloud run services update pikar-ai \
  --project=pikar-ai-project --region=us-central1 \
  --min-instances=2 --max-instances=10
```

**Cold start: 30-60s on first request** (per D4 we accepted this tradeoff). **Will fail at image pull if old project billing is off** — see Path 3 if so.

Verify: `curl https://api.pikar-ai.com/health/connections` returns 200 from the old service.

### Path 2 — Redeploy mirrored old image in NEW project (fallback when old AR is unreachable, ~5 min)

This is what Phase J.5 was for. The old `sha256:0eecac59...` image is sitting in the new AR under tag `rollback-pre-cutover-0eecac59`.

```powershell
gcloud beta run deploy pikar-ai `
  --image us-central1-docker.pkg.dev/project-c3a75795-f866-4b37-8ec/cloud-run-source-deploy/pikar-ai:rollback-pre-cutover-0eecac59 `
  --project project-c3a75795-f866-4b37-8ec `
  --region us-central1 `
  --no-traffic
# Smoke the new revision at its revision URL...
gcloud run services update-traffic pikar-ai --to-latest --project=project-c3a75795-f866-4b37-8ec
```

Cloudflare stays pointed at the new project; only the Cloud Run revision rolls back to the last-known-good binary. All Cloudflare Worker secrets, Memorystore, VPC, Secret Manager state are preserved.

### Path 3 — Fix forward (worst case)

Both paths above failed (or Phase J.5 was bypassed and old project billing can't be re-enabled). The migration is irrevocable; we must fix forward on the new project. Phase G's smoke window is what makes this an acceptable end-state — we will only reach Phase H if Phase G proved the new project healthy on direct hits before any user-visible traffic touched it.

### Selecting a path

- **First**: check `gcloud projects describe pikar-ai-project --format='value(billingAccountName)'`. If non-empty → Path 1 is viable.
- **Otherwise**: Path 2, assuming Phase J.5 succeeded. The `rollback-pre-cutover-*` tag's existence in new AR is the explicit precondition.
- **If neither**: Path 3.

---

## 7. Risks and assumptions

| Risk | Severity | Mitigation |
|---|---|---|
| Vertex AI quota in new project is zero for Gemini 2.5 | high (blocks deploy) | Phase A step 8 fails early; surface to human for quota request before continuing |
| App SA lacks Owner/Editor on new project (user might have only granted scoped roles) | medium | Phase A step 7 fails on missing IAM admin; user adds `roles/owner` temporarily, then we proceed |
| `.env` doesn't have all 16 secret values | medium | Phase D step 4 audit script enumerates gaps before any deploy; user fills in missing values from Cloudflare Worker secrets or password manager |
| `WORKFLOW_SERVICE_SECRET` drift between Cloud Run and Supabase Edge Functions | high (breaks workflow execution) | We do NOT rotate this value; we copy `.env`'s value into Secret Manager verbatim. If Supabase's value happens to differ from `.env`, that's a pre-existing bug surfaced (not caused) by this migration |
| `ADMIN_ENCRYPTION_KEY` accidentally rotated | catastrophic (bricks `integration_credentials`) | Hard-coded into the audit script: the value's SHA-256 in the new Secret Manager MUST match the SHA-256 of the value in `.env` |
| Cloudflare Worker secret swap propagates before Cloud Run is ready | low | We deploy Cloud Run first (Phase F), smoke it (Phase G), then swap Cloudflare (Phase H). Order is strict |
| Old project gets accidentally deleted | low | We are not deleting anything in the old project — only scaling Cloud Run to 0. Image hash and Secret Manager remain for forensic value |
| docker pull from billing-disabled old AR is also gated (Phase J.5 prerequisite uncertain) | medium | Implementation phase tests pull first. If gated, prompts user before re-enabling old billing temporarily. User can also choose to bypass Phase J.5 entirely, accepting that Phase G smoke is the only safety net |
| Old project billing gets accidentally LEFT ENABLED after Phase J.5 mirror step | medium (cost leak) | J5c verification check explicitly confirms billing state restored. Pre-flight in J.5 records the *initial* billing state so we know what to restore to |
| `pikar-edge-api` Worker route conflict | low | We don't touch `[[routes]]` blocks in either `wrangler.toml`; only `wrangler secret put`. The Worker keeps the same route attachment |
| Memorystore single-VM eviction during cutover | low | Cache circuit breaker tolerates Redis unavailability via fallback path. Worst case: ~5 minutes of slower responses until cache warms up |

---

## 8. Out of scope (explicitly deferred)

- **Terraform reconciliation** — `deployment/terraform/` still describes the old project shape. We do not touch it in this migration; the new project is provisioned imperatively. A follow-up phase can codify the new project as a separate Terraform workspace, but it is not blocking.
- **CI / Cloud Build triggers** — old project's GitHub triggers stay disabled (project has no billing). New project gets no CI in this round. Deploys are manual via `scripts/deploy-fast.ps1` until a follow-up phase wires CI.
- **Old project deletion** — out of scope. We only scale Cloud Run to 0 (D4). Project deletion is a separate decision the user makes later.
- **`.env` cleanup** — the local `.env` will contain values that are now in Secret Manager. We do not modify `.env` because dev workflows depend on it.
- **Secret rotation** — values carry over unchanged. Any rotation is a separate change-window with its own runbook.
- **Region change** — we stay in `us-central1` for parity. No multi-region or region migration.
- **Vertex model upgrade** — `GEMINI_AGENT_MODEL_PRIMARY/FALLBACK` carry over as `gemini-2.5-pro`/`gemini-2.5-flash`. The Gemini 3 migration is tracked separately (memory: `project_gemini3_migration.md`).

---

## 9. Verification checklist (single-line items)

These become acceptance criteria in the implementation plan:

- [ ] A1: gcloud authenticated as `pikar-ai@project-c3a75795-f866-4b37-8ec.iam.gserviceaccount.com`
- [ ] A2: all 14 APIs enabled on new project
- [ ] A3: app SA has all 7 parity roles
- [ ] A4: Vertex AI `gemini-2.5-pro` and `gemini-2.5-flash` reachable in us-central1
- [ ] B1: VPC connector `pikar-ai-connector` state=READY
- [ ] B2: Memorystore `pikar-ai-cache` state=READY, tier=BASIC, size=1GB
- [ ] C1: Image tagged `<git-sha>` pushed to new AR
- [ ] D1: 16 Secret Manager secrets created
- [ ] D2: All 16 have a non-empty `latest` version
- [ ] D3: App SA has `secretAccessor` on each secret
- [ ] D4: `ADMIN_ENCRYPTION_KEY` value SHA-256 matches `.env` value SHA-256
- [ ] E1: `gs://pikar-ai-c3a75-logs` exists, app SA can write
- [ ] F1: Cloud Run revision READY at 0% traffic
- [ ] G1: 6 smoke checks pass on direct revision URL
- [ ] G2: Traffic promoted to 100% on new revision
- [ ] H1: `wrangler secret put` succeeded on both Workers
- [ ] H2: `npx wrangler deploy` succeeded on both Workers
- [ ] H3: `curl https://api.pikar-ai.com/health/live` returns 200 within 60s
- [ ] H4: New project Cloud Run logs show inbound traffic
- [ ] I1: 5 Cloud Scheduler jobs created and enabled
- [ ] I2: Each job's first manual run returns 2xx
- [ ] J5a: `rollback-pre-cutover-0eecac59` tag exists in new AR
- [ ] J5b: New AR image digest matches `sha256:0eecac59...`
- [ ] J5c: Old project billing state is identical to its pre-migration state (re-disabled if temporarily enabled for the mirror step)
- [ ] J1: Old Cloud Run `min=max=0`, no active instances

---

## 10. Reference values

These are the literals that will be substituted at execution time. Recording them here so the implementation plan does not have to re-discover them:

```
OLD_PROJECT_ID         = pikar-ai-project
OLD_PROJECT_NUMBER     = 917671810739
OLD_SA                 = agents@pikar-ai-project.iam.gserviceaccount.com
OLD_IMAGE_DIGEST       = sha256:0eecac59a74d5e24b09fe8107185466f4348084e4fa433135d268a2fe3b14d69
OLD_RUN_URL            = https://pikar-ai-917671810739.us-central1.run.app
OLD_REDIS_HOST         = 10.131.85.107   (will not transfer)
OLD_LOGS_BUCKET        = gs://pikar-ai-project-logs

NEW_PROJECT_ID         = project-c3a75795-f866-4b37-8ec
NEW_PROJECT_NUMBER     = (read at Phase A step 5)
NEW_SA                 = pikar-ai@project-c3a75795-f866-4b37-8ec.iam.gserviceaccount.com
NEW_SA_KEY_PATH        = secrets/project-c3a75795-f866-4b37-8ec-d48bbc59e196.json
NEW_LOGS_BUCKET        = gs://pikar-ai-c3a75-logs
NEW_REDIS_NAME         = pikar-ai-cache
NEW_VPC_CONNECTOR      = pikar-ai-connector

SUPABASE_URL           = https://rbdowedrdhtlbngapexj.supabase.co   (unchanged)
CLOUDFLARE_EDGE_WORKER = deployment/cloudflare/edge-api    (origin = AGENT_BACKEND_ORIGIN secret)
CLOUDFLARE_PUB_WORKER  = deployment/cloudflare/public-api  (origin = FALLBACK_BACKEND_ORIGIN secret)
```
