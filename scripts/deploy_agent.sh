#!/usr/bin/env bash
# Deploy Patient Triage Agent to Vertex AI Agent Runtime using ADK CLI
set -e

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-eliwilner-111881}"
LOCATION="${GOOGLE_CLOUD_LOCATION:-us-east1}"

echo "=================================================="
echo "🚀 Deploying Patient Triage Agent via ADK CLI"
echo "• Project:  ${PROJECT_ID}"
echo "• Location: ${LOCATION}"
echo "=================================================="

ADK_BIN="adk"
if [ -f "/Users/eliwilner/google/onboarding/.venv/bin/adk" ]; then
    ADK_BIN="/Users/eliwilner/google/onboarding/.venv/bin/adk"
elif [ -f ".venv/bin/adk" ]; then
    ADK_BIN=".venv/bin/adk"
fi

$ADK_BIN deploy agent_engine patient-triage-agent \
  --project="${PROJECT_ID}" \
  --region="${LOCATION}" \
  --display_name="patient_triage_agent" \
  --description="Ambient Patient Triage Agent with ADK Workflow"

echo "=================================================="
echo "✅ Patient Triage Agent Deployment Complete!"
echo "=================================================="

