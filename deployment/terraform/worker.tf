# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

# Background worker for ai_jobs, workflow steps, scheduled reports, webhook
# deliveries, and long-task media renders. It runs as a short Cloud Run Job
# every minute so Cloud Run does not need an always-listening worker service.

resource "google_cloud_run_v2_job" "worker" {
  for_each = local.deploy_project_ids

  name                = "${var.project_name}-worker"
  location            = var.region
  project             = each.value
  deletion_protection = false
  labels = {
    "created-by" = "adk"
    "component"  = "worker"
  }

  template {
    parallelism = 1
    task_count  = 1

    template {
      service_account = google_service_account.app_sa[each.key].email
      timeout         = "900s"
      max_retries     = 1

      containers {
        # Placeholder, replaced by CI/CD or one-off deployment. Use the full
        # application image, not Dockerfile.worker, so Remotion/Node/LibreOffice
        # are available for background video renders.
        image   = "us-docker.pkg.dev/cloudrun/container/hello"
        command = ["uv"]
        args    = ["run", "python", "-m", "app.workflows.worker"]

        env {
          name  = "ENVIRONMENT"
          value = each.key == "prod" ? "production" : "staging"
        }
        env {
          name  = "SUPABASE_URL"
          value = var.supabase_url
        }
        env {
          name  = "SUPABASE_ANON_KEY"
          value = var.supabase_anon_key
        }
        env {
          name  = "GOOGLE_CLOUD_PROJECT"
          value = each.value
        }
        env {
          name  = "GOOGLE_CLOUD_LOCATION"
          value = var.region
        }
        env {
          name  = "GOOGLE_GENAI_USE_VERTEXAI"
          value = "1"
        }
        env {
          name  = "REMOTION_RENDER_ENABLED"
          value = "1"
        }
        env {
          name  = "REMOTION_RENDER_DIR"
          value = "/code/remotion-render"
        }

        dynamic "env" {
          for_each = local.worker_runtime_plain_env_values
          content {
            name  = env.key
            value = env.value
          }
        }
        dynamic "env" {
          for_each = local.runtime_secret_values
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = google_secret_manager_secret.runtime_secret["${each.key}:${env.key}"].secret_id
                version = "latest"
              }
            }
          }
        }

        resources {
          limits = {
            cpu    = "4"
            memory = "8Gi"
          }
        }
      }

      vpc_access {
        connector = google_vpc_access_connector.run_connector[each.key].id
        egress    = "PRIVATE_RANGES_ONLY"
      }
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].template[0].containers[0].image,
    ]
  }

  depends_on = [
    google_project_service.deploy_project_services,
  ]
}

resource "google_service_account_iam_member" "scheduler_worker_token_creator" {
  for_each = local.deploy_project_ids

  service_account_id = google_service_account.app_sa[each.key].name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.project[each.key].number}@gcp-sa-cloudscheduler.iam.gserviceaccount.com"

  depends_on = [
    google_project_service.deploy_project_services,
  ]
}

resource "google_cloud_scheduler_job" "worker_tick" {
  for_each = local.deploy_project_ids

  name        = "${var.project_name}-worker-tick"
  description = "Runs the Pikar AI background worker Cloud Run Job."
  project     = each.value
  region      = var.region
  schedule    = var.worker_schedule
  time_zone   = "Etc/UTC"

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${each.value}/jobs/${google_cloud_run_v2_job.worker[each.key].name}:run"

    oauth_token {
      service_account_email = google_service_account.app_sa[each.key].email
    }
  }

  retry_config {
    retry_count = 1
  }

  depends_on = [
    google_cloud_run_v2_job.worker,
    google_project_iam_member.app_sa_roles,
    google_service_account_iam_member.scheduler_worker_token_creator,
  ]
}
