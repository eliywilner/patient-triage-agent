#!/usr/bin/env bash
# Deploy Doctor Triage Portal to Cloud Run
set -e

export PATH="$PATH:/Users/eliwilner/google-cloud-sdk/bin:/opt/homebrew/bin:/usr/local/bin"

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-eliwilner-111881}"
LOCATION="${GOOGLE_CLOUD_LOCATION:-us-east1}"
AGENT_RUNTIME_ID="${1:-}"

if [ -z "$AGENT_RUNTIME_ID" ]; then
  if [ -f "patient-triage-agent/deployment_metadata.json" ]; then
    AGENT_RUNTIME_ID=$(python3 -c "import json; print(json.load(open('patient-triage-agent/deployment_metadata.json'))['remote_agent_runtime_id'])")
  fi
fi

echo "=================================================="
echo "🏥 Deploying Doctor Triage Portal to Cloud Run"
echo "• Project:          ${PROJECT_ID}"
echo "• Location:         ${LOCATION}"
echo "• Agent Runtime ID: ${AGENT_RUNTIME_ID}"
echo "=================================================="

gcloud artifacts repositories create cloud-run-source-deploy \
  --repository-format=docker \
  --location="${LOCATION}" \
  --project="${PROJECT_ID}" || true

IMAGE_TAG="${LOCATION}-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/patient-triage-dashboard:latest"

gcloud builds submit --tag "${IMAGE_TAG}" clinical_frontend --project="${PROJECT_ID}" --region="${LOCATION}"

gcloud run deploy patient-triage-dashboard \
  --image="${IMAGE_TAG}" \
  --region="${LOCATION}" \
  --project="${PROJECT_ID}" \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT="${PROJECT_ID}",AGENT_RUNTIME_ID="${AGENT_RUNTIME_ID}",GOOGLE_CLOUD_LOCATION="${LOCATION}"

PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${COMPUTE_SA}" \
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${COMPUTE_SA}" \
  --role="roles/serviceusage.serviceUsageConsumer"

DASHBOARD_URL=$(gcloud run services describe patient-triage-dashboard --region="${LOCATION}" --project="${PROJECT_ID}" --format="value(status.url)")

echo "=================================================="
echo "✅ Doctor Triage Portal Live at: ${DASHBOARD_URL}"
echo "=================================================="
