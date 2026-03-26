provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  type        = string
  description = "The GCP Project ID"
}

variable "region" {
  type        = string
  default     = "us-central1"
  description = "The GCP Region"
}

variable "rabbitmq_host" {
  type        = string
  default     = "localhost"
  description = "RabbitMQ host for email queuing"
}

variable "rabbitmq_queue" {
  type        = string
  default     = "task_queue"
  description = "RabbitMQ queue name for tasks"
}

variable "webhook_api_key" {
  type        = string
  sensitive   = true
  description = "API key for webhook authentication"
}

variable "allow_public_invoker" {
  type        = bool
  default     = false
  description = "Set true to allow unauthenticated public access to the webhook."
}

# Enable required APIs (Consolidated pool)
resource "google_project_service" "apis" {
  for_each = toset([
    "discoveryengine.googleapis.com",
    "dialogflow.googleapis.com",
    "aiplatform.googleapis.com",
    "run.googleapis.com",
    "vision.googleapis.com",
    "artifactregistry.googleapis.com"
  ])
  service            = each.key
  disable_on_destroy = false
}

# Artifact Registry for the webhook image
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = "omni-agent-repo"
  format        = "DOCKER"
  depends_on    = [google_project_service.apis]
}

# Cloud Run Service for the Webhook
resource "google_cloud_run_v2_service" "webhook" {
  name     = "omni-agent-webhook"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.name}/webhook:latest"
      
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
      }
      env {
        name  = "AGENT_DB_PATH"
        value = "/tmp/agent_state.db"
      }
      env {
        name  = "RABBITMQ_HOST"
        value = var.rabbitmq_host
      }
      env {
        name  = "RABBITMQ_QUEUE"
        value = var.rabbitmq_queue
      }
      env {
        name  = "WEBHOOK_API_KEY"
        value = var.webhook_api_key
      }
      
      ports {
        container_port = 8080
      }
    }
  }

  depends_on = [google_artifact_registry_repository.repo]
}

# IAM: Public access is opt-in. Keep the service private by default.
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  count    = var.allow_public_invoker ? 1 : 0
  name     = google_cloud_run_v2_service.webhook.name
  location = google_cloud_run_v2_service.webhook.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "webhook_url" {
  value = google_cloud_run_v2_service.webhook.uri
}
