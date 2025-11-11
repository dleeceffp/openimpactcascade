#!/bin/bash
#
# Cleanup script for OpenImpactCascade GCP resources
# This script removes all GCP resources created by bootstrap.sh
#
# Usage: ./cleanup.sh PROJECT_ID
#
# ⚠️ WARNING: This will delete all RAG data and cannot be undone!
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

PROJECT_ID=${1:-""}
SERVICE_ACCOUNT_NAME="oic-rarag"
BUCKET_SUFFIX="rarag-kb"

if [ -z "$PROJECT_ID" ]; then
    print_error "Project ID is required"
    echo "Usage: ./cleanup.sh PROJECT_ID"
    exit 1
fi

# Confirmation
print_warning "This will DELETE all RAG resources in project: $PROJECT_ID"
print_warning "This action CANNOT be undone!"
echo ""
read -p "Are you sure? Type 'DELETE' to confirm: " -r
echo

if [ "$REPLY" != "DELETE" ]; then
    print_info "Cleanup cancelled"
    exit 0
fi

print_info "Starting cleanup..."

# Set project
gcloud config set project "$PROJECT_ID"

# Delete GCS bucket
BUCKET_NAME="${PROJECT_ID}-${BUCKET_SUFFIX}"
print_info "Deleting GCS bucket: gs://$BUCKET_NAME"

if gsutil ls -b "gs://$BUCKET_NAME" >/dev/null 2>&1; then
    gsutil -m rm -r "gs://$BUCKET_NAME" || print_warning "Failed to delete bucket"
    print_success "Bucket deleted"
else
    print_info "Bucket does not exist"
fi

# Delete service account
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
print_info "Deleting service account: $SERVICE_ACCOUNT_EMAIL"

if gcloud iam service-accounts describe "$SERVICE_ACCOUNT_EMAIL" --project="$PROJECT_ID" >/dev/null 2>&1; then
    gcloud iam service-accounts delete "$SERVICE_ACCOUNT_EMAIL" --project="$PROJECT_ID" --quiet || print_warning "Failed to delete service account"
    print_success "Service account deleted"
else
    print_info "Service account does not exist"
fi

# Delete local files
print_info "Deleting local files..."

if [ -f "service-account-key.json" ]; then
    rm service-account-key.json
    print_success "Deleted service-account-key.json"
fi

if [ -f ".env.gcp" ]; then
    rm .env.gcp
    print_success "Deleted .env.gcp"
fi

print_success "Cleanup complete!"
print_info "Note: APIs remain enabled. To disable them manually:"
echo "  gcloud services disable aiplatform.googleapis.com --project=$PROJECT_ID"
echo "  gcloud services disable storage-api.googleapis.com --project=$PROJECT_ID"
