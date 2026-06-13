# OpenImpactCascade — Deployment Guide

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Repository** | https://github.com/dleeceffp/openimpactcascade |
| **Default deployment target** | GCP Cloud Run |
| **Deploy script** | `deployment/gcp/deploy_infrastructure.sh` |

---

## Contents

1. [Developer Environment Setup](#1-developer-environment-setup)
2. [GCP Project Prerequisites](#2-gcp-project-prerequisites)
3. [Required GCP IAM Permissions](#3-required-gcp-iam-permissions)
4. [Secrets Reference](#4-secrets-reference)
5. [Deploying to GCP Cloud Run](#5-deploying-to-gcp-cloud-run)
6. [What the Script Does](#6-what-the-script-does)
7. [Cloud Run Service Configuration](#7-cloud-run-service-configuration)
8. [Running Locally with Docker](#8-running-locally-with-docker)
9. [Post-Deployment Verification](#9-post-deployment-verification)
10. [Updating an Existing Deployment](#10-updating-an-existing-deployment)

---

## 1. Developer Environment Setup

The deployment workflow assumes a Linux-like shell environment. On Windows, **Git Bash** (included with Git for Windows) works well. WSL2 is also fine. Native PowerShell is not covered.

### Required tools

**gcloud CLI**

Install the Google Cloud CLI from the official instructions for your OS:
https://cloud.google.com/sdk/docs/install

After installing, initialize and authenticate:

```bash
gcloud init
gcloud auth login
gcloud auth application-default login
```

Verify:

```bash
gcloud version
gcloud auth list
```

**Docker**

The deployment uses Cloud Build for the image build step — you do not need Docker installed locally to deploy to GCP. You do need it if you want to build and run the container locally (see [Section 8](#8-running-locally-with-docker)).

Install Docker Desktop (Windows/Mac) or the Docker engine (Linux):
https://docs.docker.com/get-docker/

Verify:

```bash
docker --version
```

**Git**

```bash
git --version
```

If you are on Windows and using Git Bash, Git is already present.

### Clone the repository

```bash
git clone https://github.com/dleeceffp/openimpactcascade.git
cd openimpactcascade
```

---

## 2. GCP Project Prerequisites

You need a GCP project with billing enabled before running the deploy script.

- Create a project at https://console.cloud.google.com/ or via `gcloud projects create <PROJECT_ID>`
- Enable billing on the project: https://console.cloud.google.com/billing
- Note the **Project ID** — this is passed as the first argument to the deploy script

The deploy script enables all required GCP APIs automatically. No manual API activation is needed.

---

## 3. Required GCP IAM Permissions

The deploy script is designed to run within a single GCP project. It does **not** require organization-level or folder-level access. The person running the script needs the following roles on the project:

### Deployer permissions (the human running the script)

Rather than using Project Owner or Project Editor (which grant broad access), grant the deployer these specific roles:

| Role | Why it is needed |
|------|-----------------|
| `roles/iam.serviceAccountAdmin` | Create and manage the Cloud Run service account |
| `roles/iam.serviceAccountUser` | Impersonate the service account during Cloud Run deploy |
| `roles/resourcemanager.projectIamAdmin` | Bind IAM roles to the service accounts created during setup |
| `roles/run.admin` | Deploy and manage Cloud Run services |
| `roles/artifactregistry.admin` | Create the Artifact Registry repository and manage images |
| `roles/cloudbuild.builds.editor` | Submit Cloud Build jobs |
| `roles/secretmanager.admin` | Create secrets and manage secret IAM bindings |
| `roles/storage.admin` | Create and manage the application data GCS bucket |
| `roles/serviceusage.serviceUsageAdmin` | Enable GCP APIs (`gcloud services enable`) |
| `roles/apikeys.admin` | Create the scoped Gemini API key |
| `roles/iam.serviceAccountKeyAdmin` | Only needed if using local ADC key; not required for Cloud Run |

To grant these to a deployer account (run as a project owner during initial setup):

```bash
PROJECT_ID="your-project-id"
DEPLOYER="user:yourname@example.com"  # or serviceAccount:...

ROLES=(
    "roles/iam.serviceAccountAdmin"
    "roles/iam.serviceAccountUser"
    "roles/resourcemanager.projectIamAdmin"
    "roles/run.admin"
    "roles/artifactregistry.admin"
    "roles/cloudbuild.builds.editor"
    "roles/secretmanager.admin"
    "roles/storage.admin"
    "roles/serviceusage.serviceUsageAdmin"
    "roles/apikeys.admin"
)

for ROLE in "${ROLES[@]}"; do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="$DEPLOYER" \
        --role="$ROLE" \
        --condition=None \
        --quiet
    echo "Granted $ROLE"
done
```

### Runtime service account permissions (set automatically by the script)

The script creates a dedicated Cloud Run service account (`<APP_NAME>-cr-sa@<PROJECT_ID>.iam.gserviceaccount.com`) and assigns it:

| Role | Purpose |
|------|---------|
| `roles/aiplatform.user` | Vertex AI access (retained for optional future RAG use) |
| `roles/storage.objectAdmin` | Read/write application data GCS bucket |
| `roles/logging.logWriter` | Write application logs to Cloud Logging |
| `roles/secretmanager.secretAccessor` | Read each Secret Manager secret at runtime (granted per-secret) |

### Cloud Build service account permissions (set automatically by the script)

Cloud Build uses the Compute Engine default service account (`<PROJECT_NUMBER>-compute@developer.gserviceaccount.com`). The script grants it:

| Role | Purpose |
|------|---------|
| `roles/storage.admin` | Read source archive and write build logs from/to GCS |
| `roles/artifactregistry.writer` | Push the built Docker image |
| `roles/logging.logWriter` | Write build logs |

---

## 4. Secrets Reference

All secrets are stored in **GCP Secret Manager**. The deploy script prompts for values interactively and creates each secret if it does not already exist. No secrets are passed as plain environment variables.

| Secret name | Required | Description |
|-------------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key for Claude. Obtain from https://console.anthropic.com |
| `SECRET_KEY` | Yes | Flask session secret key. Use a strong random string (e.g. `openssl rand -hex 32`) |
| `APP_USERNAME` | Yes | Login username for the web application |
| `APP_PASSWORD` | Yes | Login password for the web application |
| `GOOGLE_SEARCH_API_KEY` | No | Google Custom Search API key. Required for web-search threat intelligence gap-filling. If omitted, questionnaire generation falls back to corpus-only. |
| `GOOGLE_SEARCH_CSE_ID` | No | Google Custom Search Engine ID. Required alongside `GOOGLE_SEARCH_API_KEY`. |
| `GEMINI_API_KEY` | No | Generated automatically by the script, scoped to `generativelanguage.googleapis.com`. Retained for optional Vertex AI / Gemini integration. |

To set up a Google Custom Search Engine for the web search feature:
1. Create a CSE at https://programmablesearchengine.google.com/
2. Enable the Custom Search API at https://console.cloud.google.com/apis
3. Create an API key restricted to the Custom Search API

---

## 5. Deploying to GCP Cloud Run

```bash
cd deployment/gcp
chmod +x deploy_infrastructure.sh

# Usage: ./deploy_infrastructure.sh <PROJECT_ID> [REGION] [APP_NAME]
./deploy_infrastructure.sh my-gcp-project-id us-central1 openimpactcascade
```

**Arguments:**

| Argument | Required | Default | Notes |
|----------|----------|---------|-------|
| `PROJECT_ID` | Yes | — | Your GCP project ID |
| `REGION` | No | `us-central1` | Any Cloud Run supported region. For Canadian data residency use `northamerica-northeast1` (Montreal). |
| `APP_NAME` | No | `openimpactcascade` | Used as the Cloud Run service name, service account name, and Artifact Registry repo name |

The script is **idempotent** — running it a second time on the same project will skip resources that already exist and only perform new steps (or redeploy the container image). It is safe to re-run after updating the application code.

The script will prompt interactively for each secret value. Input is read with `read -s` (no echo to terminal, not stored in shell history).

---

## 6. What the Script Does

The script executes six sequential phases:

**Phase 1 — Enable APIs**

Enables: `compute`, `run`, `aiplatform`, `secretmanager`, `artifactregistry`, `storage-component`, `logging`, `iam`, `cloudbuild`, `generativelanguage`, `apikeys`

**Phase 2 — Service account setup**

Creates `<APP_NAME>-cr-sa` and grants it `aiplatform.user`, `storage.objectAdmin`, and `logging.logWriter`. Grants the Compute Engine default service account the roles needed for Cloud Build to function.

**Phase 3 — GCS bucket**

Creates `<APP_NAME>-appdata-<PROJECT_ID>` with uniform bucket-level access in the selected region. Used for application data and optional session persistence.

**Phase 4 — Secrets**

Generates a scoped Gemini API key and stores it as `GEMINI_API_KEY`. Then prompts for and creates: `ANTHROPIC_API_KEY`, `SECRET_KEY`, `GOOGLE_SEARCH_API_KEY`, `GOOGLE_SEARCH_CSE_ID`, `APP_USERNAME`, `APP_PASSWORD`. Grants the runtime service account `secretmanager.secretAccessor` on each secret individually.

**Phase 5 — Artifact Registry and image build**

Creates a Docker repository in Artifact Registry. Submits the build to Cloud Build using the project root as the build context (the `Dockerfile` at the repo root). The image is tagged and pushed to Artifact Registry.

**Phase 6 — Cloud Run deployment**

Deploys the container with:
- 2 vCPU / 2 GiB memory
- Request timeout: 300 seconds (accommodates AI generation calls)
- Scale: 0–3 instances (scales to zero when idle)
- All secrets mounted from Secret Manager
- Unauthenticated access allowed (application-level auth is handled by the login page)

---

## 7. Cloud Run Service Configuration

The deployed service receives these settings:

**Plain environment variables** (non-sensitive, set at deploy time):

| Variable | Value |
|----------|-------|
| `GOOGLE_CLOUD_PROJECT` | Your project ID |
| `GCS_BUCKET_NAME` | `<APP_NAME>-appdata-<PROJECT_ID>` |
| `VERTEX_AI_LOCATION` | Your selected region |
| `PORT` | `8080` (set in Dockerfile) |

**From Secret Manager** (mounted at runtime, not visible in Cloud Run console):

`ANTHROPIC_API_KEY`, `SECRET_KEY`, `GOOGLE_SEARCH_API_KEY`, `GOOGLE_SEARCH_CSE_ID`, `GEMINI_API_KEY`, `APP_USERNAME`, `APP_PASSWORD`

**Optional feature flag environment variables** (not set by the script, use Cloud Run console or `gcloud run services update` to add):

| Variable | Default | Description |
|----------|---------|-------------|
| `OIC_MODEL` | `claude-sonnet-4-6` | Primary LLM model |
| `OIC_MODEL_FAST` | `claude-haiku-4-5` | Fast model for lightweight tasks |
| `OIC_CARDS_ENABLED` | `1` | Enable cascade archetype library |
| `OIC_ARCHETYPE_SELECT` | `1` | Show archetype selector on generate form |
| `OIC_ARCHETYPE_LIMIT` | `3` | Max archetypes shown in selector |
| `OIC_PILLARS_ENABLED` | `1` | Enable DBIR/IBM/NetDiligence reference data |
| `OIC_MC_COMPOUND` | `1` | Use compound Monte Carlo simulation mode |
| `OIC_PROMPT_CACHE` | `1` | Enable Anthropic prompt caching |

---

## 8. Running Locally with Docker

For local testing or development, build and run the container directly. Store secrets in a local `.env` file — never hardcode them in scripts.

```bash
# Create a local .env file (this file is gitignored)
cat > .env.local << 'EOF'
ANTHROPIC_API_KEY=your-key-here
SECRET_KEY=any-random-string-for-local
APP_USERNAME=admin
APP_PASSWORD=your-local-password
# Optional — leave blank to run corpus-only without web search
GOOGLE_SEARCH_API_KEY=
GOOGLE_SEARCH_CSE_ID=
EOF
```

```bash
# Build the image
docker build -t openimpactcascade:local .

# Run it
docker run --rm -p 8080:8080 --env-file .env.local openimpactcascade:local
```

The application will be available at `http://localhost:8080`.

**Notes on local behaviour:**
- The corpus (DBIR/IBM/NetDiligence reference data) and cascade archetype cards are baked into the image at build time — they will reflect the state of `app/corpus/` and `app/generated/cascade_archetypes/` when you ran `docker build`
- Session storage uses SQLite (in-container `/tmp`); sessions do not persist across container restarts
- The GCS bucket is not required locally; the app runs without it

**Running without Docker** (Flask dev server):

```bash
cd app
pip install -r requirements.txt

# Set environment variables in your shell
export ANTHROPIC_API_KEY="your-key"
export SECRET_KEY="local-dev-secret"
export APP_USERNAME="admin"
export APP_PASSWORD="localpass"

python main.py
```

The Flask dev server starts on port 8080. This is suitable for development only — do not expose it directly.

---

## 9. Post-Deployment Verification

After the script completes, retrieve the service URL:

```bash
gcloud run services describe openimpactcascade \
    --region us-central1 \
    --format="value(status.url)"
```

**Health check:**

```bash
curl -s https://<YOUR_SERVICE_URL>/health
# Expected: {"status": "healthy", "ai_enabled": true}
```

**Smoke test:**

1. Open the service URL in a browser
2. Log in with the `APP_USERNAME` / `APP_PASSWORD` you set during deployment
3. Generate a test questionnaire (Healthcare, Canada)
4. Confirm the questionnaire page loads and the chat assistant responds

**Check logs if something is wrong:**

```bash
gcloud logging read \
    "resource.type=cloud_run_revision AND resource.labels.service_name=openimpactcascade" \
    --limit 50 \
    --format "value(textPayload)"
```

Common startup failures:
- `APP_PASSWORD environment variable is not set` — the secret was not created or the service account does not have accessor rights; verify with `gcloud secrets get-iam-policy APP_PASSWORD`
- `AI Generator not available` — `ANTHROPIC_API_KEY` secret is missing or inaccessible; the app will still start but questionnaire generation will be disabled
- Cold start timeout — the first request after a scale-to-zero event takes 15–30 seconds; this is normal

---

## 10. Updating an Existing Deployment

To deploy a new version of the code after changes:

```bash
# Rebuild and push the image
PROJECT_ID="your-project-id"
REGION="us-central1"
APP_NAME="openimpactcascade"
REPO_NAME="${APP_NAME}-repo"
IMAGE_TAG="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${APP_NAME}:latest"

gcloud builds submit . \
    --tag "$IMAGE_TAG" \
    --project "$PROJECT_ID"

# Deploy the new image to Cloud Run
gcloud run deploy "$APP_NAME" \
    --image "$IMAGE_TAG" \
    --region "$REGION" \
    --project "$PROJECT_ID"
```

Cloud Run performs a zero-downtime rolling deployment — existing requests complete on the previous revision while the new one starts.

To update a secret value (e.g. rotate the Anthropic key):

```bash
echo -n "new-key-value" | gcloud secrets versions add ANTHROPIC_API_KEY \
    --project "$PROJECT_ID" \
    --data-file=-
```

Secret Manager secrets are read at container startup. After adding a new version, redeploy the Cloud Run service (or trigger a new revision) for the new value to take effect.
