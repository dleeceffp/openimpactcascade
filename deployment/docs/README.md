# Infrastructure Bootstrap for OpenImpactCascade

This directory contains infrastructure-as-code and bootstrap scripts for setting up the GCP project for OpenImpactCascade with Vertex AI RAG integration.

## Contents

- **`bootstrap.sh`** - Main bootstrap script for GCP project setup
- **`terraform/`** - Terraform configurations for infrastructure
- **`scripts/`** - Helper scripts for specific tasks
- **`config/`** - Configuration templates

## Quick Start

### Prerequisites

- GCP account with billing enabled
- `gcloud` CLI installed and authenticated
- Terraform installed (optional, for IaC approach)
- Appropriate GCP permissions (Owner or Editor role)

### Bootstrap a New GCP Project

```bash
# Set your project ID
export PROJECT_ID="your-project-id"

# Run bootstrap script (defaults to northamerica-northeast1 for Canadian data residency)
cd infra
chmod +x bootstrap.sh
./bootstrap.sh $PROJECT_ID
```

This will:
1. Enable required GCP APIs
2. Create service accounts
3. Set up IAM permissions
4. Create GCS buckets
5. Initialize Vertex AI RAG corpus
6. Generate configuration files

### Manual Setup

If you prefer manual setup, follow the steps in `MANUAL_SETUP.md`.

## What Gets Created

### GCP Resources

- **APIs Enabled:**
  - Vertex AI API
  - Cloud Storage API
  - IAM API
  - Cloud Resource Manager API

- **Service Accounts:**
  - `risk-assessment-rag@PROJECT_ID.iam.gserviceaccount.com`
  - Roles: `aiplatform.user`, `storage.objectAdmin`

- **GCS Buckets:**
  - `PROJECT_ID-rag-kb` - Knowledge base document storage
  - `PROJECT_ID-rag-backups` - Backup storage (optional)

- **Vertex AI Resources:**
  - RAG Corpus: `risk-assessment-kb`

### Local Files Created

- `.env.gcp` - Environment variables for GCP
- `service-account-key.json` - Service account credentials
- `terraform.tfvars` - Terraform variables (if using Terraform)

## Cost Estimate

**One-time setup:** Free  
**Ongoing costs:**
- Storage: ~$0.10-1.00/month (depending on knowledge base size)
- RAG queries: ~$0.001 per query
- Estimated monthly: $2-20 depending on usage

## Security Notes

⚠️ **Important:**
- Never commit `service-account-key.json` to version control
- Never commit `.env.gcp` to version control
- Rotate service account keys regularly
- Use least-privilege IAM roles
- Enable audit logging

## Cleanup

To remove all created resources:

```bash
./scripts/cleanup.sh $PROJECT_ID
```

⚠️ **Warning:** This will delete all RAG data and cannot be undone.

## Support

- See `MANUAL_SETUP.md` for detailed manual instructions
- See `TROUBLESHOOTING.md` for common issues
- See main `../QUICKSTART_RAG.md` for application integration
