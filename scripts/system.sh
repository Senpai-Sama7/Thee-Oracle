#!/bin/bash

# ==============================================================================
# ANTIGRAVITY & OMNI-AGENT INITIALIZATION SCRIPT
# TARGET OS: UBUNTU 25.10 | TARGET REGION: US-CENTRAL1
# ==============================================================================

set -e

echo "Checking System Architecture..."
OS_VERSION=$(lsb_release -rs)
KERNEL_VERSION=$(uname -r)

if [[ "$OS_VERSION" != "25.10" ]]; then
    echo "Warning: System is not Ubuntu 25.10. Proceeding with compatibility mode."
fi

# 1. VERIFY ANTIGRAVITY IDE ENVIRONMENT
echo "Verifying Antigravity IDE Sandbox Configuration..."
export ANTIGRAVITY_HOME="$HOME/.antigravity"
export ANTIGRAVITY_SANDBOX_ID="sandbox-$(date +%s)"

if command -v antigravity &> /dev/null; then
    echo "Antigravity IDE detected. Checking local inference engine..."
else
    echo "Antigravity IDE binary not found in PATH. Ensure it is installed via the March 2026 Preview channel."
fi

# 2. GCP AUTHENTICATION & PROJECT SELECTION
echo "Verifying GCP Cloud Identity..."
PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo "ERROR: No GCP Project ID set. Run 'gcloud config set project [YOUR_PROJECT_ID]' first."
    exit 1
fi

# 3. CONSOLIDATED API ENABLEMENT (CREDIT-TARGETED)
echo "Enabling Credit-Mapped APIs for Project: $PROJECT_ID..."
gcloud services enable \
  discoveryengine.googleapis.com \
  dialogflow.googleapis.com \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  run.googleapis.com \
  firestore.googleapis.com \
  cloudbuild.googleapis.com \
  vision.googleapis.com

# 4. DIRECTORY STRUCTURE FOR OMNI-AGENT
echo "Generating Omni-Agent Project Scaffold..."
mkdir -p ~/omni-agent/{backend,frontend,data,infrastructure}

cat <<EOF > ~/omni-agent/infrastructure/credit_map.json
{
  "pool_1000": ["discoveryengine.googleapis.com", "dialogflow.googleapis.com"],
  "pool_300": ["aiplatform.googleapis.com", "run.googleapis.com", "vision.googleapis.com"],
  "always_free": ["firestore.googleapis.com", "storage.googleapis.com"]
}
EOF

# 5. ANTIGRAVITY SANDBOX SYNC
cat <<EOF > ~/omni-agent/.antigravity.yaml
project_id: "$PROJECT_ID"
region: "us-central1"
sandbox:
  enabled: true
  runtime: "ubuntu-25.10-lts"
  hardware_acceleration: "amd-v"
EOF

echo "Initialization Complete. Omni-Agent scaffold ready at ~/omni-agent."
