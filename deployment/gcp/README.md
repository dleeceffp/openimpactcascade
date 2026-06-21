# Google Cloud Platform Deployment Guide
*Updated June 2026*

This guide walks you through deploying the OpenImpactCascade (OIC) application to Google Cloud Run, utilising standard GCP services and securely handling secrets via Google Secret Manager.

## Architectural Overview

| Layer | Service |
|---|---|
| Compute | Google Cloud Run (fully managed, scalable) |
| Container Registry | Google Artifact Registry |
| Secrets | Google Secret Manager — no API keys in plain env vars |
| Storage | Google Cloud Storage (GCS) |
| IAM | Dedicated service account, least-privilege roles |
| Web Search | Tavily (primary) + Brave (fallback) via `oic_search` |

## Prerequisites

- A Google Cloud Project where you have **Owner** privileges.
- `gcloud` CLI installed locally (or use Cloud Shell).
- Docker installed locally (only needed if building locally instead of Cloud Build).

---

## 1. Using the Automated Deployment Script

The entire infrastructure is provisioned by a single script.

```bash
cd deployment/gcp
chmod +x deploy_infrastructure.sh

# Usage: ./deploy_infrastructure.sh <PROJECT_ID> [REGION] [APP_NAME]
./deploy_infrastructure.sh my-gcp-project-id us-central1 openimpactcascade
```

### What the Script Does

| Step | Action |
|---|---|
| 1 | Enables required GCP APIs (Cloud Run, Secret Manager, Artifact Registry, etc.) |
| 2 | Creates a dedicated Cloud Run service account |
| 3 | Grants IAM roles: `aiplatform.user`, `storage.objectAdmin`, `logging.logWriter` |
| 4 | Creates a GCS bucket for application data |
| 5 | Generates a scoped Gemini API key and stores it in Secret Manager |
| 6 | Prompts for all remaining secrets and writes them to Secret Manager |
| 7 | Creates an Artifact Registry Docker repository, builds the image via Cloud Build |
| 8 | Deploys to Cloud Run with secrets mounted from Secret Manager |

### Secrets Provisioned

The script prompts for the following secrets.  All are written to Google Secret Manager and mounted into Cloud Run at runtime — none are passed as plain environment variables.

| Secret | Required | Default (press Enter) | Notes |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | — | Claude LLM key |
| `SECRET_KEY` | Yes | — | Flask session signing key |
| `GEMINI_API_KEY` | Auto | — | Generated automatically from GCP |
| `TAVILY_API_KEY` | Yes | — | Primary web search provider. Sign up: https://tavily.com (1,000 free queries/month) |
| `BRAVE_SEARCH_API_KEY` | Recommended | *(skippable)* | Fallback search provider. Sign up: https://api-dashboard.search.brave.com/ (2,000 free/month). Skipping disables automatic failover. |
| `OIC_SEARCH_PROVIDER` | Yes | `tavily` | Active primary provider name |
| `OIC_SEARCH_FALLBACK` | Yes | `brave` | Comma-separated fallback chain (e.g. `brave`) |
| `APP_USERNAME` | Yes | — | Basic-auth username |
| `APP_PASSWORD` | Yes | — | Basic-auth password |

> **Why two search providers?**  
> Tavily and Brave have independent quota pools and different upstream indexes.  Having both provisioned means web search continues automatically if the primary hits its daily quota or experiences a transient outage — the failover is transparent to end-users.  The application logs which provider was used at the `INFO` level.

---

## 2. Web Search Architecture

Web search grounding is handled by the `oic_search` shared module (`src/oic_search/`), which is copied into the container at build time and injected via `PYTHONPATH`.

### Provider selection

```
OIC_SEARCH_PROVIDER=tavily       # primary
OIC_SEARCH_FALLBACK=brave        # fallback (comma-separated, tried in order)
```

Both values are stored in Secret Manager and mounted as environment variables by Cloud Run.  Changing the active provider does not require a container rebuild — update the secret value and redeploy the revision.

### Fallback behaviour

| Primary result | Fallback triggered? |
|---|---|
| Success | No |
| Quota / rate-limit / timeout | **Yes** — next provider in `OIC_SEARCH_FALLBACK` chain |
| Auth / not-configured | **No** — permanent misconfiguration, logged and search disabled |
| All providers exhausted | No further retry — search returns empty, generation continues |

### Deprecated: Google Custom Search Engine

`GOOGLE_SEARCH_API_KEY` and `GOOGLE_SEARCH_CSE_ID` have been removed from the deployment script and from the application.  Google CSE is closed to new customers (mid-2025) and deprecated for all users on **January 1, 2027**.  Do not add these back.

---

## 3. Managing Vertex AI RAG

If you are using Vertex AI RAG functionality, set `VERTEX_RAG_CORPUS` in the deployment script.  You can create or manage your RAG corpus via the Vertex AI API or the Cloud Console.

---

## 4. Local Development

**Do not hardcode API keys.**  For local development use a `.env` file (gitignored) in the repository root or `app/` directory.  The application loads it automatically via `python-dotenv` with `override=False`, so container secrets always win over `.env` values.

```bash
# Copy the template and fill in your keys
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY, TAVILY_API_KEY, BRAVE_SEARCH_API_KEY, etc.
```

To run the container locally with Google Application Default Credentials:

```bash
gcloud auth application-default login

docker run -p 8080:8080 \
    -e ANTHROPIC_API_KEY="your-local-key" \
    -e SECRET_KEY="local-secret" \
    -e TAVILY_API_KEY="tvly-..." \
    -e BRAVE_SEARCH_API_KEY="BSA..." \
    -e OIC_SEARCH_PROVIDER="tavily" \
    -e OIC_SEARCH_FALLBACK="brave" \
    -e GOOGLE_CLOUD_PROJECT="my-gcp-project-id" \
    -e GCS_BUCKET_NAME="openimpactcascade-appdata-my-gcp-project-id" \
    -e VERTEX_AI_LOCATION="us-central1" \
    -v ~/.config/gcloud/application_default_credentials.json:/app/sa.json:ro \
    -e GOOGLE_APPLICATION_CREDENTIALS="/app/sa.json" \
    openimpactcascade:latest
```

---

## 5. Troubleshooting

| Symptom | Check |
|---|---|
| Permission errors during deploy | `gcloud auth login` — verify Owner/Editor rights on the project |
| Secret not found at runtime | Confirm the Cloud Run service account has `roles/secretmanager.secretAccessor` on the secret (the script grants this automatically) |
| Web search returning empty results | Check Cloud Logging for `oic.ai_question_generator` — look for `provider chain` at INFO level and any `WARNING` entries indicating quota or auth errors |
| Tavily quota exhausted | Search falls back to Brave automatically; if Brave is also exhausted, generation continues without web grounding |
| `BRAVE_SEARCH_API_KEY not set` in logs | The secret was skipped during provisioning — re-run the script or create the secret manually: `echo -n "BSA..." \| gcloud secrets create BRAVE_SEARCH_API_KEY --data-file=-` |
| Search disabled at startup | Check that `OIC_SEARCH_PROVIDER` and the corresponding API key secret are both present and the service account has accessor rights on both |
