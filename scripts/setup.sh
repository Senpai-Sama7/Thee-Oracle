#!/bin/bash
# Enable required APIs
gcloud services enable discoveryengine.googleapis.com
gcloud services enable dialogflow.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable vision.googleapis.com
gcloud services enable artifactregistry.googleapis.com

# Create Service Account
gcloud iam service-accounts create rag-sa --display-name="RAG Service Account"
# Add roles
# (Assuming project ID is set in gcloud config)
PROJECT_ID=$(gcloud config get-value project)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:rag-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/discoveryengine.editor"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:rag-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

echo "Setup complete."
