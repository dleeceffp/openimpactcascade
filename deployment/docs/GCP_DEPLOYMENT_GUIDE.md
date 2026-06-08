# GCP Deployment Guide (File-Based Corpus)

This guide walks through creating the required GCP project and setting up the file-based corpus structure inside a GCP bucket.

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
# Enable Cloud Storage API
gcloud services enable storage-api.googleapis.com --project=$PROJECT_ID

# Enable IAM API
gcloud services enable iam.googleapis.com --project=$PROJECT_ID

# Enable Cloud Resource Manager API
gcloud services enable cloudresourcemanager.googleapis.com --project=$PROJECT_ID
```

**Verify:**
```bash
gcloud services list --enabled --project=$PROJECT_ID | grep -E "storage-api|iam"
```

---

## Step 3: Create Service Account

```bash
# Create service account
gcloud iam service-accounts create risk-assessment-sa \
    --display-name="Risk Assessment Service Account" \
    --project=$PROJECT_ID

# Verify creation
gcloud iam service-accounts list --project=$PROJECT_ID
```

---

## Step 4: Grant IAM Permissions

```bash
# Set service account email
export SA_EMAIL="risk-assessment-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant Storage Object Admin role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/storage.objectAdmin"
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

## Step 6: Create GCS Bucket and Corpus File Structure

The File-Based Corpus utilizes standard cloud storage combined with Markdown documents and an `_index.json` registry.

```bash
# Set bucket name
export CORPUS_BUCKET_NAME="${PROJECT_ID}-corpus"
export REGION="northamerica-northeast1"  # Montreal, Canada for data residency

# Create bucket
gsutil mb -l $REGION -p $PROJECT_ID gs://$CORPUS_BUCKET_NAME

# Create the folder structure inside the bucket
gsutil cp /dev/null gs://$CORPUS_BUCKET_NAME/corpus/frameworks/
gsutil cp /dev/null gs://$CORPUS_BUCKET_NAME/corpus/advisories/
gsutil cp /dev/null gs://$CORPUS_BUCKET_NAME/corpus/attack/
gsutil cp /dev/null gs://$CORPUS_BUCKET_NAME/corpus/industry/
gsutil cp /dev/null gs://$CORPUS_BUCKET_NAME/corpus/original/

# Verify bucket created and structure defined
gsutil ls -r gs://$CORPUS_BUCKET_NAME/
```

*Note: Since the directories are currently empty, the application will default to intelligent web search to fill knowledge gaps.*

---

## Step 7: Create Environment Configuration

Create `.env.gcp` file:

```bash
cat > .env.gcp <<EOF
# GCP Configuration for OpenImpactCascade
# DO NOT COMMIT THIS FILE TO VERSION CONTROL

# GCP Project Configuration
GOOGLE_CLOUD_PROJECT=$PROJECT_ID
GCP_REGION=$REGION

# Corpus Configuration
CORPUS_BUCKET_NAME=$CORPUS_BUCKET_NAME

# Service Account
GOOGLE_APPLICATION_CREDENTIALS=$(pwd)/service-account-key.json

# Application Configuration
# ANTHROPIC_API_KEY=your-anthropic-key-here
# SECRET_KEY=your-flask-secret-here
EOF
```

---

## Step 8: Update .gitignore

Add to `.gitignore`:

```bash
# GCP Infrastructure
infra/service-account-key.json
infra/.env.gcp
```

---

## Step 9: Verify Setup

```bash
# Source environment variables
source .env.gcp

# Test gcloud authentication
gcloud auth list

# Test service account
gcloud auth activate-service-account --key-file=$GOOGLE_APPLICATION_CREDENTIALS

# Test bucket access
gsutil ls gs://$CORPUS_BUCKET_NAME/corpus/
```

---

## Next Steps

1. **Populate Knowledge Base**
   - Place your Markdown files with YAML frontmatter in the `corpus/` subdirectories.
   - Run the index builder to generate `_index.json`.

2. **Deploy Application**
   - Follow standard deployment instructions using Docker and Cloud Run.
