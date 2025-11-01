#!/bin/bash
#
# Bootstrap script for OpenImpactCascade GCP Project Setup
# This script sets up all required GCP resources for Vertex AI RAG integration
#
# Usage: ./bootstrap.sh PROJECT_ID [REGION]
#
# Example: ./bootstrap.sh my-risk-assessment-project northamerica-northeast1
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=${1:-""}
REGION=${2:-"northamerica-northeast1"}
SERVICE_ACCOUNT_NAME="oic-rarag"
RAG_CORPUS_NAME="oic-rarag-kb"
BUCKET_SUFFIX="rarag-kb"

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Validate prerequisites
print_info "Validating prerequisites..."

if [ -z "$PROJECT_ID" ]; then
    print_error "Project ID is required"
    echo "Usage: ./bootstrap.sh PROJECT_ID [REGION]"
    exit 1
fi

if ! command_exists gcloud; then
    print_error "gcloud CLI is not installed"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

if ! command_exists jq; then
    print_warning "jq is not installed (optional, but recommended)"
    echo "Install with: sudo apt-get install jq (Linux) or brew install jq (Mac)"
fi

print_success "Prerequisites validated"

# Set project
print_info "Setting GCP project to: $PROJECT_ID"
gcloud config set project "$PROJECT_ID" || {
    print_error "Failed to set project. Does the project exist?"
    exit 1
}
print_success "Project set"

# Enable required APIs
print_info "Enabling required GCP APIs..."
APIS=(
    "aiplatform.googleapis.com"
    "storage-api.googleapis.com"
    "iam.googleapis.com"
    "cloudresourcemanager.googleapis.com"
)

for api in "${APIS[@]}"; do
    print_info "Enabling $api..."
    gcloud services enable "$api" --project="$PROJECT_ID" || {
        print_error "Failed to enable $api"
        exit 1
    }
done
print_success "All APIs enabled"

# Create service account
print_info "Creating service account: $SERVICE_ACCOUNT_NAME..."
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if gcloud iam service-accounts describe "$SERVICE_ACCOUNT_EMAIL" --project="$PROJECT_ID" >/dev/null 2>&1; then
    print_warning "Service account already exists: $SERVICE_ACCOUNT_EMAIL"
else
    gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
        --display-name="OIC RAG Service Account" \
        --project="$PROJECT_ID" || {
        print_error "Failed to create service account"
        exit 1
    }
    print_success "Service account created"
fi

# Grant IAM roles
print_info "Granting IAM roles to service account..."
ROLES=(
    "roles/aiplatform.user"
    "roles/storage.objectAdmin"
)

for role in "${ROLES[@]}"; do
    print_info "Granting $role..."
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
        --role="$role" \
        --condition=None \
        >/dev/null || {
        print_error "Failed to grant $role"
        exit 1
    }
done
print_success "IAM roles granted"

# Create service account key
print_info "Creating service account key..."
KEY_FILE="service-account-key.json"

if [ -f "$KEY_FILE" ]; then
    print_warning "Service account key already exists: $KEY_FILE"
    read -p "Overwrite? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Skipping key creation"
    else
        rm "$KEY_FILE"
        gcloud iam service-accounts keys create "$KEY_FILE" \
            --iam-account="$SERVICE_ACCOUNT_EMAIL" \
            --project="$PROJECT_ID" || {
            print_error "Failed to create service account key"
            exit 1
        }
        print_success "Service account key created: $KEY_FILE"
    fi
else
    gcloud iam service-accounts keys create "$KEY_FILE" \
        --iam-account="$SERVICE_ACCOUNT_EMAIL" \
        --project="$PROJECT_ID" || {
        print_error "Failed to create service account key"
        exit 1
    }
    print_success "Service account key created: $KEY_FILE"
fi

# Create GCS bucket
print_info "Creating GCS bucket for knowledge base..."
BUCKET_NAME="${PROJECT_ID}-${BUCKET_SUFFIX}"

if gsutil ls -b "gs://$BUCKET_NAME" >/dev/null 2>&1; then
    print_warning "Bucket already exists: gs://$BUCKET_NAME"
else
    gsutil mb -l "$REGION" -p "$PROJECT_ID" "gs://$BUCKET_NAME" || {
        print_error "Failed to create bucket"
        exit 1
    }
    print_success "Bucket created: gs://$BUCKET_NAME"
fi

# Set bucket lifecycle (optional - delete old files after 365 days)
print_info "Setting bucket lifecycle policy..."
cat > /tmp/lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 365,
          "matchesPrefix": ["archive/"]
        }
      }
    ]
  }
}
EOF

gsutil lifecycle set /tmp/lifecycle.json "gs://$BUCKET_NAME" || {
    print_warning "Failed to set lifecycle policy (non-critical)"
}
rm /tmp/lifecycle.json

# Create .env.gcp file
print_info "Creating environment configuration file..."
ENV_FILE=".env.gcp"

cat > "$ENV_FILE" <<EOF
# GCP Configuration for OpenImpactCascade
# Generated on $(date)
# DO NOT COMMIT THIS FILE TO VERSION CONTROL

# GCP Project Configuration
GOOGLE_CLOUD_PROJECT=$PROJECT_ID
GCP_REGION=$REGION

# Vertex AI RAG Configuration
VERTEX_RAG_CORPUS=$RAG_CORPUS_NAME
VERTEX_RAG_GCS_BUCKET=$BUCKET_NAME

# Service Account
GOOGLE_APPLICATION_CREDENTIALS=$(pwd)/$KEY_FILE

# Application Configuration (copy from main .env)
# ANTHROPIC_API_KEY=your-anthropic-key
# SECRET_KEY=your-flask-secret
EOF

print_success "Environment file created: $ENV_FILE"

# Create .gitignore entries
print_info "Updating .gitignore..."
GITIGNORE="../.gitignore"

if [ ! -f "$GITIGNORE" ]; then
    touch "$GITIGNORE"
fi

if ! grep -q "service-account-key.json" "$GITIGNORE"; then
    cat >> "$GITIGNORE" <<EOF

# GCP Infrastructure
infra/service-account-key.json
infra/.env.gcp
infra/terraform.tfstate
infra/terraform.tfstate.backup
infra/.terraform/
EOF
    print_success ".gitignore updated"
else
    print_info ".gitignore already contains GCP entries"
fi

# Print summary
echo ""
echo "=========================================="
print_success "Bootstrap Complete!"
echo "=========================================="
echo ""
echo "GCP Resources Created:"
echo "  Project ID:        $PROJECT_ID"
echo "  Region:            $REGION"
echo "  Service Account:   $SERVICE_ACCOUNT_EMAIL"
echo "  GCS Bucket:        gs://$BUCKET_NAME"
echo "  RAG Corpus Name:   $RAG_CORPUS_NAME"
echo ""
echo "Local Files Created:"
echo "  Service Account Key: $KEY_FILE"
echo "  Environment Config:  $ENV_FILE"
echo ""
echo "Next Steps:"
echo "  1. Review and source the environment file:"
echo "     source $ENV_FILE"
echo ""
echo "  2. Copy your Anthropic API key to $ENV_FILE"
echo ""
echo "  3. Create the RAG corpus:"
echo "     cd .."
echo "     python -c \"from knowledge_base_manager import KnowledgeBaseManager; kb = KnowledgeBaseManager(); kb.create_rag_corpus('$RAG_CORPUS_NAME', 'Risk assessment knowledge base')\""
echo ""
echo "  4. Populate the knowledge base:"
echo "     python knowledge_base_manager.py"
echo ""
echo "  5. Test the integration:"
echo "     python vertex_rag.py"
echo ""
print_warning "IMPORTANT: Never commit $KEY_FILE or $ENV_FILE to version control!"
echo ""
