# Quick Start: Vertex AI RAG Integration

This guide gets you up and running with RAG-powered risk assessment in 15 minutes.

---

## Prerequisites

- ✅ Existing OpenImpactCascade installation working
- ✅ GCP account with billing enabled
- ✅ `gcloud` CLI installed and configured

---

## Step 1: Install Dependencies (2 minutes)

```bash
cd c:\projects\oicdevanthropic\OIC_SBX

# Install RAG dependencies
pip install -r requirements_rag.txt

# Verify installation
python -c "from google.cloud import aiplatform; print('✅ Vertex AI installed')"
```

---

## Step 2: GCP Setup (5 minutes)

### Enable APIs

```bash
# Set your project
export PROJECT_ID="your-gcp-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable storage-api.googleapis.com
```

### Create Service Account

```bash
# Create service account
gcloud iam service-accounts create risk-assessment-rag \
    --display-name="Risk Assessment RAG Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:risk-assessment-rag@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:risk-assessment-rag@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# Create and download key
gcloud iam service-accounts keys create ~/rag-service-account-key.json \
    --iam-account=risk-assessment-rag@$PROJECT_ID.iam.gserviceaccount.com
```

### Create GCS Bucket

```bash
# Create bucket for RAG documents
gsutil mb -l us-central1 gs://$PROJECT_ID-rag-kb

# Verify
gsutil ls gs://$PROJECT_ID-rag-kb
```

---

## Step 3: Configure Environment (1 minute)

Add to your `.env` file:

```bash
# Existing configuration
ANTHROPIC_API_KEY=your-anthropic-key
SECRET_KEY=your-flask-secret

# NEW: RAG configuration
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
VERTEX_RAG_CORPUS=risk-assessment-kb
VERTEX_RAG_GCS_BUCKET=your-project-id-rag-kb
GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\rag-service-account-key.json
```

Or export directly:

```bash
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
export VERTEX_RAG_CORPUS="risk-assessment-kb"
export VERTEX_RAG_GCS_BUCKET="your-project-id-rag-kb"
export GOOGLE_APPLICATION_CREDENTIALS="~/rag-service-account-key.json"
```

---

## Step 4: Create Knowledge Base Structure (2 minutes)

```bash
# Create directory structure
python knowledge_base_manager.py
```

This creates:
```
knowledge_base/
├── threat_intelligence/
├── mitre_attack/
├── industry_reports/
├── compliance/
├── best_practices/
├── case_studies/
└── benchmarks/
```

---

## Step 5: Populate Knowledge Base (5 minutes)

### Option A: Quick Test with Sample Documents

```bash
# Create sample documents for testing
mkdir -p knowledge_base/threat_intelligence/cisa_advisories

# Download a sample CISA advisory
curl -o knowledge_base/threat_intelligence/cisa_advisories/aa24-249a.pdf \
  https://www.cisa.gov/sites/default/files/2024-09/aa24-249a.pdf

# Create sample MITRE ATT&CK document
cat > knowledge_base/mitre_attack/techniques/t1486.md << 'EOF'
# T1486: Data Encrypted for Impact

## Description
Adversaries may encrypt data on target systems or on large numbers of systems 
in a network to interrupt availability to system and network resources.

## Industries Affected
- Healthcare: 45% of ransomware incidents
- Finance: 32% of ransomware incidents
- Manufacturing: 28% of ransomware incidents

## Regional Trends
- North America: Highest volume of attacks
- Europe: Increasing sophistication
- Asia-Pacific: Growing threat landscape

## Mitigation
- Implement backup and recovery procedures
- Use application whitelisting
- Deploy endpoint detection and response (EDR)
EOF
```

### Option B: Full Knowledge Base (Do Later)

See `documentation/VERTEX_RAG_INTEGRATION.md` for comprehensive setup.

---

## Step 6: Create RAG Corpus (2 minutes)

```python
# Run this Python script
from knowledge_base_manager import KnowledgeBaseManager

# Initialize
kb = KnowledgeBaseManager(
    project_id="your-gcp-project-id",
    location="us-central1"
)

# Create corpus
corpus_name = kb.create_rag_corpus(
    display_name="Risk Assessment Knowledge Base",
    description="Curated knowledge base for cybersecurity risk assessment"
)

print(f"✅ Created corpus: {corpus_name}")

# Upload sample documents
kb.bulk_upload_directory(
    directory="./knowledge_base/threat_intelligence",
    document_type="threat_intelligence"
)

kb.bulk_upload_directory(
    directory="./knowledge_base/mitre_attack",
    document_type="mitre_attack"
)

print("✅ Knowledge base populated")
```

Or run the test script:

```bash
python -c "
from knowledge_base_manager import KnowledgeBaseManager
kb = KnowledgeBaseManager()
corpus = kb.create_rag_corpus('Risk Assessment KB', 'Test corpus')
print(f'Created: {corpus}')
"
```

---

## Step 7: Test RAG Integration (2 minutes)

### Test RAG Engine

```bash
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

Testing risk identification context retrieval...
Retrieved 0 contexts

Testing coaching context retrieval...
Retrieved 0 contexts

=== Test Complete ===
```

### Test with Example Integration

```bash
python ai_question_generator_rag_example.py
```

This demonstrates how RAG context is retrieved and formatted.

---

## Step 8: Verify Integration (1 minute)

```bash
# Start Flask app
python flask_app_chat.py

# In another terminal, test health endpoint
curl http://localhost:8080/health

# Check RAG status
python -c "
from vertex_rag import get_rag_engine
rag = get_rag_engine()
print(rag.get_status())
"
```

---

## Next Steps

### Immediate (Today)

1. ✅ Test questionnaire generation with RAG
2. ✅ Test chat assistance with RAG
3. ✅ Monitor logs for RAG queries

### Short-term (This Week)

1. 📚 Add more documents to knowledge base
2. 🔍 Review RAG retrieval quality
3. 📊 Monitor costs and performance

### Long-term (This Month)

1. 🎯 Integrate RAG into production `ai_question_generator.py`
2. 🎯 Integrate RAG into production `flask_app_chat.py`
3. 🎯 Set up automated knowledge base updates
4. 🎯 Implement monitoring dashboard

---

## Troubleshooting

### "Vertex AI not available"

```bash
# Reinstall dependencies
pip install --upgrade google-cloud-aiplatform google-cloud-storage

# Verify
python -c "from google.cloud import aiplatform; print('OK')"
```

### "Authentication failed"

```bash
# Check credentials
echo $GOOGLE_APPLICATION_CREDENTIALS
cat $GOOGLE_APPLICATION_CREDENTIALS

# Re-authenticate
gcloud auth application-default login
```

### "RAG corpus not found"

```bash
# Verify corpus name
echo $VERTEX_RAG_CORPUS

# List corpora (if API supports)
# gcloud ai rag-corpora list
```

### "No contexts retrieved"

- Verify documents uploaded to corpus
- Check metadata filters in query
- Review query formulation
- Ensure corpus has been indexed (may take a few minutes)

---

## Cost Estimate

**For testing/development:**
- Storage: ~$0.10/month (1 GB)
- Queries: ~$0.10/month (100 queries)
- **Total: ~$0.20/month**

**For production (1000 users):**
- Storage: ~$1/month (10 GB)
- Queries: ~$10/month (10,000 queries)
- **Total: ~$11/month**

---

## Support

- 📖 Full documentation: `documentation/VERTEX_RAG_INTEGRATION.md`
- 💻 Code examples: `ai_question_generator_rag_example.py`
- 🔧 RAG engine: `vertex_rag.py`
- 📦 Knowledge base: `knowledge_base_manager.py`

---

**Ready to go!** Your risk assessment platform now has RAG-powered grounding context.

Test it by generating a questionnaire and asking the chat assistant questions. You should see more accurate, grounded responses based on your knowledge base.
