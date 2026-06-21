#!/bin/bash
# Comprehensive GCP Infrastructure Setup and Deployment Script
# As of May 2026

set -e

# =============================================================================
# PREREQUISITES & CONFIGURATION
# =============================================================================

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <PROJECT_ID> [REGION] [APP_NAME]"
    echo "Example: $0 my-oic-project us-central1 openimpactcascade"
    exit 1
fi

PROJECT_ID=$1
REGION=${2:-us-central1}
APP_NAME=${3:-openimpactcascade}

# Variables
SA_NAME="${APP_NAME}-cr-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
REPO_NAME="${APP_NAME}-repo"
IMAGE_TAG="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${APP_NAME}:latest"
GCS_BUCKET_NAME="${APP_NAME}-appdata-${PROJECT_ID}"

echo "============================================================"
echo "Starting GCP Deployment for Project: $PROJECT_ID"
echo "Region: $REGION"
echo "App Name: $APP_NAME"
echo "============================================================"

# Ensure gcloud is configured with the correct project
gcloud config set project "$PROJECT_ID"
gcloud config set run/region "$REGION"

# =============================================================================
# 1. ENABLE APIS
# =============================================================================
echo "Enabling necessary GCP APIs..."
gcloud services enable \
    compute.googleapis.com \
    run.googleapis.com \
    aiplatform.googleapis.com \
    secretmanager.googleapis.com \
    artifactregistry.googleapis.com \
    storage-component.googleapis.com \
    logging.googleapis.com \
    iam.googleapis.com \
    cloudbuild.googleapis.com \
    generativelanguage.googleapis.com \
    apikeys.googleapis.com \
    --project "$PROJECT_ID"

# =============================================================================
# 2. SERVICE ACCOUNT CONFIGURATION
# =============================================================================
echo "Setting up Application Service Account ($SA_EMAIL)..."

if ! gcloud iam service-accounts describe "$SA_EMAIL" &>/dev/null; then
    gcloud iam service-accounts create "$SA_NAME" \
        --display-name "$APP_NAME Cloud Run Service Account" \
        --project "$PROJECT_ID"
else
    echo "Service Account already exists."
fi

# Grant necessary IAM roles for runtime operations
APP_ROLES=(
    "roles/aiplatform.user"       # For Vertex AI RAG and Models
    "roles/storage.objectAdmin"   # For reading/writing GCS
    "roles/logging.logWriter"     # For writing application logs
)

for ROLE in "${APP_ROLES[@]}"; do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="$ROLE" \
        --condition=None \
        --quiet
done

# In many enterprise environments, the Compute Engine Default Service Account 
# (which Cloud Build uses by default) has its default Editor role stripped.
# We must explicitly grant it permissions to build, read sources from GCS, and push to Artifact Registry.
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Configuring Cloud Build permissions for Default Compute SA ($COMPUTE_SA)..."
BUILD_ROLES=(
    "roles/storage.admin"            # Needs to read/write source and logs in GCS
    "roles/artifactregistry.writer"  # Needs to push the compiled image
    "roles/logging.logWriter"        # Needs to write build logs
)

for ROLE in "${BUILD_ROLES[@]}"; do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${COMPUTE_SA}" \
        --role="$ROLE" \
        --condition=None \
        --quiet
done

# =============================================================================
# 3. STORAGE BUCKET CONFIGURATION
# =============================================================================
echo "Ensuring Application Data GCS Bucket exists..."
if ! gcloud storage buckets describe "gs://$GCS_BUCKET_NAME" &>/dev/null; then
    gcloud storage buckets create "gs://$GCS_BUCKET_NAME" \
        --project="$PROJECT_ID" \
        --location="$REGION" \
        --uniform-bucket-level-access
else
    echo "Bucket gs://$GCS_BUCKET_NAME already exists."
fi

# =============================================================================
# 4. SECRET MANAGER & API KEYS SETUP
# =============================================================================

echo "Setting up API Keys..."
if ! gcloud secrets describe "GEMINI_API_KEY" --project="$PROJECT_ID" &>/dev/null; then
    echo "Generating scoped Gemini API Key..."
    
    # Create key scoped to generativelanguage.googleapis.com
    gcloud services api-keys create \
        --display-name="${APP_NAME}-gemini-key" \
        --api-target=service=generativelanguage.googleapis.com \
        --project="$PROJECT_ID"
    
    echo "Waiting for API key to be created..."
    sleep 5
    
    # Retrieve the key name using its display name
    KEY_NAME=$(gcloud services api-keys list \
        --filter="displayName=${APP_NAME}-gemini-key" \
        --project="$PROJECT_ID" \
        --format="value(name)" \
        --limit=1)
    
    GEMINI_KEY_VALUE=$(gcloud services api-keys get-key-string "$KEY_NAME" \
        --project="$PROJECT_ID" \
        --format="value(keyString)")
        
    echo -n "$GEMINI_KEY_VALUE" | gcloud secrets create "GEMINI_API_KEY" \
        --project="$PROJECT_ID" \
        --replication-policy="automatic" \
        --data-file=-
    
    echo "Successfully generated and stored GEMINI_API_KEY."
else
    echo "Secret GEMINI_API_KEY already exists. Skipping generation."
fi

# Ensure SA has access to the generated key
gcloud secrets add-iam-policy-binding "GEMINI_API_KEY" \
    --project="$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None \
    --quiet

# The application requires several sensitive keys. We will store these in Secret Manager.
#
# Search provider notes:
#   TAVILY_API_KEY       — Primary provider key (recommended — purpose-built for LLM grounding).
#                          Sign up at https://tavily.com  (1,000 free queries/month).
#   BRAVE_SEARCH_API_KEY — Fallback provider key.  Having both means web search continues
#                          automatically if Tavily hits quota or is temporarily down.
#                          Sign up at https://api-dashboard.search.brave.com/ (2,000 free/month).
#   OIC_SEARCH_PROVIDER  — Active primary provider. Stored as a secret so the operator can
#                          switch providers (e.g. tavily → brave) without a container redeploy.
#                          Typical value: tavily
#   OIC_SEARCH_FALLBACK  — Comma-separated fallback chain tried on quota/timeout/rate-limit.
#                          Typical value: brave   (i.e. fall back to Brave when Tavily is down)
#                          The failover is invisible to end-users.
#
# Both TAVILY_API_KEY and BRAVE_SEARCH_API_KEY should be provisioned so the fallback
# chain is always available.  Skipping one means there is no failover for that provider.
#
# Google Custom Search (GOOGLE_SEARCH_API_KEY / GOOGLE_SEARCH_CSE_ID) has been removed.
# The service is closed to new customers and deprecated Jan 2027.
SECRETS=(
    "ANTHROPIC_API_KEY"
    "SECRET_KEY"
    "TAVILY_API_KEY"
    "BRAVE_SEARCH_API_KEY"
    "OIC_SEARCH_PROVIDER"
    "OIC_SEARCH_FALLBACK"
    "APP_USERNAME"
    "APP_PASSWORD"
)

echo "Setting up remaining Secret Manager secrets..."

# OIC_SEARCH_FALLBACK has a safe default (brave) so it is optional at the prompt.
# Both search provider keys are strongly encouraged but individually skippable
# (you lose failover for whichever one is absent).
OPTIONAL_SECRETS=(
    "BRAVE_SEARCH_API_KEY"    # strongly recommended — failover when Tavily is down
    "OIC_SEARCH_FALLBACK"     # safe default is "brave"; skip only if single-provider is acceptable
)

for SECRET in "${SECRETS[@]}"; do
    if ! gcloud secrets describe "$SECRET" --project="$PROJECT_ID" &>/dev/null; then
        # Check if this is an optional secret
        IS_OPTIONAL=false
        for OPT in "${OPTIONAL_SECRETS[@]}"; do
            if [ "$SECRET" = "$OPT" ]; then IS_OPTIONAL=true; break; fi
        done

        if [ "$SECRET" = "OIC_SEARCH_FALLBACK" ]; then
            read -p "Enter value for $SECRET [default: brave] (press Enter to use default): " SECRET_VALUE
            echo
            if [ -z "$SECRET_VALUE" ]; then
                SECRET_VALUE="brave"
                echo "Using default value 'brave' for OIC_SEARCH_FALLBACK."
            fi
        elif [ "$IS_OPTIONAL" = true ]; then
            read -s -p "Enter value for $SECRET (press Enter to skip — failover for this provider will be unavailable): " SECRET_VALUE
            echo
        else
            read -s -p "Enter value for $SECRET: " SECRET_VALUE
            echo
        fi

        if [ -z "$SECRET_VALUE" ] && [ "$IS_OPTIONAL" = true ]; then
            echo "Skipping optional secret $SECRET (no value provided — no failover for this provider)."
            continue
        fi

        if [ -z "$SECRET_VALUE" ]; then
            echo "ERROR: $SECRET is required and cannot be empty."
            exit 1
        fi

        echo -n "$SECRET_VALUE" | gcloud secrets create "$SECRET" \
            --project="$PROJECT_ID" \
            --replication-policy="automatic" \
            --data-file=-

        echo "Successfully created secret $SECRET."
    else
        echo "Secret $SECRET already exists. Skipping creation."
    fi

    # Grant Cloud Run service account access to the secret
    gcloud secrets add-iam-policy-binding "$SECRET" \
        --project="$PROJECT_ID" \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="roles/secretmanager.secretAccessor" \
        --condition=None \
        --quiet
done

# =============================================================================
# 5. ARTIFACT REGISTRY & BUILD
# =============================================================================
echo "Setting up Artifact Registry..."
if ! gcloud artifacts repositories describe "$REPO_NAME" --location="$REGION" --project="$PROJECT_ID" &>/dev/null; then
    gcloud artifacts repositories create "$REPO_NAME" \
        --repository-format=docker \
        --location="$REGION" \
        --description="Docker repository for $APP_NAME" \
        --project="$PROJECT_ID"
else
    echo "Artifact Registry repository already exists."
fi

# Authenticate Docker to Artifact Registry
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

echo "Building and pushing Docker image using Cloud Build..."
# Navigate to project root assuming script is run from deployment/gcp or root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

gcloud builds submit "$PROJECT_ROOT" \
    --tag "$IMAGE_TAG" \
    --project "$PROJECT_ID"

# =============================================================================
# 6. CLOUD RUN DEPLOYMENT
# =============================================================================
echo "Deploying to Cloud Run..."

# Set up Vertex AI Corpus Placeholder
# Uncomment if using Vertex AI RAG Corpus functionality
# read -p "Enter VERTEX_RAG_CORPUS ID or name (leave blank if not using): " VERTEX_RAG_CORPUS
VERTEX_RAG_CORPUS=""

# Build the --set-secrets argument dynamically.
# Required secrets are always included; optional secrets (e.g. BRAVE_SEARCH_API_KEY)
# are only mounted if the Secret Manager secret actually exists — so skipping an
# optional key during setup above does not break the deploy command.
REQUIRED_SECRETS=(
    "ANTHROPIC_API_KEY"
    "SECRET_KEY"
    "TAVILY_API_KEY"
    "OIC_SEARCH_PROVIDER"
    "OIC_SEARCH_FALLBACK"
    "GEMINI_API_KEY"
    "APP_USERNAME"
    "APP_PASSWORD"
)
# BRAVE_SEARCH_API_KEY is optional — only mounted if provisioned above.
# OIC_SEARCH_FALLBACK is required (has a safe "brave" default) so it is in REQUIRED_SECRETS,
# but if for any reason it doesn't exist in Secret Manager, we catch it here too.
OPTIONAL_DEPLOY_SECRETS=(
    "BRAVE_SEARCH_API_KEY"
)

SECRET_FLAGS=""
for S in "${REQUIRED_SECRETS[@]}"; do
    SECRET_FLAGS="${SECRET_FLAGS}${S}=${S}:latest,"
done
for S in "${OPTIONAL_DEPLOY_SECRETS[@]}"; do
    if gcloud secrets describe "$S" --project="$PROJECT_ID" &>/dev/null; then
        SECRET_FLAGS="${SECRET_FLAGS}${S}=${S}:latest,"
    else
        echo "Optional secret $S not found in Secret Manager — skipping mount."
    fi
done
# Strip trailing comma
SECRET_FLAGS="${SECRET_FLAGS%,}"

gcloud run deploy "$APP_NAME" \
    --image "$IMAGE_TAG" \
    --platform managed \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --service-account "$SA_EMAIL" \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 3 \
    --min-instances 0 \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GCS_BUCKET_NAME=$GCS_BUCKET_NAME,VERTEX_AI_LOCATION=$REGION,VERTEX_RAG_CORPUS=$VERTEX_RAG_CORPUS" \
    --set-secrets="$SECRET_FLAGS" \
    --allow-unauthenticated

echo "============================================================"
echo "Deployment Complete!"
echo "Service Account: $SA_EMAIL"
echo "Cloud Run Service: $APP_NAME"
echo "============================================================"
