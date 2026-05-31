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
echo "Setting up Service Account ($SA_EMAIL)..."

if ! gcloud iam service-accounts describe "$SA_EMAIL" &>/dev/null; then
    gcloud iam service-accounts create "$SA_NAME" \
        --display-name "$APP_NAME Cloud Run Service Account" \
        --project "$PROJECT_ID"
else
    echo "Service Account already exists."
fi

# Grant necessary IAM roles for runtime operations
ROLES=(
    "roles/aiplatform.user"       # For Vertex AI RAG and Models
    "roles/storage.objectAdmin"   # For reading/writing GCS
    "roles/logging.logWriter"     # For writing application logs
)

for ROLE in "${ROLES[@]}"; do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${SA_EMAIL}" \
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
SECRETS=(
    "ANTHROPIC_API_KEY"
    "SECRET_KEY"
    "GOOGLE_SEARCH_API_KEY"
    "GOOGLE_SEARCH_CSE_ID"
)

echo "Setting up remaining Secret Manager secrets..."
for SECRET in "${SECRETS[@]}"; do
    if ! gcloud secrets describe "$SECRET" --project="$PROJECT_ID" &>/dev/null; then
        echo "Creating secret: $SECRET (You will be prompted to provide the value)"
        
        # We read securely to not store secrets in bash history
        read -s -p "Enter value for $SECRET: " SECRET_VALUE
        echo
        
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

# Set up Vertex AI Corpus Placeholder (You can override this as needed)
read -p "Enter VERTEX_RAG_CORPUS ID or name (leave blank if not using): " VERTEX_RAG_CORPUS

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
    --set-secrets="ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest,SECRET_KEY=SECRET_KEY:latest,GOOGLE_SEARCH_API_KEY=GOOGLE_SEARCH_API_KEY:latest,GOOGLE_SEARCH_CSE_ID=GOOGLE_SEARCH_CSE_ID:latest,GEMINI_API_KEY=GEMINI_API_KEY:latest" \
    --allow-unauthenticated

echo "============================================================"
echo "Deployment Complete!"
echo "Service Account: $SA_EMAIL"
echo "Cloud Run Service: $APP_NAME"
echo "============================================================"
