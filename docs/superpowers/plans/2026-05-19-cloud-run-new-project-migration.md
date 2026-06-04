# Cloud Run new-project migration — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the `pikar-ai` Cloud Run workload from the billing-disabled `pikar-ai-project` to a brand-new GCP project (`project-c3a75795-f866-4b37-8ec`) with zero user-visible downtime, by deploying full-parity infrastructure in the new project and then atomically swapping Cloudflare Worker backend origins.

**Architecture:** Imperative provisioning (no Terraform) using PowerShell + `gcloud` + `docker` + `wrangler` from the operator's Windows workstation. Cutover uses Cloudflare Worker `wrangler secret put AGENT_BACKEND_ORIGIN` + `npx wrangler deploy` as the atomic flip — Cloudflare DNS, routes, and worker code stay untouched. Rollback is layered: (1) Cloudflare revert to old backend, (2) redeploy mirrored old image in new project, (3) fix forward.

**Tech Stack:** PowerShell 7+, `gcloud` CLI, `docker` (local), `npx wrangler` (Cloudflare), Memorystore Redis 7.0 (Basic, 1GB), Cloud Run on us-central1, Artifact Registry, Secret Manager.

**Source spec:** `docs/superpowers/specs/2026-05-19-cloud-run-new-project-migration-design.md` (commit `a0b540f0`, branch `infra/cloud-run-new-project-migration`)

---

## Constants

These values are referenced throughout the plan. The implementer should NOT re-discover them.

```
OLD_PROJECT_ID         = pikar-ai-project
OLD_PROJECT_NUMBER     = 917671810739
OLD_SA                 = agents@pikar-ai-project.iam.gserviceaccount.com
OLD_IMAGE_DIGEST       = sha256:0eecac59a74d5e24b09fe8107185466f4348084e4fa433135d268a2fe3b14d69
OLD_RUN_URL            = https://pikar-ai-917671810739.us-central1.run.app
OLD_LOGS_BUCKET        = gs://pikar-ai-project-logs

NEW_PROJECT_ID         = project-c3a75795-f866-4b37-8ec
NEW_SA                 = pikar-ai@project-c3a75795-f866-4b37-8ec.iam.gserviceaccount.com
NEW_SA_KEY_PATH        = secrets\project-c3a75795-f866-4b37-8ec-d48bbc59e196.json
NEW_LOGS_BUCKET        = gs://pikar-ai-c3a75-logs
NEW_REDIS_NAME         = pikar-ai-cache
NEW_VPC_CONNECTOR      = pikar-ai-connector
NEW_AR_REPO            = cloud-run-source-deploy
NEW_GCLOUD_CONFIG_NAME = pikar-ai-c3a75

REGION                 = us-central1
REGION_ZONE            = us-central1-a
SUPABASE_URL           = https://rbdowedrdhtlbngapexj.supabase.co
```

`NEW_PROJECT_NUMBER` is captured in Task 2 and re-used as `$NEW_PROJECT_NUMBER` in later PowerShell snippets.

---

## File structure

This plan creates/modifies the following files:

```
scripts/
  deploy-fast.ps1                          MODIFY — add -BuildOnly switch (Task 9)
  migration/
    audit-secrets-gap.ps1                  CREATE — gap-check script for the 16 secrets (Task 11)
docs/
  superpowers/
    plans/
      2026-05-19-cloud-run-new-project-migration.md   CREATE (this file)
    specs/
      2026-05-19-cloud-run-new-project-migration-design.md   (already committed)
```

No other code is modified. Cloudflare worker source code, Terraform, app code, and the frontend are all untouched.

---

## Pre-flight checklist (before any task begins)

The implementer MUST confirm before starting Task 1:

- [ ] `secrets\project-c3a75795-f866-4b37-8ec-d48bbc59e196.json` exists and is readable (this is the new SA key — gitignored, sensitive)
- [ ] `.env` exists at repo root (will be the source for many secret values)
- [ ] User has Cloudflare wrangler authenticated (the `.wrangler/cache/wrangler-account.json` files in `deployment/cloudflare/*/` should exist; if not, run `npx wrangler login` first)
- [ ] Docker Desktop is running (verify: `docker info` exits 0)
- [ ] Currently on branch `infra/cloud-run-new-project-migration` (the spec lives here). If not: `git checkout infra/cloud-run-new-project-migration`
- [ ] All tests passing on main (smoke check — we are not modifying code, but want a known-good baseline)

---

## Task 1: Save current gcloud configuration and verify SA key

**Why:** The active gcloud config currently points at `pikar-ai-project` with user `africantouch.official@gmail.com` (per session-start observation). We must preserve this context — switching to the new project must use a SEPARATE configuration so we can flip back to the old project for rollback queries without re-authenticating.

**Files:** None modified. PowerShell session state only.

- [ ] **Step 1: Capture current gcloud state for restoration later**

Run:
```powershell
$savedActiveConfig = (gcloud config configurations list --filter="is_active:true" --format="value(name)").Trim()
"Original active config: $savedActiveConfig" | Tee-Object -FilePath secrets\migration-checkpoint.txt
```

Expected: a file `secrets\migration-checkpoint.txt` exists with one line, e.g. `Original active config: default`.

- [ ] **Step 2: Verify the new SA key file is readable JSON with the expected project_id**

Run:
```powershell
$keyPath = "secrets\project-c3a75795-f866-4b37-8ec-d48bbc59e196.json"
$key = Get-Content $keyPath -Raw | ConvertFrom-Json
if ($key.project_id -ne "project-c3a75795-f866-4b37-8ec") { throw "project_id mismatch in SA key: got $($key.project_id)" }
if ($key.client_email -ne "pikar-ai@project-c3a75795-f866-4b37-8ec.iam.gserviceaccount.com") { throw "client_email mismatch in SA key" }
"SA key validated: project=$($key.project_id), client_email=$($key.client_email)"
```

Expected output: `SA key validated: project=project-c3a75795-f866-4b37-8ec, client_email=pikar-ai@project-c3a75795-f866-4b37-8ec.iam.gserviceaccount.com`

If it throws, STOP — the SA key file is wrong or corrupt; do not proceed.

- [ ] **Step 3: Record SHA-256 of the local ADMIN_ENCRYPTION_KEY value (sentinel for Task 13)**

Run:
```powershell
$envContent = Get-Content .env -Raw
$adminKey = ($envContent -split "`n" | Where-Object { $_ -match '^ADMIN_ENCRYPTION_KEY=' } | Select-Object -First 1) -replace '^ADMIN_ENCRYPTION_KEY=', ''
if (-not $adminKey) { throw "ADMIN_ENCRYPTION_KEY not found in .env — cannot proceed; would brick integration_credentials" }
$adminKeyHash = (Get-FileHash -InputStream ([System.IO.MemoryStream]::new([System.Text.Encoding]::UTF8.GetBytes($adminKey))) -Algorithm SHA256).Hash
"ADMIN_ENCRYPTION_KEY local hash: $adminKeyHash" | Add-Content secrets\migration-checkpoint.txt
"Recorded local ADMIN_ENCRYPTION_KEY hash: $adminKeyHash"
```

Expected output: `Recorded local ADMIN_ENCRYPTION_KEY hash: <64-char hex>`

If it throws, STOP — there is no usable source for ADMIN_ENCRYPTION_KEY locally. User must provide before proceeding.

---

## Task 2: Authenticate as new SA and create dedicated gcloud configuration

**Why:** Isolating the new project's auth in its own `gcloud config configuration` lets us trivially `gcloud config configurations activate <name>` to swap between old and new for the duration of the migration.

**Files:** None.

- [ ] **Step 1: Activate the new SA**

Run:
```powershell
gcloud auth activate-service-account --key-file="secrets\project-c3a75795-f866-4b37-8ec-d48bbc59e196.json"
```

Expected: `Activated service account credentials for: [pikar-ai@project-c3a75795-f866-4b37-8ec.iam.gserviceaccount.com]`

- [ ] **Step 2: Create a dedicated gcloud configuration**

Run:
```powershell
gcloud config configurations create pikar-ai-c3a75 2>&1
gcloud config set account pikar-ai@project-c3a75795-f866-4b37-8ec.iam.gserviceaccount.com
gcloud config set project project-c3a75795-f866-4b37-8ec
gcloud config set compute/region us-central1
gcloud config set run/region us-central1
```

Expected: `Created [pikar-ai-c3a75].` followed by `Activated [pikar-ai-c3a75].` and `Updated property [...]` for each set command.

If the `create` step says "already exists", that's fine — run `gcloud config configurations activate pikar-ai-c3a75` instead and continue with the `set` commands.

- [ ] **Step 3: Capture project number for use throughout the rest of the plan**

Run:
```powershell
$NEW_PROJECT_NUMBER = (gcloud projects describe project-c3a75795-f866-4b37-8ec --format="value(projectNumber)").Trim()
if (-not $NEW_PROJECT_NUMBER) { throw "Could not resolve new project number — IAM may be insufficient" }
"NEW_PROJECT_NUMBER: $NEW_PROJECT_NUMBER" | Add-Content secrets\migration-checkpoint.txt
"Project number captured: $NEW_PROJECT_NUMBER"
```

Expected output: `Project number captured: <12-digit number>`

If it throws or returns empty, the SA likely lacks `roles/resourcemanager.projectViewer` (or higher). User must grant Owner temporarily before proceeding. The implementer should STOP and report this to the user.

- [ ] **Step 4: Validate SA permission breadth with a non-destructive read**

Run:
```powershell
gcloud projects get-iam-policy project-c3a75795-f866-4b37-8ec --format="value(bindings.role)" 2>&1 | Select-Object -First 5
```

Expected: a list of role names (e.g. `roles/owner`, `roles/iam.serviceAccountAdmin`, ...). If this errors with `PERMISSION_DENIED` or `403`, the SA is missing IAM read perms — STOP and ask user to grant `roles/owner` or at minimum `roles/resourcemanager.projectIamAdmin`.

---

## Task 3: Enable required GCP APIs in new project

**Why:** A brand-new project has only the most basic APIs enabled by default. The migration requires 14 specific services.

**Files:** None.

- [ ] **Step 1: Enable all 14 APIs in one batched call**

Run:
```powershell
gcloud services enable `
  run.googleapis.com `
  artifactregistry.googleapis.com `
  secretmanager.googleapis.com `
  aiplatform.googleapis.com `
  redis.googleapis.com `
  vpcaccess.googleapis.com `
  compute.googleapis.com `
  storage.googleapis.com `
  cloudbuild.googleapis.com `
  cloudscheduler.googleapis.com `
  iamcredentials.googleapis.com `
  logging.googleapis.com `
  monitoring.googleapis.com `
  cloudtrace.googleapis.com `
  --project=project-c3a75795-f866-4b37-8ec
```

Expected: a single `Operation "operations/..." finished successfully.` after roughly 30-60 seconds (the batch enable runs in parallel).

If a specific service fails ("Service X is not available for billing account Y"), it usually means billing isn't fully propagated. Wait 60 seconds and re-run.

- [ ] **Step 2: Verify all 14 APIs are now ENABLED**

Run:
```powershell
$expected = @(
  'run.googleapis.com','artifactregistry.googleapis.com','secretmanager.googleapis.com',
  'aiplatform.googleapis.com','redis.googleapis.com','vpcaccess.googleapis.com',
  'compute.googleapis.com','storage.googleapis.com','cloudbuild.googleapis.com',
  'cloudscheduler.googleapis.com','iamcredentials.googleapis.com',
  'logging.googleapis.com','monitoring.googleapis.com','cloudtrace.googleapis.com'
)
$enabled = (gcloud services list --enabled --project=project-c3a75795-f866-4b37-8ec --format="value(NAME)" 2>&1) -split "`n"
$missing = $expected | Where-Object { $_ -notin $enabled }
if ($missing) { throw "Missing APIs: $($missing -join ', ')" } else { "All 14 APIs enabled." }
```

Expected output: `All 14 APIs enabled.`

If it throws, re-run Step 1 and then Step 2 again.

---

## Task 4: Grant the 7 parity IAM roles to the app SA

**Why:** The app SA needs Vertex AI, storage, secrets, logging, tracing, and discovery access at runtime. These roles match the `app_sa_roles` declared in `deployment/terraform/variables.tf:53-66`.

**Files:** None.

- [ ] **Step 1: Bind all 7 roles**

Run:
```powershell
$appSa = "serviceAccount:pikar-ai@project-c3a75795-f866-4b37-8ec.iam.gserviceaccount.com"
$roles = @(
  'roles/aiplatform.user',
  'roles/discoveryengine.editor',
  'roles/logging.logWriter',
  'roles/cloudtrace.agent',
  'roles/storage.admin',
  'roles/serviceusage.serviceUsageConsumer',
  'roles/secretmanager.secretAccessor'
)
foreach ($r in $roles) {
  gcloud projects add-iam-policy-binding project-c3a75795-f866-4b37-8ec --member=$appSa --role=$r --condition=None --quiet | Out-Null
  "  bound $r"
}
"Done."
```

Expected output: 7 lines `  bound roles/...` followed by `Done.`

- [ ] **Step 2: Verify all 7 are now bound**

Run:
```powershell
$bound = (gcloud projects get-iam-policy project-c3a75795-f866-4b37-8ec `
  --flatten="bindings[].members" `
  --filter="bindings.members:serviceAccount:pikar-ai@project-c3a75795-f866-4b37-8ec.iam.gserviceaccount.com" `
  --format="value(bindings.role)") -split "`n"
$expected = @('roles/aiplatform.user','roles/discoveryengine.editor','roles/logging.logWriter','roles/cloudtrace.agent','roles/storage.admin','roles/serviceusage.serviceUsageConsumer','roles/secretmanager.secretAccessor')
$missing = $expected | Where-Object { $_ -notin $bound }
if ($missing) { throw "Missing role bindings: $($missing -join ', ')" } else { "All 7 IAM roles bound to app SA." }
```

Expected: `All 7 IAM roles bound to app SA.`

---

## Task 5: Verify Vertex AI quota for Gemini 2.5 family

**Why:** Brand-new projects sometimes start at zero quota for specific Gemini models. We need to confirm `gemini-2.5-pro` and `gemini-2.5-flash` are reachable in `us-central1` BEFORE building infrastructure that depends on them.

**Files:** None.

- [ ] **Step 1: Check Gemini 2.5 model availability**

Run:
```powershell
$models = gcloud ai models list --region=us-central1 --project=project-c3a75795-f866-4b37-8ec 2>&1
"Output of ai models list:"
$models
```

Expected: a list including model entries with names like `gemini-2.5-pro` and `gemini-2.5-flash`, OR an empty list (which is also acceptable — Gemini models are accessed via `generateContent` not via the AI Platform `models` resource, so an empty list does NOT necessarily mean no quota).

- [ ] **Step 2: Issue a one-shot generate call as a real quota test**

Run:
```powershell
$accessToken = (gcloud auth print-access-token).Trim()
$body = @{
  contents = @(@{
    role = "user"
    parts = @(@{ text = "Say only OK in one word." })
  })
} | ConvertTo-Json -Depth 5
$response = Invoke-RestMethod -Method POST `
  -Uri "https://us-central1-aiplatform.googleapis.com/v1/projects/project-c3a75795-f866-4b37-8ec/locations/us-central1/publishers/google/models/gemini-2.5-flash:generateContent" `
  -Headers @{ Authorization = "Bearer $accessToken"; "Content-Type" = "application/json" } `
  -Body $body
if ($response.candidates[0].content.parts[0].text) { "Vertex AI OK — Gemini 2.5 Flash responded: $($response.candidates[0].content.parts[0].text.Trim())" } else { throw "Vertex AI returned no text" }
```

Expected: `Vertex AI OK — Gemini 2.5 Flash responded: OK` (or any short response).

If you get a `403` with "Permission denied" — the SA lacks `roles/aiplatform.user`; re-run Task 4.
If you get a `429` or "Quota exceeded" — surface to user: they need to request quota for Gemini 2.5 family in us-central1 via the GCP console **before any further task**. STOP here.

---

## Task 6: Create Serverless VPC Access connector

**Why:** Cloud Run reaches Memorystore (private IP) only through a VPC connector. The old project had this at `pikar-ai-connector`, range `10.8.0.0/28`, network `default`. We mirror that exactly.

**Files:** None.

- [ ] **Step 1: Create the connector**

Run:
```powershell
gcloud compute networks vpc-access connectors create pikar-ai-connector `
  --project=project-c3a75795-f866-4b37-8ec `
  --region=us-central1 `
  --network=default `
  --range=10.8.0.0/28 `
  --min-throughput=200 `
  --max-throughput=300
```

Expected: This takes ~2-3 minutes to complete. Final output is a YAML block with `state: READY`.

- [ ] **Step 2: Verify READY state**

Run:
```powershell
$state = (gcloud compute networks vpc-access connectors describe pikar-ai-connector --region=us-central1 --project=project-c3a75795-f866-4b37-8ec --format="value(state)").Trim()
if ($state -ne "READY") { throw "VPC connector not READY: state=$state" } else { "VPC connector READY." }
```

Expected: `VPC connector READY.`

---

## Task 7: Create Memorystore Redis instance (Basic, 1 GB)

**Why:** Matches the old project's actual config (`tier=BASIC`, `memory_size_gb=1`) confirmed against `deployment/terraform/redis.tf:8-9`. The app's cache circuit breaker tolerates Redis outages, so Basic is acceptable.

**Files:** None.

- [ ] **Step 1: Create the instance**

Run:
```powershell
gcloud redis instances create pikar-ai-cache `
  --project=project-c3a75795-f866-4b37-8ec `
  --region=us-central1 `
  --zone=us-central1-a `
  --tier=basic `
  --size=1 `
  --redis-version=redis_7_0 `
  --network=default `
  --display-name="pikar-ai Cache" `
  --labels=app=pikar-ai,env=production
```

Expected: This takes ~5-10 minutes. Final output is YAML with `state: READY` and a `host` (IP address).

- [ ] **Step 2: Capture REDIS_HOST + REDIS_PORT for the Cloud Run deploy**

Run:
```powershell
$REDIS_HOST = (gcloud redis instances describe pikar-ai-cache --region=us-central1 --project=project-c3a75795-f866-4b37-8ec --format="value(host)").Trim()
$REDIS_PORT = (gcloud redis instances describe pikar-ai-cache --region=us-central1 --project=project-c3a75795-f866-4b37-8ec --format="value(port)").Trim()
if (-not $REDIS_HOST -or -not $REDIS_PORT) { throw "Failed to capture Redis host/port" }
"REDIS_HOST: $REDIS_HOST" | Add-Content secrets\migration-checkpoint.txt
"REDIS_PORT: $REDIS_PORT" | Add-Content secrets\migration-checkpoint.txt
"Captured: REDIS_HOST=$REDIS_HOST REDIS_PORT=$REDIS_PORT"
```

Expected: `Captured: REDIS_HOST=10.x.x.x REDIS_PORT=6379`

---

## Task 8: Create Artifact Registry repo and configure docker auth

**Why:** Cloud Run pulls images from Artifact Registry. We need a docker-format repo in the new project, and docker on the host must trust the AR endpoint.

**Files:** None.

- [ ] **Step 1: Create the AR repo**

Run:
```powershell
gcloud artifacts repositories create cloud-run-source-deploy `
  --project=project-c3a75795-f866-4b37-8ec `
  --location=us-central1 `
  --repository-format=docker `
  --description="Cloud Run source deploy"
```

Expected: `Created repository [cloud-run-source-deploy].`

- [ ] **Step 2: Configure docker to authenticate to AR**

Run:
```powershell
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
```

Expected: `Adding credentials for: us-central1-docker.pkg.dev` and `Docker configuration file updated.`

- [ ] **Step 3: Verify AR is reachable**

Run:
```powershell
gcloud artifacts repositories describe cloud-run-source-deploy --location=us-central1 --project=project-c3a75795-f866-4b37-8ec --format="value(name,format)"
```

Expected: A line containing `cloud-run-source-deploy` and `DOCKER`.

---

## Task 9: Add `-BuildOnly` flag to `scripts/deploy-fast.ps1`

**Why:** Phase F of the spec deploys with `--no-traffic` and explicit env vars unfamiliar to `deploy-fast.ps1`. To use the script's build+push leg without its deploy leg, we add a `-BuildOnly` switch. This is a small, reusable improvement.

**Files:**
- Modify: `scripts/deploy-fast.ps1`

- [ ] **Step 1: Add the new switch parameter**

Edit `scripts/deploy-fast.ps1` line 14-17 — change:
```powershell
param(
    [switch]$SkipBuild,
    [string]$Tag = ""
)
```
to:
```powershell
param(
    [switch]$SkipBuild,
    [switch]$BuildOnly,
    [string]$Tag = ""
)
```

- [ ] **Step 2: Skip the deploy leg when `-BuildOnly` is set**

In `scripts/deploy-fast.ps1`, find the section starting at line 102 (`# --- deploy ---`). Wrap the entire deploy block (lines 102-137, from `Write-Output ""` through `Write-Output "[3/3] Deploy complete in ${deployDur}s"`) in:
```powershell
if (-not $BuildOnly) {
    # ... existing deploy block (lines 102-137) unchanged ...
} else {
    Write-Output ""
    Write-Output "[3/3] Skipped (BuildOnly mode)."
}
```

- [ ] **Step 3: Sanity-check the edited script by running with `-BuildOnly -SkipBuild`**

Run:
```powershell
pwsh scripts\deploy-fast.ps1 -BuildOnly -SkipBuild
```

Expected output ends with:
```
[1/3 + 2/3] Skipped (re-deploying existing tag <sha>)

[3/3] Skipped (BuildOnly mode).
```

(It will use the OLD project per the script's `gcloud config get-value project`. That's fine for this dry-run — we're only testing the flag wiring.)

- [ ] **Step 4: Commit the change**

```powershell
git add scripts/deploy-fast.ps1
git commit -m "chore(deploy): add -BuildOnly flag to deploy-fast.ps1 to skip the gcloud deploy leg"
```

---

## Task 10: Build and push the image to the new project's AR

**Why:** Cloud Run needs an image to deploy. We build from the current branch HEAD (assumed clean, on `main` or a release branch).

**Files:** None.

- [ ] **Step 1: Verify the active gcloud config points at the new project**

Run:
```powershell
$activeProject = (gcloud config get-value project).Trim()
if ($activeProject -ne "project-c3a75795-f866-4b37-8ec") {
  throw "gcloud project is $activeProject; expected project-c3a75795-f866-4b37-8ec. Run: gcloud config configurations activate pikar-ai-c3a75"
}
"Active project: $activeProject — correct."
```

Expected: `Active project: project-c3a75795-f866-4b37-8ec — correct.`

- [ ] **Step 2: Run the build+push leg**

Run:
```powershell
pwsh scripts\deploy-fast.ps1 -BuildOnly
```

This will:
1. Resolve git SHA as the image tag
2. Build the docker image (3-8 minutes depending on cache)
3. Push to `us-central1-docker.pkg.dev/project-c3a75795-f866-4b37-8ec/cloud-run-source-deploy/pikar-ai:<sha>`

Expected output ends with: `[3/3] Skipped (BuildOnly mode).` and an image tag line above it.

- [ ] **Step 3: Capture the image tag for Task 15**

Run:
```powershell
$gitSha = (git rev-parse --short HEAD).Trim()
$NEW_IMAGE = "us-central1-docker.pkg.dev/project-c3a75795-f866-4b37-8ec/cloud-run-source-deploy/pikar-ai:$gitSha"
"NEW_IMAGE: $NEW_IMAGE" | Add-Content secrets\migration-checkpoint.txt
"Image tag captured: $NEW_IMAGE"
```

Expected: `Image tag captured: us-central1-docker.pkg.dev/project-c3a75795-f866-4b37-8ec/cloud-run-source-deploy/pikar-ai:<7-char sha>`

- [ ] **Step 4: Verify image is in AR**

Run:
```powershell
gcloud artifacts docker images list us-central1-docker.pkg.dev/project-c3a75795-f866-4b37-8ec/cloud-run-source-deploy/pikar-ai --project=project-c3a75795-f866-4b37-8ec --format="value(IMAGE,DIGEST,CREATE_TIME)" --limit=3
```

Expected: at least one row with today's CREATE_TIME and a DIGEST starting with `sha256:`.

---

## Task 11: Create the secret-audit gap-check script

**Why:** Before we populate Secret Manager, we need to know which of the 16 required secrets we already have values for (in `.env` or `wrangler secret list`) and which need user input. This script is also re-run in Task 13 to verify the populated state.

**Files:**
- Create: `scripts/migration/audit-secrets-gap.ps1`

- [ ] **Step 1: Create the script directory**

```powershell
New-Item -ItemType Directory -Path scripts\migration -Force | Out-Null
```

- [ ] **Step 2: Write the audit script**

Create `scripts/migration/audit-secrets-gap.ps1` with this exact content:

```powershell
# Audit which of the 16 required secrets have known sources and which are gaps.
# Usage:
#   pwsh scripts/migration/audit-secrets-gap.ps1                  # local audit only (.env + wrangler)
#   pwsh scripts/migration/audit-secrets-gap.ps1 -RemoteCheck     # also verify each is in Secret Manager and non-empty

param(
    [switch]$RemoteCheck
)

$ErrorActionPreference = 'Stop'

# Mapping: env_name -> sm_secret_name
$secrets = [ordered]@{
    'SCHEDULER_SECRET'                = 'pikar-ai-scheduler-secret'
    'SUPABASE_SERVICE_ROLE_KEY'       = 'pikar-ai-supabase-service-role-key'
    'SUPABASE_JWT_SECRET'             = 'pikar-ai-supabase-jwt-secret'
    'ADMIN_ENCRYPTION_KEY'            = 'pikar-ai-admin-encryption-key'
    'TAVILY_API_KEY'                  = 'pikar-ai-tavily-api-key'
    'FIRECRAWL_API_KEY'               = 'pikar-ai-firecrawl-api-key'
    'RESEND_API_KEY'                  = 'pikar-ai-resend-api-key'
    'RESEND_WEBHOOK_SECRET'           = 'pikar-ai-resend-webhook-secret'
    'FACEBOOK_APP_SECRET'             = 'pikar-ai-facebook-app-secret'
    'TIKTOK_CLIENT_SECRET'            = 'pikar-ai-tiktok-client-secret'
    'LINKEDIN_CLIENT_SECRET'          = 'pikar-ai-linkedin-client-secret'
    'LINKEDIN_WEBHOOK_SECRET'         = 'pikar-ai-linkedin-webhook-secret'
    'HUBSPOT_CLIENT_SECRET'           = 'pikar-ai-hubspot-client-secret'
    'SHOPIFY_CLIENT_SECRET'           = 'pikar-ai-shopify-client-secret'
    'WORKFLOW_SERVICE_SECRET'         = 'pikar-ai-workflow-service-secret'
    'GOOGLE_WORKSPACE_CLIENT_SECRET'  = 'pikar-ai-google-workspace-client-secret'
}

# Load .env values into a hashtable (no echoing values)
$envValues = @{}
if (Test-Path .env) {
    foreach ($line in Get-Content .env) {
        if ($line -match '^([A-Z_]+)=(.*)$') {
            $envValues[$matches[1]] = $matches[2]
        }
    }
}

# Load wrangler secrets list (public-api) — name-only
$wranglerSecrets = @()
$publicApiPath = "deployment\cloudflare\public-api"
if (Test-Path $publicApiPath) {
    Push-Location $publicApiPath
    try {
        $listJson = (npx wrangler secret list --format json 2>&1) -join "`n"
        if ($listJson -match '^\[') {
            $wranglerSecrets = ($listJson | ConvertFrom-Json) | ForEach-Object { $_.name }
        }
    } catch {
        Write-Warning "Could not list wrangler secrets — auth may be missing"
    } finally {
        Pop-Location
    }
}

$gaps = @()
$ready = @()

Write-Output ("{0,-35} {1,-12} {2,-12} {3}" -f "ENV_NAME","IN_DOTENV","IN_WRANGLER","STATUS")
Write-Output ("-" * 80)
foreach ($envName in $secrets.Keys) {
    $inEnv = $envValues.ContainsKey($envName) -and -not [string]::IsNullOrWhiteSpace($envValues[$envName])
    $inWrangler = $wranglerSecrets -contains $envName
    if ($inEnv -or $inWrangler) {
        $status = "READY"
        $ready += $envName
    } else {
        $status = "GAP"
        $gaps += $envName
    }
    Write-Output ("{0,-35} {1,-12} {2,-12} {3}" -f $envName, $inEnv, $inWrangler, $status)
}

Write-Output ""
Write-Output "READY: $($ready.Count)/16"
Write-Output "GAPS:  $($gaps.Count)/16"
if ($gaps) { Write-Output "Missing values: $($gaps -join ', ')" }

if ($RemoteCheck) {
    Write-Output ""
    Write-Output "Remote check (Secret Manager in new project):"
    $project = "project-c3a75795-f866-4b37-8ec"
    foreach ($envName in $secrets.Keys) {
        $smName = $secrets[$envName]
        try {
            $val = (gcloud secrets versions access latest --secret=$smName --project=$project 2>&1)
            if ($LASTEXITCODE -eq 0 -and $val.Length -gt 0) {
                Write-Output ("  OK     {0,-35} (len={1})" -f $envName, $val.Length)
            } else {
                Write-Output ("  MISSING {0,-35}" -f $envName)
            }
        } catch {
            Write-Output ("  ERROR  {0,-35} ({1})" -f $envName, $_.Exception.Message)
        }
    }
}

if ($gaps -and -not $RemoteCheck) { exit 1 } else { exit 0 }
```

- [ ] **Step 3: Run the local-only audit**

Run:
```powershell
pwsh scripts\migration\audit-secrets-gap.ps1
```

Expected: a 16-row table. The implementer must record which envs are GAP for use in Task 12. If GAPS > 0, the script exits with code 1 — that's expected at this point. If ALL 16 are READY, you can skip Step 4 below.

- [ ] **Step 4: If gaps exist, ask user to supply each missing value**

For each `GAP` row above, ask the user (DO NOT proceed without explicit values):
> "I need the value for `<ENV_NAME>` — please paste it. (Will be written to Secret Manager only, not to disk.)"

Store user-provided values in a session-only hashtable variable `$userSecrets[<env_name>]` for use in Task 12. Do NOT write to `.env` or any file.

- [ ] **Step 5: Commit the audit script**

```powershell
git add scripts/migration/audit-secrets-gap.ps1
git commit -m "chore(migration): add Secret Manager gap-audit script for new project rebuild"
```

---

## Task 12: Create and populate the 16 Secret Manager secrets

**Why:** Cloud Run deploy in Task 15 references these secrets by name. They must exist with at least one version before deploy or the deploy will fail.

**Files:** None.

- [ ] **Step 1: Create all 16 secrets (empty containers)**

Run:
```powershell
$secrets = @(
  'pikar-ai-scheduler-secret','pikar-ai-supabase-service-role-key','pikar-ai-supabase-jwt-secret',
  'pikar-ai-admin-encryption-key','pikar-ai-tavily-api-key','pikar-ai-firecrawl-api-key',
  'pikar-ai-resend-api-key','pikar-ai-resend-webhook-secret','pikar-ai-facebook-app-secret',
  'pikar-ai-tiktok-client-secret','pikar-ai-linkedin-client-secret','pikar-ai-linkedin-webhook-secret',
  'pikar-ai-hubspot-client-secret','pikar-ai-shopify-client-secret','pikar-ai-workflow-service-secret',
  'pikar-ai-google-workspace-client-secret'
)
foreach ($s in $secrets) {
  gcloud secrets create $s --project=project-c3a75795-f866-4b37-8ec --replication-policy=automatic --quiet 2>&1 | Out-Null
  "  created $s"
}
"Done. 16 secrets created."
```

Expected: 16 lines of `  created <name>` then `Done. 16 secrets created.`

If any one fails with "Secret already exists" — that's fine, it means we're re-running; continue.

- [ ] **Step 2: Populate each secret's first version**

For each `<env_name>` in the secret table:
1. If `.env` has a non-empty value for `<env_name>`, use that.
2. Else if `wrangler secret list` (from public-api worker) contains `<env_name>`, fetch with `npx wrangler secret get <env_name>` (this prompts wrangler for the value). Note: as of some wrangler versions, secret values cannot be retrieved — only names listed. In that case, the user must re-supply the value (Step 4 of Task 11).
3. Else use the value captured from `$userSecrets[<env_name>]` in Task 11 Step 4.

Run this block (the implementer fills in each value via the source priority above; do NOT paste literal secret values into the plan, but DO paste them on the command line when running):

```powershell
# Per-secret population. Replace <VALUE> with the actual value from .env, wrangler, or user.
# IMPORTANT: Run each line separately so a failure on one secret does not interrupt others.
# IMPORTANT: Use --data-file=- with echo, NOT --data-file=tmp.txt, to avoid writing secrets to disk.

$secretMap = @{
    'SCHEDULER_SECRET'                = 'pikar-ai-scheduler-secret'
    'SUPABASE_SERVICE_ROLE_KEY'       = 'pikar-ai-supabase-service-role-key'
    'SUPABASE_JWT_SECRET'             = 'pikar-ai-supabase-jwt-secret'
    'ADMIN_ENCRYPTION_KEY'            = 'pikar-ai-admin-encryption-key'
    'TAVILY_API_KEY'                  = 'pikar-ai-tavily-api-key'
    'FIRECRAWL_API_KEY'               = 'pikar-ai-firecrawl-api-key'
    'RESEND_API_KEY'                  = 'pikar-ai-resend-api-key'
    'RESEND_WEBHOOK_SECRET'           = 'pikar-ai-resend-webhook-secret'
    'FACEBOOK_APP_SECRET'             = 'pikar-ai-facebook-app-secret'
    'TIKTOK_CLIENT_SECRET'            = 'pikar-ai-tiktok-client-secret'
    'LINKEDIN_CLIENT_SECRET'          = 'pikar-ai-linkedin-client-secret'
    'LINKEDIN_WEBHOOK_SECRET'         = 'pikar-ai-linkedin-webhook-secret'
    'HUBSPOT_CLIENT_SECRET'           = 'pikar-ai-hubspot-client-secret'
    'SHOPIFY_CLIENT_SECRET'           = 'pikar-ai-shopify-client-secret'
    'WORKFLOW_SERVICE_SECRET'         = 'pikar-ai-workflow-service-secret'
    'GOOGLE_WORKSPACE_CLIENT_SECRET'  = 'pikar-ai-google-workspace-client-secret'
}

# Source .env into a hashtable
$envValues = @{}
foreach ($line in Get-Content .env) {
    if ($line -match '^([A-Z_]+)=(.*)$') { $envValues[$matches[1]] = $matches[2] }
}

foreach ($envName in $secretMap.Keys) {
    $smName = $secretMap[$envName]
    $value = $envValues[$envName]
    if (-not $value -and $userSecrets -and $userSecrets.ContainsKey($envName)) {
        $value = $userSecrets[$envName]
    }
    if (-not $value) {
        Write-Warning "No value for $envName — skipping (secret container exists but has no version)"
        continue
    }
    # Write via stdin so the value never lands on disk
    $value | gcloud secrets versions add $smName --data-file=- --project=project-c3a75795-f866-4b37-8ec --quiet | Out-Null
    "  populated $envName -> $smName"
}
"Done."
```

Expected: up to 16 lines of `  populated X -> Y`, possibly some `WARNING: No value for X — skipping`, then `Done.`

- [ ] **Step 3: Grant the app SA `secretAccessor` on each secret**

The project-level `roles/secretmanager.secretAccessor` from Task 4 covers this. We verify:

```powershell
$appSa = "serviceAccount:pikar-ai@project-c3a75795-f866-4b37-8ec.iam.gserviceaccount.com"
$smName = "pikar-ai-admin-encryption-key"
$canAccess = (gcloud secrets get-iam-policy $smName --project=project-c3a75795-f866-4b37-8ec --format="value(bindings.members)" 2>&1) -contains $appSa
$projectHasRole = (gcloud projects get-iam-policy project-c3a75795-f866-4b37-8ec --flatten="bindings[].members" --filter="bindings.members:$appSa AND bindings.role:roles/secretmanager.secretAccessor" --format="value(bindings.role)") -ne ""
if ($projectHasRole) { "App SA has project-level secretAccessor — covers all secrets." } else { throw "App SA missing secretAccessor at project level. Re-run Task 4." }
```

Expected: `App SA has project-level secretAccessor — covers all secrets.`

---

## Task 13: Audit secrets are populated and ADMIN_ENCRYPTION_KEY integrity is preserved

**Why:** Last gate before deploy. We confirm all 16 secrets have non-empty versions AND that the live ADMIN_ENCRYPTION_KEY matches the local `.env` value (rotation would brick all `integration_credentials`).

**Files:** None.

- [ ] **Step 1: Run remote-check audit**

Run:
```powershell
pwsh scripts\migration\audit-secrets-gap.ps1 -RemoteCheck
```

Expected: every row in the "Remote check" section shows `OK <name> (len=<N>)` with N > 0. If any shows `MISSING` — STOP and re-do Task 12 for that secret.

- [ ] **Step 2: Verify ADMIN_ENCRYPTION_KEY hash matches the local value**

Run:
```powershell
$savedHash = (Select-String -Path secrets\migration-checkpoint.txt -Pattern '^ADMIN_ENCRYPTION_KEY local hash: ' | Select-Object -First 1).Line -replace '^ADMIN_ENCRYPTION_KEY local hash: ', ''
$remoteValue = (gcloud secrets versions access latest --secret=pikar-ai-admin-encryption-key --project=project-c3a75795-f866-4b37-8ec).Trim()
$remoteHash = (Get-FileHash -InputStream ([System.IO.MemoryStream]::new([System.Text.Encoding]::UTF8.GetBytes($remoteValue))) -Algorithm SHA256).Hash
if ($remoteHash -ne $savedHash) {
  throw "ADMIN_ENCRYPTION_KEY HASH MISMATCH: local=$savedHash remote=$remoteHash — DO NOT DEPLOY"
}
"ADMIN_ENCRYPTION_KEY integrity verified (hash match)."
```

Expected: `ADMIN_ENCRYPTION_KEY integrity verified (hash match).`

If the throw fires — STOP. The secret value got mangled in transit. Re-do Task 12 specifically for ADMIN_ENCRYPTION_KEY, taking care to pipe the value via stdin and not via a temp file (Windows line-ending mangling is the usual culprit).

---

## Task 14: Create logs GCS bucket

**Why:** The `LOGS_BUCKET_NAME` env var in Task 15 references this bucket. App writes telemetry logs here.

**Files:** None.

- [ ] **Step 1: Create the bucket**

Run:
```powershell
gcloud storage buckets create gs://pikar-ai-c3a75-logs `
  --project=project-c3a75795-f866-4b37-8ec `
  --location=us-central1 `
  --uniform-bucket-level-access
```

Expected: `Creating gs://pikar-ai-c3a75-logs/...`

If you get `HTTPError 409: ...already exists`, the bucket name is taken globally — choose `pikar-ai-c3a75-logs-1` and update `NEW_LOGS_BUCKET` in `secrets\migration-checkpoint.txt` accordingly.

- [ ] **Step 2: Verify the bucket exists and app SA can write (project-level storage.admin from Task 4 covers it)**

Run:
```powershell
gcloud storage ls gs://pikar-ai-c3a75-logs 2>&1
```

Expected: empty list (bucket exists but has no objects yet) — no error.

---

## Task 15: Deploy Cloud Run revision (at 0% traffic)

**Why:** This is the heart of the migration. The new project gets a Cloud Run service `pikar-ai` with full-parity config. We deploy with `--no-traffic` so the new revision is NOT serving yet — we'll smoke-test it directly at its revision URL in Task 16 before promoting.

**Files:** None.

- [ ] **Step 1: Re-load NEW_PROJECT_NUMBER, REDIS_HOST, REDIS_PORT, NEW_IMAGE from the checkpoint file**

Run:
```powershell
$ckpt = Get-Content secrets\migration-checkpoint.txt -Raw
$NEW_PROJECT_NUMBER = (($ckpt -split "`n" | Where-Object { $_ -match '^NEW_PROJECT_NUMBER: ' } | Select-Object -First 1) -replace '^NEW_PROJECT_NUMBER: ', '').Trim()
$REDIS_HOST = (($ckpt -split "`n" | Where-Object { $_ -match '^REDIS_HOST: ' } | Select-Object -First 1) -replace '^REDIS_HOST: ', '').Trim()
$REDIS_PORT = (($ckpt -split "`n" | Where-Object { $_ -match '^REDIS_PORT: ' } | Select-Object -First 1) -replace '^REDIS_PORT: ', '').Trim()
$NEW_IMAGE = (($ckpt -split "`n" | Where-Object { $_ -match '^NEW_IMAGE: ' } | Select-Object -First 1) -replace '^NEW_IMAGE: ', '').Trim()
if (-not ($NEW_PROJECT_NUMBER -and $REDIS_HOST -and $REDIS_PORT -and $NEW_IMAGE)) { throw "Missing checkpoint values" }
"Loaded: project_num=$NEW_PROJECT_NUMBER redis=${REDIS_HOST}:${REDIS_PORT} image=$NEW_IMAGE"
```

Expected: `Loaded: project_num=<num> redis=<ip>:6379 image=us-central1-...`

- [ ] **Step 2: Capture SUPABASE_ANON_KEY from .env (it's a public JWT, not a secret)**

Run:
```powershell
$envValues = @{}
foreach ($line in Get-Content .env) {
    if ($line -match '^([A-Z_]+)=(.*)$') { $envValues[$matches[1]] = $matches[2] }
}
$SUPABASE_ANON_KEY = $envValues['SUPABASE_ANON_KEY']
if (-not $SUPABASE_ANON_KEY) { throw "SUPABASE_ANON_KEY missing in .env" }
"SUPABASE_ANON_KEY length: $($SUPABASE_ANON_KEY.Length) chars"
```

Expected: `SUPABASE_ANON_KEY length: ~250 chars`

- [ ] **Step 3: Build the env-var argument string**

The Cloud Run CLI uses `;` as separator by default but `ALLOWED_ORIGINS` contains commas. So we use the `^;^` custom-delimiter syntax (per `scripts/deploy-fast.ps1:108`).

Run:
```powershell
$APP_URL = "https://pikar-ai-$NEW_PROJECT_NUMBER.us-central1.run.app"
$version = (Select-String -Path pyproject.toml -Pattern '^version = "(.*)"' | ForEach-Object { $_.Matches[0].Groups[1].Value })
$gitSha = (git rev-parse --short HEAD).Trim()

$envVarPairs = @(
  "APP_URL=$APP_URL",
  "BACKEND_API_URL=$APP_URL",
  "ENVIRONMENT=production",
  "ALLOWED_ORIGINS=https://pikar-ai.com,https://www.pikar-ai.com,https://admin.pikar-ai.com,https://pikar-ai.vercel.app,https://pikar-ai-joelferuzi-gmailcoms-projects.vercel.app,https://pikar-ai-git-main-joelferuzi-gmailcoms-projects.vercel.app",
  "LOGS_BUCKET_NAME=gs://pikar-ai-c3a75-logs",
  "GOOGLE_CLOUD_PROJECT=project-c3a75795-f866-4b37-8ec",
  "GOOGLE_CLOUD_LOCATION=us-central1",
  "GOOGLE_GENAI_USE_VERTEXAI=1",
  "GEMINI_AGENT_MODEL_PRIMARY=gemini-2.5-pro",
  "GEMINI_AGENT_MODEL_FALLBACK=gemini-2.5-flash",
  "SUPABASE_URL=https://rbdowedrdhtlbngapexj.supabase.co",
  "SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY",
  "REQUIRE_STRICT_AUTH=1",
  "ALLOW_ANONYMOUS_CHAT=0",
  "ALLOW_ALL_FEATURES_FOR_TESTING=true",
  "WORKFLOW_STRICT_TOOL_RESOLUTION=true",
  "WORKFLOW_STRICT_CRITICAL_TOOL_GUARD=true",
  "WORKFLOW_ALLOW_FALLBACK_SIMULATION=false",
  "WORKFLOW_ENFORCE_READINESS_GATE=true",
  "REDIS_HOST=$REDIS_HOST",
  "REDIS_PORT=$REDIS_PORT",
  "REDIS_DB=0",
  "REDIS_ENABLED=1",
  "REMOTION_RENDER_ENABLED=1",
  "REMOTION_RENDER_DIR=/code/remotion-render",
  "REMOTION_RENDER_TIMEOUT=300",
  "WEB_CONCURRENCY=2",
  "SKILL_EMBEDDING_WARMUP_ENABLED=0",
  "EMBEDDING_QUOTA_COOLDOWN_SECONDS=900",
  "AGENT_VERSION=$version",
  "COMMIT_SHA=$gitSha",
  "ADMIN_EMAILS=joel@pikar-ai.com",
  "RESEND_FROM_EMAIL=noreply@pikar-ai.com",
  "RESEND_FORWARD_TO=joel.feruzi@gmail.com",
  "FACEBOOK_APP_ID=4064994950416607",
  "TIKTOK_CLIENT_KEY=awktqc6pgvai54qe",
  "LINKEDIN_CLIENT_ID=77f5eslppa1ips",
  "HUBSPOT_CLIENT_ID=36832136",
  "SHOPIFY_CLIENT_ID=735d58083996a927ae6095d41ae60e3a",
  "GOOGLE_WORKSPACE_CLIENT_ID=706895462845-7kfuod6uh18csiu5lk70da2fpklruptn.apps.googleusercontent.com",
  "GOOGLE_WORKSPACE_REDIRECT_URI=https://api.pikar-ai.com/integrations/google_workspace/callback"
)
$ENV_VARS = "^;^" + ($envVarPairs -join ';')
"Env var count: $($envVarPairs.Count)"
```

Expected: `Env var count: 41` (39 from spec + AGENT_VERSION + COMMIT_SHA which are populated per-deploy)

- [ ] **Step 4: Build the set-secrets argument string**

Run:
```powershell
$secretRefs = @(
  "SCHEDULER_SECRET=pikar-ai-scheduler-secret:latest",
  "SUPABASE_SERVICE_ROLE_KEY=pikar-ai-supabase-service-role-key:latest",
  "SUPABASE_JWT_SECRET=pikar-ai-supabase-jwt-secret:latest",
  "ADMIN_ENCRYPTION_KEY=pikar-ai-admin-encryption-key:latest",
  "TAVILY_API_KEY=pikar-ai-tavily-api-key:latest",
  "FIRECRAWL_API_KEY=pikar-ai-firecrawl-api-key:latest",
  "RESEND_API_KEY=pikar-ai-resend-api-key:latest",
  "RESEND_WEBHOOK_SECRET=pikar-ai-resend-webhook-secret:latest",
  "FACEBOOK_APP_SECRET=pikar-ai-facebook-app-secret:latest",
  "TIKTOK_CLIENT_SECRET=pikar-ai-tiktok-client-secret:latest",
  "LINKEDIN_CLIENT_SECRET=pikar-ai-linkedin-client-secret:latest",
  "LINKEDIN_WEBHOOK_SECRET=pikar-ai-linkedin-webhook-secret:latest",
  "HUBSPOT_CLIENT_SECRET=pikar-ai-hubspot-client-secret:latest",
  "SHOPIFY_CLIENT_SECRET=pikar-ai-shopify-client-secret:latest",
  "WORKFLOW_SERVICE_SECRET=pikar-ai-workflow-service-secret:latest",
  "GOOGLE_WORKSPACE_CLIENT_SECRET=pikar-ai-google-workspace-client-secret:latest"
)
$SECRETS = $secretRefs -join ','
"Secret ref count: $($secretRefs.Count)"
```

Expected: `Secret ref count: 16`

- [ ] **Step 5: Deploy the Cloud Run service (at 0% traffic)**

Run:
```powershell
gcloud beta run deploy pikar-ai `
  --image=$NEW_IMAGE `
  --project=project-c3a75795-f866-4b37-8ec `
  --region=us-central1 `
  --service-account=pikar-ai@project-c3a75795-f866-4b37-8ec.iam.gserviceaccount.com `
  --port=8000 `
  --cpu=2 `
  --memory=4Gi `
  --no-cpu-throttling `
  --min-instances=2 `
  --max-instances=10 `
  --concurrency=250 `
  --timeout=1800 `
  --vpc-connector=pikar-ai-connector `
  --vpc-egress=private-ranges-only `
  --allow-unauthenticated `
  --no-traffic `
  --startup-probe="httpGet.path=/health/live,httpGet.port=8000,initialDelaySeconds=10,timeoutSeconds=30,periodSeconds=45,failureThreshold=8" `
  --liveness-probe="httpGet.path=/health/live,httpGet.port=8000,initialDelaySeconds=15,timeoutSeconds=5,periodSeconds=30,failureThreshold=3" `
  --labels="created-by=adk" `
  --set-env-vars=$ENV_VARS `
  --set-secrets=$SECRETS
```

Expected: 3-5 minutes of pulling the image and starting containers. Final output:
```
Deploying container to Cloud Run service [pikar-ai] in project [project-c3a75795-f866-4b37-8ec] region [us-central1]
...
Service [pikar-ai] revision [pikar-ai-00001-xxx] has been deployed and is serving 0 percent of traffic.
```

If the deploy fails with `Container failed to start` — pull logs immediately:
```powershell
gcloud run services logs read pikar-ai --project=project-c3a75795-f866-4b37-8ec --region=us-central1 --limit=100
```

Common causes: missing secret value, REDIS unreachable (VPC connector not READY), Vertex AI quota.

- [ ] **Step 6: Capture revision name for the next task**

Run:
```powershell
$NEW_REVISION = (gcloud run services describe pikar-ai --project=project-c3a75795-f866-4b37-8ec --region=us-central1 --format="value(status.latestCreatedRevisionName)").Trim()
"NEW_REVISION: $NEW_REVISION" | Add-Content secrets\migration-checkpoint.txt
"Captured: NEW_REVISION=$NEW_REVISION"
```

Expected: `Captured: NEW_REVISION=pikar-ai-00001-xxx`

---

## Task 16: Smoke-test the new revision directly (before promoting traffic)

**Why:** Phase G of the spec. We hit the new revision's own URL (not the service URL, since the service is 0% on this revision). If anything is wrong, we abort here — Cloudflare is still pointing at the old project, so users see no impact.

**Files:** None.

- [ ] **Step 1: Get the revision-tagged URL**

Run:
```powershell
$NEW_REVISION = (Select-String -Path secrets\migration-checkpoint.txt -Pattern '^NEW_REVISION: ' | Select-Object -First 1).Line -replace '^NEW_REVISION: ', ''
$NEW_PROJECT_NUMBER = (Select-String -Path secrets\migration-checkpoint.txt -Pattern '^NEW_PROJECT_NUMBER: ' | Select-Object -First 1).Line -replace '^NEW_PROJECT_NUMBER: ', ''

# Tag the revision so it gets a stable URL prefix we can curl
gcloud run services update-traffic pikar-ai `
  --project=project-c3a75795-f866-4b37-8ec `
  --region=us-central1 `
  --set-tags=smoke=$NEW_REVISION `
  --quiet | Out-Null

$SMOKE_URL = "https://smoke---pikar-ai-$NEW_PROJECT_NUMBER.us-central1.run.app"
"SMOKE_URL: $SMOKE_URL" | Add-Content secrets\migration-checkpoint.txt
"Smoke URL: $SMOKE_URL"
```

Expected: `Smoke URL: https://smoke---pikar-ai-<num>.us-central1.run.app`

- [ ] **Step 2: Hit /health/live**

Run:
```powershell
$r = Invoke-WebRequest -Uri "$SMOKE_URL/health/live" -Method GET -TimeoutSec 30 -UseBasicParsing
if ($r.StatusCode -ne 200) { throw "health/live returned $($r.StatusCode)" }
"PASS /health/live ($($r.StatusCode))"
```

Expected: `PASS /health/live (200)`

- [ ] **Step 3: Hit /health/connections (validates Supabase + Redis are reachable)**

Run:
```powershell
$r = Invoke-WebRequest -Uri "$SMOKE_URL/health/connections" -Method GET -TimeoutSec 30 -UseBasicParsing
if ($r.StatusCode -ne 200) { throw "health/connections returned $($r.StatusCode): $($r.Content)" }
"PASS /health/connections ($($r.StatusCode)) body: $($r.Content.Substring(0, [Math]::Min(200,$r.Content.Length)))"
```

Expected: `PASS /health/connections (200) body: {...supabase: ok, cache: ok...}`

If status is non-200 OR the body says cache=down, the VPC connector is likely not reachable from Cloud Run. STOP and investigate.

- [ ] **Step 4: Hit /health/cache (Redis circuit-breaker state)**

Run:
```powershell
$r = Invoke-WebRequest -Uri "$SMOKE_URL/health/cache" -Method GET -TimeoutSec 30 -UseBasicParsing
if ($r.StatusCode -ne 200) { throw "health/cache returned $($r.StatusCode)" }
"PASS /health/cache ($($r.StatusCode))"
```

Expected: `PASS /health/cache (200)`

- [ ] **Step 5: Hit /health/embeddings (Vertex AI access)**

Run:
```powershell
$r = Invoke-WebRequest -Uri "$SMOKE_URL/health/embeddings" -Method GET -TimeoutSec 30 -UseBasicParsing
if ($r.StatusCode -ne 200) { throw "health/embeddings returned $($r.StatusCode)" }
"PASS /health/embeddings ($($r.StatusCode))"
```

Expected: `PASS /health/embeddings (200)`

- [ ] **Step 6: Hit the agent card endpoint**

Run:
```powershell
$r = Invoke-WebRequest -Uri "$SMOKE_URL/a2a/app/.well-known/agent-card.json" -Method GET -TimeoutSec 30 -UseBasicParsing
$card = $r.Content | ConvertFrom-Json
if (-not $card.name) { throw "agent card has no name field" }
"PASS /a2a/app/.well-known/agent-card.json — name=$($card.name)"
```

Expected: `PASS /a2a/app/.well-known/agent-card.json — name=ExecutiveAgent` (or similar)

- [ ] **Step 7: If all 5 smoke checks passed, promote new revision to 100% traffic**

Run:
```powershell
gcloud run services update-traffic pikar-ai `
  --project=project-c3a75795-f866-4b37-8ec `
  --region=us-central1 `
  --to-latest `
  --quiet
```

Expected: a YAML block showing 100% traffic on the new revision.

- [ ] **Step 8: Verify the un-tagged service URL now serves the new revision**

Run:
```powershell
$SERVICE_URL = "https://pikar-ai-$NEW_PROJECT_NUMBER.us-central1.run.app"
$r = Invoke-WebRequest -Uri "$SERVICE_URL/health/live" -Method GET -TimeoutSec 30 -UseBasicParsing
if ($r.StatusCode -ne 200) { throw "production URL /health/live returned $($r.StatusCode)" }
"PASS production URL: $SERVICE_URL/health/live ($($r.StatusCode))"
"NEW_SERVICE_URL: $SERVICE_URL" | Add-Content secrets\migration-checkpoint.txt
```

Expected: `PASS production URL: https://pikar-ai-<num>.us-central1.run.app/health/live (200)`

**STOP-AND-ASK GATE: at this point, Cloud Run new project is fully ready but Cloudflare still points at the OLD project. Before Task 17 (Cloudflare cutover — user-visible), the implementer MUST get explicit user confirmation to proceed.**

---

## Task 17: Cloudflare cutover — edge-api Worker

**Why:** This is the atomic flip. After this task, `api.pikar-ai.com` traffic hits the new Cloud Run.

**Files:** None.

- [ ] **Step 1: Confirm checkpoint values**

Run:
```powershell
$NEW_SERVICE_URL = (Select-String -Path secrets\migration-checkpoint.txt -Pattern '^NEW_SERVICE_URL: ' | Select-Object -First 1).Line -replace '^NEW_SERVICE_URL: ', ''
if (-not $NEW_SERVICE_URL) { throw "NEW_SERVICE_URL not in checkpoint" }
"Will set AGENT_BACKEND_ORIGIN = $NEW_SERVICE_URL"
```

Expected: `Will set AGENT_BACKEND_ORIGIN = https://pikar-ai-<num>.us-central1.run.app`

- [ ] **Step 2: Update edge-api Worker's AGENT_BACKEND_ORIGIN secret**

Run:
```powershell
Push-Location deployment\cloudflare\edge-api
try {
    $NEW_SERVICE_URL | npx wrangler secret put AGENT_BACKEND_ORIGIN
} finally {
    Pop-Location
}
```

Expected: `Success! Uploaded secret AGENT_BACKEND_ORIGIN`

- [ ] **Step 3: Deploy edge-api Worker**

Run:
```powershell
Push-Location deployment\cloudflare\edge-api
try {
    npx wrangler deploy
} finally {
    Pop-Location
}
```

Expected: `Deployed pikar-edge-api triggers (X.XX sec)` followed by `https://api.pikar-ai.com`.

---

## Task 18: Cloudflare cutover — public-api Worker

**Files:** None.

- [ ] **Step 1: Update public-api Worker's FALLBACK_BACKEND_ORIGIN**

Run:
```powershell
$NEW_SERVICE_URL = (Select-String -Path secrets\migration-checkpoint.txt -Pattern '^NEW_SERVICE_URL: ' | Select-Object -First 1).Line -replace '^NEW_SERVICE_URL: ', ''
Push-Location deployment\cloudflare\public-api
try {
    $NEW_SERVICE_URL | npx wrangler secret put FALLBACK_BACKEND_ORIGIN
} finally {
    Pop-Location
}
```

Expected: `Success! Uploaded secret FALLBACK_BACKEND_ORIGIN`

- [ ] **Step 2: Deploy public-api Worker**

Run:
```powershell
Push-Location deployment\cloudflare\public-api
try {
    npx wrangler deploy
} finally {
    Pop-Location
}
```

Expected: `Deployed pikar-public-api triggers (X.XX sec)` followed by `https://public-api.pikar-ai.com`.

---

## Task 19: Post-cutover verification

**Why:** Confirm `api.pikar-ai.com` traffic is actually landing on the new project's Cloud Run logs.

**Files:** None.

- [ ] **Step 1: Hit api.pikar-ai.com/health/live**

Run:
```powershell
$r = Invoke-WebRequest -Uri "https://api.pikar-ai.com/health/live" -Method GET -TimeoutSec 30 -UseBasicParsing
if ($r.StatusCode -ne 200) { throw "api.pikar-ai.com health/live returned $($r.StatusCode)" }
"PASS api.pikar-ai.com/health/live ($($r.StatusCode))"
```

Expected: `PASS api.pikar-ai.com/health/live (200)`

- [ ] **Step 2: Confirm the new project's Cloud Run logs show the request**

Run:
```powershell
Start-Sleep -Seconds 5  # give logs a moment to propagate
gcloud run services logs read pikar-ai --project=project-c3a75795-f866-4b37-8ec --region=us-central1 --limit=10 --format="value(timestamp,textPayload)" | Select-Object -First 5
```

Expected: at least one log line with a recent timestamp containing `GET /health/live` or similar request signature.

If no recent logs in new project — Cloudflare is still routing to the old backend, possibly due to cache. Force-bust:
```powershell
$r = Invoke-WebRequest -Uri "https://api.pikar-ai.com/health/live?bust=$(Get-Random)" -Headers @{"Cache-Control"="no-cache"}
```

---

## Task 20: Create 5 Cloud Scheduler jobs

**Why:** Recreate the scheduled triggers that hit `/scheduled/*` and `/admin/*/...` endpoints. They need the new Cloud Run URL.

**Files:** None.

- [ ] **Step 1: Get SCHEDULER_SECRET value (lives in `.env` and now in Secret Manager)**

Run:
```powershell
$envValues = @{}
foreach ($line in Get-Content .env) {
    if ($line -match '^([A-Z_]+)=(.*)$') { $envValues[$matches[1]] = $matches[2] }
}
$SCHEDULER_SECRET = $envValues['SCHEDULER_SECRET']
if (-not $SCHEDULER_SECRET) { throw "SCHEDULER_SECRET missing in .env" }
$NEW_SERVICE_URL = (Select-String -Path secrets\migration-checkpoint.txt -Pattern '^NEW_SERVICE_URL: ' | Select-Object -First 1).Line -replace '^NEW_SERVICE_URL: ', ''
"Will use: NEW_SERVICE_URL=$NEW_SERVICE_URL, SCHEDULER_SECRET length=$($SCHEDULER_SECRET.Length)"
```

Expected: `Will use: NEW_SERVICE_URL=https://... SCHEDULER_SECRET length=<N>`

- [ ] **Step 2: Create the 5 jobs**

Run:
```powershell
$jobs = @(
  @{ Name='pikar-ai-daily-report';                  Schedule='0 7 * * *';   Path='/scheduled/daily-report' },
  @{ Name='pikar-ai-weekly-digest';                 Schedule='0 9 * * 1';   Path='/scheduled/weekly-digest' },
  @{ Name='pikar-ai-admin-observability-rollup';    Schedule='0 * * * *';   Path='/admin/observability/run-rollup' },
  @{ Name='pikar-ai-admin-monitoring-check';        Schedule='* * * * *';   Path='/admin/monitoring/run-check' },
  @{ Name='pikar-ai-admin-analytics-aggregate';     Schedule='30 6 * * *';  Path='/admin/analytics/aggregate' }
)

foreach ($job in $jobs) {
  gcloud scheduler jobs create http $job.Name `
    --project=project-c3a75795-f866-4b37-8ec `
    --location=us-central1 `
    --schedule=$job.Schedule `
    --uri="$NEW_SERVICE_URL$($job.Path)" `
    --http-method=POST `
    --headers="X-Scheduler-Secret=$SCHEDULER_SECRET" `
    --time-zone=UTC `
    --max-retry-attempts=3 `
    --quiet | Out-Null
  "  created $($job.Name) — $($job.Schedule) -> $($job.Path)"
}
"5 scheduler jobs created."
```

Expected: 5 `  created` lines, then `5 scheduler jobs created.`

- [ ] **Step 3: Manually fire each job once and confirm 2xx**

Run:
```powershell
foreach ($job in $jobs) {
  $result = gcloud scheduler jobs run $job.Name --project=project-c3a75795-f866-4b37-8ec --location=us-central1 2>&1
  Start-Sleep -Seconds 3
  $lastRun = (gcloud scheduler jobs describe $job.Name --project=project-c3a75795-f866-4b37-8ec --location=us-central1 --format="value(lastAttemptTime,status.code)").Trim()
  "  $($job.Name): lastAttempt=$lastRun"
}
```

Expected: each line shows a recent `lastAttempt` time. If `status.code` is non-empty and not `0`, that job's first run failed — check logs:
```powershell
gcloud run services logs read pikar-ai --project=project-c3a75795-f866-4b37-8ec --region=us-central1 --limit=50 --filter="textPayload:scheduled OR textPayload:scheduler"
```

---

## Task 21: Mirror old image into new Artifact Registry

**Why:** Phase J.5 of the spec. Pre-rollback insurance: even if the old project's billing stays disabled forever, we'll have the last-known-good image (`sha256:0eecac59...`) deployable in the new project.

**Files:** None.

- [ ] **Step 1: Verify gcloud user auth (not the SA — we need IAM on the OLD project too)**

Run:
```powershell
$activeAccount = (gcloud auth list --filter="status:ACTIVE" --format="value(account)").Trim()
# We want the human user account that has IAM on pikar-ai-project.
# The new SA does NOT have IAM there — switch back to the original account.
$humanAccount = (gcloud auth list --format="value(account)") -split "`n" | Where-Object { $_ -match '@gmail\.com$' -or $_ -match '@pikar-ai\.com$' } | Select-Object -First 1
gcloud config set account $humanAccount
"Switched to human account: $humanAccount"
```

Expected: `Switched to human account: <user>@gmail.com` (or similar).

- [ ] **Step 2: Attempt to pull the old image. If it fails with BILLING_DISABLED, prompt user to temporarily re-enable old project billing**

Run:
```powershell
$OLD_IMAGE = "us-central1-docker.pkg.dev/pikar-ai-project/cloud-run-source-deploy/pikar-ai@sha256:0eecac59a74d5e24b09fe8107185466f4348084e4fa433135d268a2fe3b14d69"
docker pull $OLD_IMAGE 2>&1 | Tee-Object -Variable pullOutput
if ($LASTEXITCODE -ne 0) {
  if ($pullOutput -match 'denied|unauthorized|BILLING_DISABLED|billing') {
    Write-Warning "Old AR pull failed (likely billing-gated). Options:"
    Write-Warning "  A) Temporarily re-enable billing on pikar-ai-project, then re-run this task."
    Write-Warning "  B) Skip Phase J.5 entirely (rollback Path 1 stays available only if old billing comes back)."
    throw "STOP. Choose A or B and re-invoke."
  } else {
    throw "Unexpected docker pull failure: $pullOutput"
  }
}
"Old image pulled."
```

Expected: a Docker pull progress block, then `Old image pulled.`

If the throw fires with the billing message, ask the user which option (A or B). If A, the user must enable billing in GCP Console (link: https://console.developers.google.com/billing/enable?project=pikar-ai-project), then re-run this step. If B, skip the rest of Task 21 and proceed to Task 22.

- [ ] **Step 3: Re-tag for the new project's AR**

Run:
```powershell
$ROLLBACK_TAG = "us-central1-docker.pkg.dev/project-c3a75795-f866-4b37-8ec/cloud-run-source-deploy/pikar-ai:rollback-pre-cutover-0eecac59"
docker tag $OLD_IMAGE $ROLLBACK_TAG
"Tagged as: $ROLLBACK_TAG"
```

Expected: `Tagged as: us-central1-docker.pkg.dev/project-c3a75795-f866-4b37-8ec/cloud-run-source-deploy/pikar-ai:rollback-pre-cutover-0eecac59`

- [ ] **Step 4: Push to new AR**

Run:
```powershell
docker push $ROLLBACK_TAG
"Pushed."
```

Expected: docker push progress lines, then `Pushed.`

- [ ] **Step 5: Verify the rollback image is in new AR with the same digest**

Run:
```powershell
$desc = gcloud artifacts docker images describe $ROLLBACK_TAG --format=json | ConvertFrom-Json
if ($desc.image_summary.digest -notmatch '0eecac59a74d5e24b09fe8107185466f4348084e4fa433135d268a2fe3b14d69') {
  throw "Mirrored image digest does not match expected old digest: got $($desc.image_summary.digest)"
}
"Rollback image verified: $($desc.image_summary.fully_qualified_digest)"
```

Expected: `Rollback image verified: ...sha256:0eecac59...`

- [ ] **Step 6: If billing was temporarily re-enabled on old project, prompt user to re-disable**

If the user re-enabled billing for Step 2:
> "Please re-disable billing on `pikar-ai-project` now via the GCP Console (https://console.cloud.google.com/billing/projects). The mirror is complete and we no longer need any access to the old project until rollback."

Wait for user confirmation before continuing.

- [ ] **Step 7: Switch back to the SA configuration for the remaining tasks**

Run:
```powershell
gcloud config configurations activate pikar-ai-c3a75
$activeProject = (gcloud config get-value project).Trim()
if ($activeProject -ne "project-c3a75795-f866-4b37-8ec") { throw "Failed to switch back to new project config" }
"Back to new project config."
```

Expected: `Back to new project config.`

---

## Task 22: Decommission old Cloud Run service

**Why:** Phase J of the spec. User wants immediate scale-to-zero per decision D4. Old service stays defined (revision history, env config preserved) but has zero running instances.

**Files:** None.

- [ ] **Step 1: Scale old service to zero**

Run:
```powershell
# Use the human user account for old project ops (new SA has no IAM there)
$humanAccount = (gcloud auth list --format="value(account)") -split "`n" | Where-Object { $_ -match '@gmail\.com$' -or $_ -match '@pikar-ai\.com$' } | Select-Object -First 1
gcloud config configurations activate default 2>&1 | Out-Null  # back to original config
gcloud config set account $humanAccount

gcloud run services update pikar-ai `
  --project=pikar-ai-project `
  --region=us-central1 `
  --min-instances=0 `
  --max-instances=0 `
  --quiet
```

Expected: `Service [pikar-ai] revision [...] has been deployed.`

If this fails with `BILLING_DISABLED`, the operation cannot complete. That's actually fine — billing being off effectively scales it to 0 already (Cloud Run can't run without billing). Move on.

- [ ] **Step 2: Verify old service is at 0/0**

Run:
```powershell
$old = gcloud run services describe pikar-ai --project=pikar-ai-project --region=us-central1 --format="value(spec.template.metadata.annotations.'autoscaling.knative.dev/minScale',spec.template.metadata.annotations.'autoscaling.knative.dev/maxScale')" 2>&1
"Old service scaling: $old (expected: 0 0 or unable due to billing)"
```

Expected: `Old service scaling: 0	0` (tab-separated) OR a billing error (acceptable).

- [ ] **Step 3: Restore the original gcloud configuration**

Run:
```powershell
$savedConfig = (Select-String -Path secrets\migration-checkpoint.txt -Pattern '^Original active config: ' | Select-Object -First 1).Line -replace '^Original active config: ', ''
gcloud config configurations activate $savedConfig
"Restored gcloud config to: $savedConfig"
```

Expected: `Restored gcloud config to: default`

---

## Task 23: Final verification and cleanup

**Why:** Confirm the migration succeeded end-to-end and the workspace is back to a known-clean state.

**Files:** None.

- [ ] **Step 1: Production URL final smoke**

Run:
```powershell
$paths = @('/health/live','/health/connections','/health/cache','/health/embeddings','/a2a/app/.well-known/agent-card.json')
foreach ($p in $paths) {
  try {
    $r = Invoke-WebRequest -Uri "https://api.pikar-ai.com$p" -Method GET -TimeoutSec 20 -UseBasicParsing
    "  PASS $p ($($r.StatusCode))"
  } catch {
    "  FAIL $p ($($_.Exception.Message))"
  }
}
```

Expected: 5 `PASS` lines, all with `(200)`.

- [ ] **Step 2: Run the audit one more time for confirmation**

Run:
```powershell
pwsh scripts\migration\audit-secrets-gap.ps1 -RemoteCheck | Select-Object -Last 20
```

Expected: 16 `OK` lines in the remote-check section.

- [ ] **Step 3: Save checkpoint summary to docs/superpowers/runbooks/**

Create a one-shot summary at `docs/superpowers/runbooks/2026-05-19-cloud-run-migration-result.md` with:
- New project URL
- New revision name
- Rollback image tag
- Timestamps

Run:
```powershell
$now = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
$NEW_SERVICE_URL = (Select-String -Path secrets\migration-checkpoint.txt -Pattern '^NEW_SERVICE_URL: ' | Select-Object -First 1).Line -replace '^NEW_SERVICE_URL: ', ''
$NEW_REVISION = (Select-String -Path secrets\migration-checkpoint.txt -Pattern '^NEW_REVISION: ' | Select-Object -First 1).Line -replace '^NEW_REVISION: ', ''
$summary = @"
# Cloud Run migration result — $now

- New service URL: $NEW_SERVICE_URL
- New revision: $NEW_REVISION
- Rollback image (in new AR): us-central1-docker.pkg.dev/project-c3a75795-f866-4b37-8ec/cloud-run-source-deploy/pikar-ai:rollback-pre-cutover-0eecac59
- Old project state: pikar-ai-project, Cloud Run scaled to 0/0 (or billing-disabled equivalent)
- Cloudflare workers: pikar-edge-api + pikar-public-api both re-deployed pointing at new origin
"@
New-Item -ItemType Directory -Path docs\superpowers\runbooks -Force | Out-Null
$summary | Set-Content -Path "docs\superpowers\runbooks\2026-05-19-cloud-run-migration-result.md"
"Summary written."
```

Expected: `Summary written.`

- [ ] **Step 4: Delete the secrets\migration-checkpoint.txt (contains transient values, not secrets but unnecessary now)**

Run:
```powershell
Remove-Item secrets\migration-checkpoint.txt -Force
"Checkpoint file removed."
```

- [ ] **Step 5: Commit the result summary**

```powershell
git add docs/superpowers/runbooks/2026-05-19-cloud-run-migration-result.md
git commit -m "docs(infra): record Cloud Run new-project migration result"
```

---

## Rollback procedures (reference only — do not run unless something broke)

If, within 24-48 hours of Task 19, the new project misbehaves:

### Rollback Path 1 — Cloudflare revert (preferred, ~2 min)

```powershell
$OLD_URL = "https://pikar-ai-917671810739.us-central1.run.app"

Push-Location deployment\cloudflare\edge-api
$OLD_URL | npx wrangler secret put AGENT_BACKEND_ORIGIN
npx wrangler deploy
Pop-Location

Push-Location deployment\cloudflare\public-api
$OLD_URL | npx wrangler secret put FALLBACK_BACKEND_ORIGIN
npx wrangler deploy
Pop-Location

# Wake old Cloud Run (requires billing on old project — may fail if billing stayed off)
gcloud run services update pikar-ai `
  --project=pikar-ai-project --region=us-central1 `
  --min-instances=2 --max-instances=10
```

### Rollback Path 2 — Redeploy mirrored image in new project (if old AR is unreachable)

```powershell
gcloud beta run deploy pikar-ai `
  --image=us-central1-docker.pkg.dev/project-c3a75795-f866-4b37-8ec/cloud-run-source-deploy/pikar-ai:rollback-pre-cutover-0eecac59 `
  --project=project-c3a75795-f866-4b37-8ec `
  --region=us-central1 `
  --no-traffic

# Smoke at the new revision URL, then:
gcloud run services update-traffic pikar-ai --to-latest --project=project-c3a75795-f866-4b37-8ec
```

### Rollback Path 3 — Fix forward (worst case)

If Paths 1 and 2 are unavailable: the new project is now the production substrate. Investigate the failure and patch on the new project. The spec's Phase G smoke window is what makes this acceptable as the worst-case outcome — by Task 17 we had high confidence the new project was healthy.

---

## Acceptance criteria (mirror of spec section 9)

- [ ] A1: gcloud authenticated as `pikar-ai@project-c3a75795-f866-4b37-8ec.iam.gserviceaccount.com` — Task 2
- [ ] A2: all 14 APIs enabled — Task 3
- [ ] A3: app SA has all 7 parity roles — Task 4
- [ ] A4: Vertex AI Gemini 2.5 family reachable — Task 5
- [ ] B1: VPC connector READY — Task 6
- [ ] B2: Memorystore READY, BASIC, 1GB — Task 7
- [ ] C1: Image pushed to new AR — Task 10
- [ ] D1: 16 SM secrets created — Task 12
- [ ] D2: All 16 have non-empty `latest` version — Task 13
- [ ] D3: App SA has secretAccessor — Task 12
- [ ] D4: `ADMIN_ENCRYPTION_KEY` hash matches `.env` — Task 13
- [ ] E1: Logs bucket exists — Task 14
- [ ] F1: Cloud Run revision READY at 0% — Task 15
- [ ] G1: 5 smoke checks pass on direct revision URL — Task 16
- [ ] G2: Traffic promoted to 100% — Task 16
- [ ] H1: `wrangler secret put` succeeded on both Workers — Tasks 17, 18
- [ ] H2: `npx wrangler deploy` succeeded on both Workers — Tasks 17, 18
- [ ] H3: `curl https://api.pikar-ai.com/health/live` returns 200 within 60s — Task 19
- [ ] H4: New project Cloud Run logs show inbound traffic — Task 19
- [ ] I1: 5 Cloud Scheduler jobs created and enabled — Task 20
- [ ] I2: Each job's first manual run returns 2xx — Task 20
- [ ] J5a: `rollback-pre-cutover-0eecac59` tag exists in new AR — Task 21
- [ ] J5b: Mirror digest matches `sha256:0eecac59...` — Task 21
- [ ] J5c: Old project billing restored to initial state — Task 21
- [ ] J1: Old Cloud Run min=max=0 — Task 22
