#!/bin/bash
# Service Account Setup Script
# Run this from Cloud Shell or your local machine with gcloud configured

set -e

PROJECT_ID="oicsbx"
SA_NAME="rag-uploader"
SA_DISPLAY_NAME="RAG Upload Service Account"
KEY_FILE="${HOME}/rag-uploader-key.json"

echo "=========================================="
echo "Service Account Setup for RAG Upload"
echo "=========================================="
echo ""
echo "Project: ${PROJECT_ID}"
echo "Service Account: ${SA_NAME}"
echo ""

# Set project
echo "Setting project..."
gcloud config set project ${PROJECT_ID}

# Check if service account exists
echo ""
echo "Checking if service account exists..."
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if gcloud iam service-accounts describe ${SA_EMAIL} &>/dev/null; then
    echo "✓ Service account already exists: ${SA_EMAIL}"
else
    echo "Creating service account..."
    gcloud iam service-accounts create ${SA_NAME} \
        --display-name="${SA_DISPLAY_NAME}" \
        --description="Service account for uploading documents to RAG corpus"
    echo "✓ Service account created: ${SA_EMAIL}"
fi

# Grant roles
echo ""
echo "Granting IAM roles..."

# Role 1: Vertex AI User
echo "  - roles/aiplatform.user"
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/aiplatform.user" \
    --quiet

# Role 2: Storage Object Viewer
echo "  - roles/storage.objectViewer"
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.objectViewer" \
    --quiet

echo "✓ IAM roles granted"

# Create key
echo ""
echo "Creating service account key..."
if [ -f "${KEY_FILE}" ]; then
    echo "⚠️  Key file already exists: ${KEY_FILE}"
    read -p "Overwrite? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping key creation."
        KEY_FILE=""
    else
        rm ${KEY_FILE}
    fi
fi

if [ -n "${KEY_FILE}" ]; then
    gcloud iam service-accounts keys create ${KEY_FILE} \
        --iam-account=${SA_EMAIL}
    echo "✓ Key created: ${KEY_FILE}"
    
    # Secure the key file
    chmod 600 ${KEY_FILE}
    echo "✓ Key file permissions set to 600"
fi

# Summary
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Service Account: ${SA_EMAIL}"
echo ""
echo "Granted Roles:"
echo "  - roles/aiplatform.user (for Vertex AI RAG)"
echo "  - roles/storage.objectViewer (for reading GCS files)"
echo ""

if [ -n "${KEY_FILE}" ] && [ -f "${KEY_FILE}" ]; then
    echo "Key File: ${KEY_FILE}"
    echo ""
    echo "Next Steps:"
    echo "1. Transfer key to remote server:"
    echo "   scp ${KEY_FILE} user@remote-server:~/gcp-service-account-key.json"
    echo ""
    echo "2. On remote server, set environment variable:"
    echo "   export GOOGLE_APPLICATION_CREDENTIALS=~/gcp-service-account-key.json"
    echo ""
    echo "3. Test authentication:"
    echo "   python3 test_rag_auth.py --project ${PROJECT_ID} --corpus-id 6917529027641081856"
    echo ""
    echo "⚠️  Security: Keep this key file secure and delete it when no longer needed!"
else
    echo "No new key created."
    echo ""
    echo "To create a key later:"
    echo "  gcloud iam service-accounts keys create ~/key.json --iam-account=${SA_EMAIL}"
fi

echo "=========================================="
