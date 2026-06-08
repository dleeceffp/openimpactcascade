# Google Cloud Platform Deployment Guide
*Updated May 2026*

This guide walks you through deploying the OpenImpactCascade (OIC) application to Google Cloud Run, utilizing standard GCP services and securely handling secrets via Google Secret Manager.

## Architectural Overview
- **Compute**: Google Cloud Run (Fully managed, scalable container platform)
- **Container Registry**: Google Artifact Registry
- **Secrets Management**: Google Secret Manager (No API keys are passed in plain environment variables)
- **Data & Storage**: Google Cloud Storage (GCS) and Vertex AI RAG Corpus
- **IAM**: Dedicated Service Account tailored using least privilege principles.

## Prerequisites
- A Google Cloud Project where you have **Owner** privileges.
- Standard `gcloud` CLI tools installed locally (or via Cloud Shell).
- Docker installed locally (if building locally instead of Cloud Build).

## 1. Using the Automated Deployment Script

We have consolidated the deployment into a single, comprehensive script that will set up the entire infrastructure.

```bash
cd deployment/gcp
chmod +x deploy_infrastructure.sh

# Usage: ./deploy_infrastructure.sh <PROJECT_ID> [REGION] [APP_NAME]
./deploy_infrastructure.sh my-gcp-project-id us-central1 openimpactcascade
```

### What the Script Does:
1. **Enables APIs**: Cloud Run, Compute, Vertex AI, Secret Manager, Storage, IAM, Artifact Registry, API Keys, and Generative Language (Gemini API).
2. **Creates a Service Account**: e.g., `openimpactcascade-cr-sa@<project-id>.iam.gserviceaccount.com`.
3. **Grants Roles**: Assigns `roles/aiplatform.user`, `roles/storage.objectAdmin`, and `roles/logging.logWriter` to the Service Account.
4. **Provisions Storage**: Creates a dedicated GCS bucket for your application's data.
5. **Generates Gemini API Key**: Programmatically generates an API key explicitly scoped to the `generativelanguage.googleapis.com` service inside the project. The raw key is automatically placed inside Google Secret Manager under `GEMINI_API_KEY`.
6. **Configures Additional Secrets**: Prompts you for sensitive variables (`ANTHROPIC_API_KEY`, `SECRET_KEY`, `GOOGLE_SEARCH_API_KEY`, `GOOGLE_SEARCH_CSE_ID`) and securely writes them to Google Secret Manager, granting the Service Account `roles/secretmanager.secretAccessor`.
7. **Artifact Registry**: Creates a Docker repository, builds the image from the root of the project using Cloud Build, and pushes it.
8. **Deploys to Cloud Run**: Deploys the container, mapping the environment variables securely to Secret Manager and standard configurations to plain env variables.

## 2. Managing Vertex AI RAG

If you are using Vertex AI RAG functionality, the deployment script will prompt you for a `VERTEX_RAG_CORPUS`. You can create or manage your RAG corpus using the Vertex AI API natively or through standard Vertex AI Cloud Console interfaces available.

## 3. Local Evaluation Note

**Warning:** Do not hardcode API keys or production secrets in local run scripts (e.g., `local_docker_eval`). For local development, utilize `.env` files that are `.gitignore`d or securely load them into your shell session temporarily. 

To run the Docker container locally using Google Application Default Credentials:

```bash
gcloud auth application-default login

docker run -p 8080:8080 \
    -e ANTHROPIC_API_KEY="your-local-key" \
    -e SECRET_KEY="local-secret" \
    -e GOOGLE_CLOUD_PROJECT="my-gcp-project-id" \
    -e GCS_BUCKET_NAME="openimpactcascade-appdata-my-gcp-project-id" \
    -e VERTEX_AI_LOCATION="us-central1" \
    -e VERTEX_RAG_CORPUS="<your-corpus-id>" \
    -v ~/.config/gcloud/application_default_credentials.json:/app/sa.json:ro \
    -e GOOGLE_APPLICATION_CREDENTIALS="/app/sa.json" \
    openimpactcascade:latest
```

## Troubleshooting
- **Permission Errors**: Verify that your terminal session is authenticated (`gcloud auth login`) and that you have Owner/Editor rights on the GCP project.
- **Missing Secrets**: Ensure that the Cloud Run service account has `roles/secretmanager.secretAccessor` on the created secrets. This is handled automatically by the deployment script.
