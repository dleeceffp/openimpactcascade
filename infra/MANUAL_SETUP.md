# Manual GCP Setup Guide

If you prefer to set up GCP resources manually instead of using the bootstrap script, follow these steps.

---

## Prerequisites

- GCP account with billing enabled
- `gcloud` CLI installed and authenticated
- Appropriate GCP permissions (Project Editor or Owner)

---

## Step 1: Set Your Project

```bash
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID
```

---

## Step 2: Enable Required APIs

```bash
# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com --project=$PROJECT_ID

# Enable Cloud Storage API
gcloud services enable storage-api.googleapis.com --project=$PROJECT_ID

# Enable IAM API
gcloud services enable iam.googleapis.com --project=$PROJECT_ID

# Enable Cloud Resource Manager API
gcloud services enable cloudresourcemanager.googleapis.com --project=$PROJECT_ID
```

**Verify:**
```bash
gcloud services list --enabled --project=$PROJECT_ID | grep -E "aiplatform|storage-api|iam"
```

---

## Step 3: Create Service Account

```bash
# Create service account
gcloud iam service-accounts create risk-assessment-rag \
    --display-name="Risk Assessment RAG Service Account" \
    --project=$PROJECT_ID

# Verify creation
gcloud iam service-accounts list --project=$PROJECT_ID
```

---

## Step 4: Grant IAM Permissions

```bash
# Set service account email
export SA_EMAIL="risk-assessment-rag@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant Vertex AI User role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/aiplatform.user"

# Grant Storage Object Admin role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/storage.objectAdmin"
```

**Verify:**
```bash
gcloud projects get-iam-policy $PROJECT_ID \
    --flatten="bindings[].members" \
    --filter="bindings.members:$SA_EMAIL"
```

---

## Step 5: Create Service Account Key

```bash
# Create key file
gcloud iam service-accounts keys create service-account-key.json \
    --iam-account=$SA_EMAIL \
    --project=$PROJECT_ID

# Verify key created
ls -la service-account-key.json
```

**⚠️ Security Note:** Keep this file secure and never commit to version control!

---

## Step 6: Create GCS Bucket

```bash
# Set bucket name
export BUCKET_NAME="${PROJECT_ID}-rag-kb"
export REGION="northamerica-northeast1"  # Montreal, Canada for data residency

# Create bucket
gsutil mb -l $REGION -p $PROJECT_ID gs://$BUCKET_NAME

# Verify bucket created
gsutil ls -b gs://$BUCKET_NAME
```

**Optional - Set Lifecycle Policy:**

Create `lifecycle.json`:
```json
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
```

Apply policy:
```bash
gsutil lifecycle set lifecycle.json gs://$BUCKET_NAME
```

---

## Step 7: Set Bucket Permissions

```bash
# Grant service account access to bucket
gsutil iam ch serviceAccount:$SA_EMAIL:objectAdmin gs://$BUCKET_NAME
```

---

## Step 8: Create Environment Configuration

Create `.env.gcp` file:

```bash
cat > .env.gcp <<EOF
# GCP Configuration for OpenImpactCascade
# DO NOT COMMIT THIS FILE TO VERSION CONTROL

# GCP Project Configuration
GOOGLE_CLOUD_PROJECT=$PROJECT_ID
GCP_REGION=$REGION

# Vertex AI RAG Configuration
VERTEX_RAG_CORPUS=risk-assessment-kb
VERTEX_RAG_GCS_BUCKET=$BUCKET_NAME

# Service Account
GOOGLE_APPLICATION_CREDENTIALS=$(pwd)/service-account-key.json

# Application Configuration
# ANTHROPIC_API_KEY=your-anthropic-key-here
# SECRET_KEY=your-flask-secret-here
EOF
```

---

## Step 9: Update .gitignore

Add to `.gitignore`:

```bash
# GCP Infrastructure
infra/service-account-key.json
infra/.env.gcp
infra/terraform.tfstate
infra/terraform.tfstate.backup
infra/.terraform/
```

---

## Step 10: Verify Setup

```bash
# Source environment variables
source .env.gcp

# Test gcloud authentication
gcloud auth list

# Test service account
gcloud auth activate-service-account --key-file=$GOOGLE_APPLICATION_CREDENTIALS

# Test bucket access
gsutil ls gs://$BUCKET_NAME

# Test Vertex AI API
gcloud ai models list --region=$REGION --project=$PROJECT_ID
```

---

## Step 11: Initialize Python Environment

```bash
# Navigate to project root
cd ..

# Install dependencies
pip install -r requirements_rag.txt

# Test imports
python -c "from google.cloud import aiplatform; print('✅ Vertex AI SDK installed')"
python -c "from google.cloud import storage; print('✅ Storage SDK installed')"
```

---

## Step 12: Create RAG Corpus

```bash
# Create corpus using Python
python -c "
from knowledge_base_manager import KnowledgeBaseManager

kb = KnowledgeBaseManager(
    project_id='$PROJECT_ID',
    location='$REGION'
)

corpus_name = kb.create_rag_corpus(
    display_name='risk-assessment-kb',
    description='Knowledge base for cybersecurity risk assessment'
)

print(f'✅ Created corpus: {corpus_name}')
"
```

---

## Step 13: Test RAG Engine

```bash
# Test RAG engine
python vertex_rag.py
```

Expected output:
```
=== Vertex AI RAG Engine Test ===

RAG Engine Status:
  enabled: True
  vertex_ai_available: True
  project_id: your-project-id
  location: us-central1
  rag_corpus: risk-assessment-kb
  fallback_enabled: True

✅ RAG engine is enabled and ready
```

---

## Verification Checklist

- [ ] GCP project set and accessible
- [ ] All required APIs enabled
- [ ] Service account created
- [ ] IAM roles granted
- [ ] Service account key downloaded
- [ ] GCS bucket created
- [ ] Bucket permissions set
- [ ] Environment file created
- [ ] .gitignore updated
- [ ] Python dependencies installed
- [ ] RAG corpus created
- [ ] RAG engine test passes

---

## Troubleshooting

### "Permission denied" errors

Check IAM roles:
```bash
gcloud projects get-iam-policy $PROJECT_ID \
    --flatten="bindings[].members" \
    --filter="bindings.members:$SA_EMAIL"
```

### "API not enabled" errors

Re-enable APIs:
```bash
gcloud services enable aiplatform.googleapis.com --project=$PROJECT_ID
```

### "Bucket already exists" errors

Choose a different bucket name:
```bash
export BUCKET_NAME="${PROJECT_ID}-rag-kb-$(date +%s)"
```

### "Service account key not found" errors

Check file path:
```bash
ls -la service-account-key.json
echo $GOOGLE_APPLICATION_CREDENTIALS
```

### Python import errors

Reinstall dependencies:
```bash
pip install --upgrade google-cloud-aiplatform google-cloud-storage
```

---

## Cost Monitoring

Set up billing alerts:

```bash
# Create budget alert (requires billing account ID)
gcloud billing budgets create \
    --billing-account=YOUR_BILLING_ACCOUNT_ID \
    --display-name="RAG Monthly Budget" \
    --budget-amount=20 \
    --threshold-rule=percent=50 \
    --threshold-rule=percent=90 \
    --threshold-rule=percent=100
```

---

## Next Steps

1. **Populate Knowledge Base**
   - See `../documentation/VERTEX_RAG_INTEGRATION.md`
   - Run `python knowledge_base_manager.py`

2. **Test Integration**
   - Generate a questionnaire with RAG
   - Test chat assistance with RAG

3. **Deploy Application**
   - See `../QUICKSTART_RAG.md`
   - Follow deployment guide

---

## Cleanup (Optional)

To remove all resources:

```bash
# Delete service account
gcloud iam service-accounts delete $SA_EMAIL --project=$PROJECT_ID

# Delete bucket
gsutil -m rm -r gs://$BUCKET_NAME

# Delete local files
rm service-account-key.json .env.gcp

# Disable APIs (optional)
gcloud services disable aiplatform.googleapis.com --project=$PROJECT_ID
```

⚠️ **Warning:** This will delete all data and cannot be undone!

---

**Manual setup complete!** You can now proceed with populating the knowledge base and integrating RAG into the application.
