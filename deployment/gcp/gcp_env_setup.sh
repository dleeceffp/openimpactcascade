#!/bin/bash
# GCP Environment Setup for Remote Linux Server
# Source this file: source gcp_env_setup.sh

# =============================================================================
# PROJECT CONFIGURATION
# =============================================================================

export PROJECT_ID="oicsbx"
export LOCATION="northamerica-northeast1"
export CORPUS_ID="6917529027641081856"

# Full corpus name (for API calls)
export CORPUS_NAME="projects/${PROJECT_ID}/locations/${LOCATION}/ragCorpora/${CORPUS_ID}"

# API endpoints
export API_BASE="https://${LOCATION}-aiplatform.googleapis.com/v1"

# =============================================================================
# CORPUS DETAILS
# =============================================================================

export CORPUS_DISPLAY_NAME="oic-rarag-kb"
export CORPUS_DESCRIPTION="Knowledge base for OpenImpactCascade risk assessment platform"

# =============================================================================
# AUTHENTICATION
# =============================================================================

# Option 1: Service Account Key File (RECOMMENDED for remote servers)
# Download from: https://console.cloud.google.com/iam-admin/serviceaccounts
export GOOGLE_APPLICATION_CREDENTIALS="${HOME}/gcp-service-account-key.json"

# Option 2: User credentials (if using gcloud auth application-default login)
# export GOOGLE_APPLICATION_CREDENTIALS="${HOME}/.config/gcloud/application_default_credentials.json"

# =============================================================================
# GCS CONFIGURATION
# =============================================================================

# Your GCS bucket (adjust as needed)
export GCS_BUCKET="dev-rarag-kb"
export METADATA_DIR="./processed_metadata"

# =============================================================================
# SCRIPT CONFIGURATION
# =============================================================================

# Upload batch size
export BATCH_SIZE="10"

# Delay between batches (seconds)
export BATCH_DELAY="2.0"

# =============================================================================
# PYTHON CONFIGURATION
# =============================================================================

# Ensure Python uses UTF-8
export PYTHONIOENCODING="utf-8"

# Optional: Use virtual environment
# export VIRTUAL_ENV="${HOME}/venv/gcp"
# export PATH="${VIRTUAL_ENV}/bin:${PATH}"

# =============================================================================
# LOGGING
# =============================================================================

export LOG_LEVEL="INFO"

# =============================================================================
# VALIDATION
# =============================================================================

echo "=========================================="
echo "GCP Environment Configuration"
echo "=========================================="
echo "Project ID:       ${PROJECT_ID}"
echo "Location:         ${LOCATION}"
echo "Corpus ID:        ${CORPUS_ID}"
echo "Corpus Name:      ${CORPUS_DISPLAY_NAME}"
echo "Metadata Dir:     ${METADATA_DIR}"
echo ""
echo "Authentication:"
if [ -f "${GOOGLE_APPLICATION_CREDENTIALS}" ]; then
    echo "  ✓ Credentials file found: ${GOOGLE_APPLICATION_CREDENTIALS}"
else
    echo "  ✗ Credentials file NOT found: ${GOOGLE_APPLICATION_CREDENTIALS}"
    echo "  Please download service account key or run: gcloud auth application-default login"
fi
echo ""
echo "Environment loaded. Ready to use scripts."
echo "=========================================="

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

# Quick test function
test_gcp_access() {
    echo "Testing GCP access..."
    python - <<EOF
import os
import sys
from google.auth import default
from google.cloud import storage

try:
    credentials, project = default()
    print(f"✓ Authentication successful")
    print(f"  Project: {project}")
    print(f"  Credentials type: {type(credentials).__name__}")
    
    # Test storage access
    client = storage.Client(project="${PROJECT_ID}")
    buckets = list(client.list_buckets(max_results=1))
    print(f"✓ Storage access confirmed")
    
    print("✓ All checks passed!")
    sys.exit(0)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
EOF
}

# Quick upload command
upload_rag_docs() {
    python gcs_to_rag_upload_fixed.py \
        --corpus oic-rarag-kb \
        --project ${PROJECT_ID} \
        --location ${LOCATION} \
        --metadata-dir ${METADATA_DIR} \
        --batch-size ${BATCH_SIZE} \
        --delay ${BATCH_DELAY}
}

# Quick test command
test_rag_access() {
    python test_rag_auth.py \
        --project ${PROJECT_ID} \
        --location ${LOCATION} \
        --corpus-id ${CORPUS_ID}
}

# Export functions
export -f test_gcp_access
export -f upload_rag_docs
export -f test_rag_access
