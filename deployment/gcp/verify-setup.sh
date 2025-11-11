#!/bin/bash
#
# Verification script for OpenImpactCascade GCP setup
# Checks that all required resources are properly configured
#
# Usage: ./verify-setup.sh PROJECT_ID
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }

PROJECT_ID=${1:-""}
SERVICE_ACCOUNT_NAME="oic-rarag"
BUCKET_SUFFIX="rarag-kb"

if [ -z "$PROJECT_ID" ]; then
    print_error "Project ID is required"
    echo "Usage: ./verify-setup.sh PROJECT_ID"
    exit 1
fi

echo "=========================================="
echo "  GCP Setup Verification"
echo "  Project: $PROJECT_ID"
echo "=========================================="
echo ""

ERRORS=0

# Check gcloud
print_info "Checking gcloud CLI..."
if command -v gcloud >/dev/null 2>&1; then
    print_success "gcloud CLI installed"
else
    print_error "gcloud CLI not found"
    ((ERRORS++))
fi

# Check project access
print_info "Checking project access..."
if gcloud projects describe "$PROJECT_ID" >/dev/null 2>&1; then
    print_success "Project accessible: $PROJECT_ID"
else
    print_error "Cannot access project: $PROJECT_ID"
    ((ERRORS++))
fi

# Check APIs
print_info "Checking enabled APIs..."
REQUIRED_APIS=(
    "aiplatform.googleapis.com"
    "storage-api.googleapis.com"
    "iam.googleapis.com"
)

for api in "${REQUIRED_APIS[@]}"; do
    if gcloud services list --enabled --project="$PROJECT_ID" --filter="name:$api" --format="value(name)" | grep -q "$api"; then
        print_success "API enabled: $api"
    else
        print_error "API not enabled: $api"
        ((ERRORS++))
    fi
done

# Check service account
print_info "Checking service account..."
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if gcloud iam service-accounts describe "$SERVICE_ACCOUNT_EMAIL" --project="$PROJECT_ID" >/dev/null 2>&1; then
    print_success "Service account exists: $SERVICE_ACCOUNT_EMAIL"
else
    print_error "Service account not found: $SERVICE_ACCOUNT_EMAIL"
    ((ERRORS++))
fi

# Check IAM roles
print_info "Checking IAM roles..."
REQUIRED_ROLES=(
    "roles/aiplatform.user"
    "roles/storage.objectAdmin"
)

for role in "${REQUIRED_ROLES[@]}"; do
    if gcloud projects get-iam-policy "$PROJECT_ID" --flatten="bindings[].members" --filter="bindings.members:$SERVICE_ACCOUNT_EMAIL AND bindings.role:$role" --format="value(bindings.role)" | grep -q "$role"; then
        print_success "Role granted: $role"
    else
        print_error "Role not granted: $role"
        ((ERRORS++))
    fi
done

# Check GCS bucket
print_info "Checking GCS bucket..."
BUCKET_NAME="${PROJECT_ID}-${BUCKET_SUFFIX}"

if gsutil ls -b "gs://$BUCKET_NAME" >/dev/null 2>&1; then
    print_success "Bucket exists: gs://$BUCKET_NAME"
else
    print_error "Bucket not found: gs://$BUCKET_NAME"
    ((ERRORS++))
fi

# Check local files
print_info "Checking local files..."

if [ -f "service-account-key.json" ]; then
    print_success "Service account key exists"
else
    print_warning "Service account key not found (may be in different location)"
fi

if [ -f ".env.gcp" ]; then
    print_success "Environment config exists"
else
    print_warning "Environment config not found"
fi

# Check Python dependencies
print_info "Checking Python dependencies..."

if python -c "from google.cloud import aiplatform" 2>/dev/null; then
    print_success "google-cloud-aiplatform installed"
else
    print_warning "google-cloud-aiplatform not installed"
    echo "  Install with: pip install google-cloud-aiplatform"
fi

if python -c "from google.cloud import storage" 2>/dev/null; then
    print_success "google-cloud-storage installed"
else
    print_warning "google-cloud-storage not installed"
    echo "  Install with: pip install google-cloud-storage"
fi

# Summary
echo ""
echo "=========================================="
if [ $ERRORS -eq 0 ]; then
    print_success "All checks passed!"
    echo "=========================================="
    echo ""
    echo "Your GCP setup is ready for RAG integration."
    echo ""
    echo "Next steps:"
    echo "  1. Source environment: source .env.gcp"
    echo "  2. Create RAG corpus: python knowledge_base_manager.py"
    echo "  3. Test RAG engine: python vertex_rag.py"
else
    print_error "Found $ERRORS error(s)"
    echo "=========================================="
    echo ""
    echo "Please fix the errors above before proceeding."
    echo "See MANUAL_SETUP.md for detailed instructions."
    exit 1
fi
