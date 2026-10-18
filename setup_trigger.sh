#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Script: setup_trigger.sh
# Purpose: Finalize Developer Connect repository linking and Cloud Build trigger
# ==============================================================================

PROJECT_ID="${1:-formula-e-drive}"
REGION="${2:-europe-west2}"
CONNECTION_NAME="${3:-fe-github-conn}"
REPO_NAME="${4:-fe-driver-performance}"
GITHUB_REPO_URL="${5:-}"

if [[ -z "$GITHUB_REPO_URL" ]]; then
    echo "Usage: $0 [PROJECT_ID] [REGION] [CONNECTION_NAME] [REPO_NAME] <GITHUB_REPO_URL>"
    echo "Example: $0 formula-e-drive europe-west2 fe-github-conn fe-driver-performance https://github.com/myuser/fe-driver-performance.git"
    exit 1
fi

echo "==> Verifying Developer Connect connection state..."
STATE=$(gcloud developer-connect connections describe "$CONNECTION_NAME" \
    --project="$PROJECT_ID" \
    --location="$REGION" \
    --format="value(installationState.stage)")

echo "Current connection state: $STATE"

if [[ "$STATE" != "COMPLETE" ]]; then
    echo "ERROR: Developer Connect connection '$CONNECTION_NAME' is not COMPLETE (current: $STATE)."
    echo "Please visit the authorization link in your browser to complete GitHub authorization."
    exit 1
fi

echo "==> Creating Developer Connect git repository link '$REPO_NAME'..."
gcloud developer-connect connections git-repository-links create "$REPO_NAME" \
    --project="$PROJECT_ID" \
    --location="$REGION" \
    --connection="$CONNECTION_NAME" \
    --clone-uri="$GITHUB_REPO_URL" \
    --quiet || echo "Repository link may already exist."

REPO_RESOURCE="projects/$PROJECT_ID/locations/$REGION/connections/$CONNECTION_NAME/gitRepositoryLinks/$REPO_NAME"
PROJECT_NUM=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
SERVICE_ACCOUNT="projects/$PROJECT_ID/serviceAccounts/${PROJECT_NUM}-compute@developer.gserviceaccount.com"

echo "==> Creating Cloud Build push trigger 'fe-driver-performance-push'..."
gcloud beta builds triggers create developer-connect \
    --project="$PROJECT_ID" \
    --name="fe-driver-performance-push" \
    --region="$REGION" \
    --git-repository-link="$REPO_RESOURCE" \
    --branch-pattern="^main$" \
    --build-config="cloudbuild.yaml" \
    --service-account="$SERVICE_ACCOUNT" \
    --description="Continuous Integration & Deployment trigger for Formula E Driver Performance on push to main" \
    --quiet || echo "Trigger may already exist."

echo "==> Trigger successfully configured!"
gcloud builds triggers describe "fe-driver-performance-push" --region="$REGION" --project="$PROJECT_ID"
