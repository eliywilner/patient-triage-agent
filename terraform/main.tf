# Declarative Terraform Infrastructure-as-Code (IaC) for Patient Triage Agent
terraform {
  required_version = ">= 1.0.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Pub/Sub Topics
resource "google_pubsub_topic" "reports" {
  name    = "patient-triage-reports"
  project = var.project_id
}

resource "google_pubsub_topic" "dead_letter" {
  name    = "patient-triage-dead-letter"
  project = var.project_id
}

# 2. Service Account for OIDC Push Invocation
resource "google_service_account" "pubsub_invoker" {
  account_id   = "triage-pubsub-invoker"
  display_name = "Patient Triage PubSub OIDC Invoker Service Account"
  project      = var.project_id
}

# 3. IAM Bindings
resource "google_project_iam_member" "aiplatform_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.pubsub_invoker.email}"
}

# 4. Pub/Sub Push Subscription with Dead Letter Policy
resource "google_pubsub_subscription" "push_sub" {
  name    = "patient-triage-push"
  topic   = google_pubsub_topic.reports.name
  project = var.project_id

  ack_deadline_seconds = 600

  push_config {
    push_endpoint = "https://${var.region}-aiplatform.googleapis.com/v1/${var.agent_runtime_id}:query"
    
    no_wrapper {
      write_metadata = false
    }

    oidc_token {
      service_account_email = google_service_account.pubsub_invoker.email
    }
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = 5
  }
}

