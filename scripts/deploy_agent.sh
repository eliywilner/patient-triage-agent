#!/usr/bin/env bash
# Deploy Patient Triage Agent to Vertex AI Agent Runtime using ADK CLI
set -e

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
LOCATION="${GOOGLE_CLOUD_LOCATION:-us-east1}"

if [ -z "$PROJECT_ID" ]; then
  echo "Error: GOOGLE_CLOUD_PROJECT environment variable is not set and no active gcloud project found."
  echo "Please run: export GOOGLE_CLOUD_PROJECT='your-project-id'"
  exit 1
fi

echo "=================================================="
echo "🚀 Deploying Patient Triage Agent via ADK CLI"
echo "• Project:  ${PROJECT_ID}"
echo "• Location: ${LOCATION}"
echo "=================================================="

# Dynamically locate the adk CLI binary
ADK_BIN="adk"
if command -v adk &> /dev/null; then
    ADK_BIN="adk"
elif [ -f ".venv/bin/adk" ]; then
    ADK_BIN=".venv/bin/adk"
elif [ -f "../.venv/bin/adk" ]; then
    ADK_BIN="../.venv/bin/adk"
else
    echo "Error: 'adk' command line tool not found in PATH or .venv."
    echo "Please install ADK with: pip install google-adk"
    exit 1
fi

$ADK_BIN deploy agent_engine patient-triage-agent \
  --project="${PROJECT_ID}" \
  --region="${LOCATION}" \
  --display_name="patient_triage_agent" \
  --description="Ambient Patient Triage Agent with ADK Workflow"

echo "=================================================="
echo "✅ Patient Triage Agent Deployment Complete!"
echo "=================================================="
