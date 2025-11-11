# RAG Corpus Creation Scripts

Scripts for creating Vertex AI RAG corpus in GCP Cloud Shell or local environment.

---

## Files

- **`create_rag_corpus.py`** - Python script to create RAG corpus
- **`create_corpus_cloudshell.sh`** - Bash wrapper for Cloud Shell
- **`README_CORPUS.md`** - This file

---

## Quick Start (Cloud Shell)

### 1. Open Cloud Shell

Go to [Google Cloud Console](https://console.cloud.google.com) and click the Cloud Shell icon.

### 2. Upload Scripts

```bash
# Create directory
mkdir -p ~/oic-rag-setup
cd ~/oic-rag-setup

# Upload these files to Cloud Shell:
# - create_rag_corpus.py
# - create_corpus_cloudshell.sh
```

Or clone from repository:
```bash
git clone YOUR_REPO_URL
cd YOUR_REPO/infra/scripts
```

### 3. Make Executable

```bash
chmod +x create_corpus_cloudshell.sh
```

### 4. Run Script

```bash
# With project ID
./create_corpus_cloudshell.sh oicsbx risk-assessment-kb

# Or let it detect project
./create_corpus_cloudshell.sh
```

---

## Usage Options

### Option 1: Cloud Shell Wrapper (Easiest)

```bash
./create_corpus_cloudshell.sh PROJECT_ID [CORPUS_NAME] [LOCATION]
```

**What it does:**
- Checks authentication
- Enables APIs if needed
- Installs dependencies
- Creates corpus
- Verifies creation

**Example:**
```bash
./create_corpus_cloudshell.sh oicsbx risk-assessment-kb us-east4
```

---

### Option 2: Direct Python Script

```bash
python3 create_rag_corpus.py --project-id PROJECT_ID --display-name CORPUS_NAME
```

**Examples:**

**Basic:**
```bash
python3 create_rag_corpus.py \
  --project-id oicsbx \
  --display-name risk-assessment-kb
```

**With custom location:**
```bash
python3 create_rag_corpus.py \
  --project-id oicsbx \
  --display-name risk-assessment-kb \
  --location us-central1
```

**With description:**
```bash
python3 create_rag_corpus.py \
  --project-id oicsbx \
  --display-name risk-assessment-kb \
  --description "Knowledge base for cybersecurity risk assessment"
```

**With custom embedding model:**
```bash
python3 create_rag_corpus.py \
  --project-id oicsbx \
  --display-name risk-assessment-kb \
  --embedding-model text-embedding-004
```

**List existing corpora:**
```bash
python3 create_rag_corpus.py \
  --project-id oicsbx \
  --list-only
```

**Create and verify:**
```bash
python3 create_rag_corpus.py \
  --project-id oicsbx \
  --display-name risk-assessment-kb \
  --verify
```

---

## Supported Locations

RAG Engine is available in these regions:

- **us-central1** (Iowa)
- **us-east4** (Virginia) - Default
- **europe-west1** (Belgium)
- **asia-southeast1** (Singapore)

Choose the location closest to your users for best performance.

---

## Prerequisites

### Cloud Shell (Automatic)
- ✅ Python 3 (pre-installed)
- ✅ gcloud CLI (pre-installed)
- ✅ Authentication (automatic)

### Local Environment
- Python 3.7+
- gcloud CLI installed
- Authenticated: `gcloud auth application-default login`

### GCP Requirements
- Project with billing enabled
- Vertex AI API enabled (script can enable it)
- IAM role: `roles/aiplatform.user`

---

## Installation (Local)

```bash
# Install Python package
pip install google-cloud-aiplatform

# Authenticate
gcloud auth application-default login

# Set project
gcloud config set project YOUR_PROJECT_ID
```

---

## Command-Line Arguments

### Required
- `--project-id` - GCP project ID

### Optional
- `--display-name` - Corpus display name (required for creation)
- `--location` - GCP region (default: us-east4)
- `--description` - Corpus description
- `--embedding-model` - Embedding model (default: text-embedding-005)
- `--list-only` - Only list existing corpora
- `--verify` - Verify corpus after creation

---

## Output

### Success
```
============================================================
  Vertex AI RAG Corpus Creation
  OpenImpactCascade Risk Assessment Platform
============================================================

Initializing Vertex AI...
  Project: oicsbx
  Location: us-east4
✓ Vertex AI initialized

Listing existing RAG corpora in oicsbx...
  No existing corpora found

Creating RAG Corpus...
  Display Name: risk-assessment-kb
  Embedding Model: text-embedding-005 (default)

✓ Successfully created RAG Corpus!
  Corpus Name: projects/123456789/locations/us-east4/ragCorpora/1234567890
  Resource ID: 1234567890

============================================================
  Next Steps
============================================================

1. Update your .env.gcp file:
   VERTEX_RAG_CORPUS=risk-assessment-kb
   GCP_REGION=us-east4

2. Upload documents to the corpus:
   python knowledge_base_manager.py

3. Test RAG engine:
   python vertex_rag.py

4. Integrate into application:
   See documentation/VERTEX_RAG_INTEGRATION.md

============================================================
✓ Corpus creation complete!
============================================================
```

---

## Troubleshooting

### "ERROR: vertexai library not installed"

**Cloud Shell:**
```bash
pip3 install --user google-cloud-aiplatform
```

**Local:**
```bash
pip install google-cloud-aiplatform
```

---

### "Failed to initialize Vertex AI"

**Check project ID:**
```bash
gcloud projects list
```

**Enable API:**
```bash
gcloud services enable aiplatform.googleapis.com --project=YOUR_PROJECT_ID
```

**Check authentication:**
```bash
gcloud auth list
gcloud auth application-default login
```

---

### "Location not supported"

Use one of the supported locations:
- us-central1
- us-east4
- europe-west1
- asia-southeast1

```bash
python3 create_rag_corpus.py \
  --project-id oicsbx \
  --display-name risk-assessment-kb \
  --location us-central1
```

---

### "Permission denied"

**Check IAM role:**
```bash
gcloud projects get-iam-policy YOUR_PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:YOUR_EMAIL"
```

**Grant role:**
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="user:YOUR_EMAIL" \
  --role="roles/aiplatform.user"
```

---

### "Corpus already exists"

**List existing corpora:**
```bash
python3 create_rag_corpus.py --project-id oicsbx --list-only
```

**Use different name:**
```bash
python3 create_rag_corpus.py \
  --project-id oicsbx \
  --display-name risk-assessment-kb-v2
```

---

## Integration with Bootstrap

These scripts complement the main bootstrap process:

### After Bootstrap
```bash
# 1. Run bootstrap (creates service account, bucket, etc.)
./bootstrap.sh oicsbx

# 2. Create RAG corpus
./scripts/create_corpus_cloudshell.sh oicsbx risk-assessment-kb

# 3. Verify setup
./scripts/verify-setup.sh oicsbx
```

---

## Embedding Models

### Available Models

- **text-embedding-005** (default) - Latest, best performance
- **text-embedding-004** - Previous version
- **textembedding-gecko** - Legacy model

### Choosing a Model

**Default (recommended):**
```bash
python3 create_rag_corpus.py --project-id oicsbx --display-name my-corpus
```

**Specific model:**
```bash
python3 create_rag_corpus.py \
  --project-id oicsbx \
  --display-name my-corpus \
  --embedding-model text-embedding-004
```

---

## Next Steps After Creation

### 1. Update Configuration

Add to `.env.gcp`:
```bash
VERTEX_RAG_CORPUS=risk-assessment-kb
GCP_REGION=us-east4
```

### 2. Upload Documents

```bash
cd ../..
python knowledge_base_manager.py
```

### 3. Test RAG Engine

```bash
python vertex_rag.py
```

### 4. Integrate into Application

See `documentation/VERTEX_RAG_INTEGRATION.md`

---

## Cost Information

### Corpus Creation
- **One-time:** Free

### Ongoing Costs
- **Storage:** ~$0.10/GB/month
- **Embeddings:** ~$0.025 per 1,000 pages
- **Queries:** ~$0.001 per query

### Example Monthly Cost
- 1 GB knowledge base: $0.10
- 10,000 queries: $10.00
- **Total:** ~$10.10/month

---

## Advanced Usage

### Custom Vector Database

```python
from vertexai import rag

corpus = rag.RagCorpus.create(
    display_name="my-corpus",
    embedding_model_config=rag.EmbeddingModelConfig(),
    vector_db_config=rag.RagVectorDbConfig(
        # Configure custom vector DB
        # See Vertex AI documentation
    )
)
```

### Programmatic Creation

```python
from vertexai import rag
import vertexai

# Initialize
vertexai.init(project="oicsbx", location="us-east4")

# Create corpus
corpus = rag.RagCorpus.create(
    display_name="risk-assessment-kb",
    description="Knowledge base for risk assessment",
    embedding_model_config=rag.EmbeddingModelConfig()
)

print(f"Created: {corpus.name}")
```

---

## Support

- **Script issues:** Check this README
- **GCP issues:** See [Vertex AI RAG Documentation](https://cloud.google.com/vertex-ai/docs/generative-ai/rag-overview)
- **Integration:** See `../../documentation/VERTEX_RAG_INTEGRATION.md`

---

**Ready to create your corpus!** Choose your method above and follow the instructions.
