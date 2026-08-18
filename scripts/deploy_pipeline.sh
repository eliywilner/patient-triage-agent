#!/usr/bin/env bash
# Deploy Pub/Sub Event Pipeline for Patient Triage Agent
set -e

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
LOCATION="${GOOGLE_CLOUD_LOCATION:-us-east1}"
AGENT_RUNTIME_ID="${1:-}"

if [ -z "$PROJECT_ID" ]; then
  echo "Error: GOOGLE_CLOUD_PROJECT environment variable is not set and no active gcloud project found."
  echo "Please run: export GOOGLE_CLOUD_PROJECT='your-project-id'"
  exit 1
fi

if [ -z "$AGENT_RUNTIME_ID" ]; then
  if [ -f "patient-triage-agent/deployment_metadata.json" ]; then
    AGENT_RUNTIME_ID=$(python3 -c "import json; print(json.load(open('patient-triage-agent/deployment_metadata.json'))['remote_agent_runtime_id'])")
  fi
fi

if [ -z "$AGENT_RUNTIME_ID" ]; then
  echo "Error: AGENT_RUNTIME_ID not provided and deployment_metadata.json not found."
  echo "Usage: ./scripts/deploy_pipeline.sh <AGENT_RUNTIME_ID>"
  exit 1
fi

echo "=================================================="
echo "📡 Configuring Pub/Sub Event Pipeline"
echo "• Project:          ${PROJECT_ID}"
echo "• Location:         ${LOCATION}"
echo "• Agent Runtime ID: ${AGENT_RUNTIME_ID}"
echo "=================================================="

# 1. Create Topics
gcloud pubsub topics create patient-triage-reports --project="${PROJECT_ID}" || true
gcloud pubsub topics create patient-triage-dead-letter --project="${PROJECT_ID}" || true

# 2. Create Service Account
SA_NAME="triage-pubsub-invoker"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud iam service-accounts create "${SA_NAME}" \
  --display-name="Patient Triage PubSub Invoker SA" \
  --project="${PROJECT_ID}" || true

# 3. IAM Bindings
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/aiplatform.user"

PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")
PUBSUB_SA="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"

gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
  --member="serviceAccount:${PUBSUB_SA}" \
  --role="roles/iam.serviceAccountTokenCreator" \
  --project="${PROJECT_ID}"

gcloud pubsub topics add-iam-policy-binding patient-triage-dead-letter \
  --member="serviceAccount:${PUBSUB_SA}" \
  --role="roles/pubsub.publisher" \
  --project="${PROJECT_ID}"

# 4. Create Push Subscription
TARGET_ENDPOINT="https://${LOCATION}-aiplatform.googleapis.com/v1/${AGENT_RUNTIME_ID}:query"

gcloud pubsub subscriptions create patient-triage-push \
  --topic=patient-triage-reports \
  --push-endpoint="${TARGET_ENDPOINT}" \
  --push-auth-service-account="${SA_EMAIL}" \
  --push-no-wrapper \
  --ack-deadline=600 \
  --dead-letter-topic="projects/${PROJECT_ID}/topics/patient-triage-dead-letter" \
  --max-delivery-attempts=5 \
  --project="${PROJECT_ID}" || true

gcloud pubsub subscriptions add-iam-policy-binding patient-triage-push \
  --member="serviceAccount:${PUBSUB_SA}" \
  --role="roles/pubsub.subscriber" \
  --project="${PROJECT_ID}"

echo "=================================================="
echo "✅ Pub/Sub Event Pipeline Fully Configured!"
echo "=================================================="
