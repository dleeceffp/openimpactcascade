# Canadian Data Residency Configuration

## Overview

All infrastructure bootstrap scripts and RAG integration code have been configured to use **`northamerica-northeast1`** (Montreal, Canada) as the default region to ensure Canadian data residency compliance.

---

## Region Details

### Primary Region
- **Region Code:** `northamerica-northeast1`
- **Location:** Montreal, Quebec, Canada
- **Vertex AI RAG:** ✅ Supported
- **Data Residency:** Canadian data stays in Canada

### Why Montreal?
- ✅ Vertex AI RAG Engine available
- ✅ Canadian data sovereignty
- ✅ Compliance with Canadian privacy laws
- ✅ Lower latency for Canadian users
- ✅ Full GCP service availability

---

## Files Updated

All the following files now default to `northamerica-northeast1`:

### Bootstrap Scripts
- ✅ `bootstrap.sh` - Line 22
- ✅ `bootstrap.ps1` - Line 13

### Terraform Configuration
- ✅ `terraform/variables.tf` - Default region variable
- ✅ `terraform/terraform.tfvars.example` - Example values

### Python Scripts
- ✅ `scripts/create_rag_corpus.py` - All location defaults
- ✅ `scripts/create_corpus_cloudshell.sh` - Default location
- ✅ `../vertex_rag.py` - RAG engine default location
- ✅ `../knowledge_base_manager.py` - KB manager default location

### Documentation
- ✅ `README.md` - Updated examples
- ✅ `MANUAL_SETUP.md` - Updated region references
- ✅ `scripts/README_CORPUS.md` - Updated location lists

---

## Verification

### Check Your Configuration

**Environment Variables:**
```bash
# Should show northamerica-northeast1
echo $GCP_REGION
grep GCP_REGION .env.gcp
```

**GCS Bucket Location:**
```bash
# Check bucket location
gsutil ls -L -b gs://YOUR-PROJECT-ID-rag-kb | grep Location
```

**RAG Corpus Location:**
```bash
# List corpora and check location
python3 scripts/create_rag_corpus.py --project-id YOUR-PROJECT --list-only
```

---

## Usage Examples

### Bootstrap with Default (Montreal)
```bash
# Uses northamerica-northeast1 automatically
./bootstrap.sh oicsbx
```

### Bootstrap with Custom Region
```bash
# Override if needed (not recommended for Canadian data)
./bootstrap.sh oicsbx us-central1
```

### Create RAG Corpus (Montreal)
```bash
# Uses northamerica-northeast1 automatically
python3 scripts/create_rag_corpus.py \
  --project-id oicsbx \
  --display-name risk-assessment-kb
```

### Terraform Apply (Montreal)
```bash
cd terraform
terraform init
terraform apply
# Uses northamerica-northeast1 from variables.tf
```

---

## Data Residency Compliance

### What Stays in Canada

When using `northamerica-northeast1`:

✅ **GCS Bucket Data**
- All knowledge base documents
- Uploaded files
- Backup data

✅ **Vertex AI RAG Corpus**
- Vector embeddings
- Document indices
- Query results

✅ **Compute Resources**
- RAG query processing
- Embedding generation
- Vector search operations

### What May Leave Canada

⚠️ **External API Calls**
- Anthropic Claude API (US-based)
- Web search APIs (if used)
- Third-party services

⚠️ **Control Plane**
- GCP management APIs (global)
- IAM operations (global)
- Logging/monitoring metadata (may be global)

---

## Alternative Canadian Regions

### Other Options

If `northamerica-northeast1` is not suitable:

**northamerica-northeast2** (Toronto)
- ✅ Canadian data residency
- ❌ Vertex AI RAG **NOT** available
- Use for: Storage only

**No other Canadian regions support Vertex AI RAG**

### Recommendation

**Stick with `northamerica-northeast1` (Montreal)** for:
- Canadian data residency
- Full Vertex AI RAG support
- Best balance of features and compliance

---

## Compliance Considerations

### Canadian Privacy Laws

**PIPEDA (Personal Information Protection and Electronic Documents Act)**
- ✅ Data stored in Canada
- ✅ Canadian jurisdiction applies
- ⚠️ Review third-party API usage

**Provincial Privacy Laws**
- Quebec: Law 25
- BC: PIPA
- Alberta: PIPA

### Best Practices

1. **Document Data Flows**
   - Where data is stored
   - Where data is processed
   - Third-party integrations

2. **Review Service Agreements**
   - GCP terms for Canadian regions
   - Anthropic API terms
   - Data processing agreements

3. **Implement Access Controls**
   - Restrict access to Canadian personnel
   - Use VPC Service Controls (optional)
   - Enable audit logging

4. **Regular Audits**
   - Verify bucket locations
   - Check corpus regions
   - Review access logs

---

## Migration from Other Regions

### If You Already Used US Regions

**Step 1: Create New Resources in Montreal**
```bash
# Create new bucket
gsutil mb -l northamerica-northeast1 gs://PROJECT-ID-rag-kb-ca

# Create new corpus
python3 scripts/create_rag_corpus.py \
  --project-id PROJECT-ID \
  --display-name risk-assessment-kb-ca \
  --location northamerica-northeast1
```

**Step 2: Copy Data**
```bash
# Copy bucket data
gsutil -m cp -r gs://OLD-BUCKET/* gs://NEW-BUCKET/

# Re-upload documents to new corpus
python knowledge_base_manager.py
```

**Step 3: Update Configuration**
```bash
# Update .env.gcp
GCP_REGION=northamerica-northeast1
VERTEX_RAG_CORPUS=risk-assessment-kb-ca
VERTEX_RAG_GCS_BUCKET=PROJECT-ID-rag-kb-ca
```

**Step 4: Test**
```bash
# Verify RAG engine
python vertex_rag.py
```

**Step 5: Clean Up Old Resources**
```bash
# Delete old bucket
gsutil -m rm -r gs://OLD-BUCKET

# Delete old corpus (via console or API)
```

---

## Cost Implications

### Regional Pricing

**Montreal vs US Regions:**
- Storage: Similar pricing (~$0.02/GB/month)
- Network egress: Slightly higher to US
- Compute: Similar pricing
- Vertex AI: Same pricing

**Estimated Monthly Cost:**
- Small deployment: $2-5/month
- Medium deployment: $10-20/month
- Large deployment: $50-100/month

**No significant cost difference for Canadian region**

---

## Performance Considerations

### Latency

**From Canada:**
- Montreal: ~5-20ms (excellent)
- US regions: ~30-80ms (good)

**From US:**
- Montreal: ~30-80ms (good)
- US regions: ~5-20ms (excellent)

**Recommendation:** Use Montreal for Canadian users

### Availability

**Montreal Region SLA:**
- Same 99.95% SLA as US regions
- Multiple availability zones
- Redundant infrastructure

---

## Support and Resources

### GCP Documentation
- [Canadian Regions](https://cloud.google.com/about/locations#americas)
- [Vertex AI Locations](https://cloud.google.com/vertex-ai/docs/general/locations)
- [Data Residency](https://cloud.google.com/security/compliance/data-residency)

### Compliance Resources
- [PIPEDA](https://www.priv.gc.ca/en/privacy-topics/privacy-laws-in-canada/the-personal-information-protection-and-electronic-documents-act-pipeda/)
- [Quebec Law 25](https://www.quebec.ca/en/government/ministere/cybersecurite-numerique/law-25)

### Internal Documentation
- `README.md` - Bootstrap overview
- `MANUAL_SETUP.md` - Step-by-step setup
- `../documentation/VERTEX_RAG_INTEGRATION.md` - RAG integration guide

---

## Frequently Asked Questions

### Q: Can I use a different region?

**A:** Yes, but consider:
- Vertex AI RAG availability
- Data residency requirements
- Latency for your users
- Compliance obligations

Override default:
```bash
./bootstrap.sh PROJECT-ID us-central1
```

### Q: Is my data really in Canada?

**A:** Yes, when using `northamerica-northeast1`:
- GCS buckets are in Montreal
- Vertex AI corpus is in Montreal
- Processing happens in Montreal

Verify:
```bash
gsutil ls -L -b gs://YOUR-BUCKET | grep Location
```

### Q: What about Anthropic API calls?

**A:** Anthropic Claude API is US-based:
- API calls go to US servers
- Prompts/responses transit US
- Consider this in your compliance assessment

### Q: Can I use Toronto instead?

**A:** Toronto (`northamerica-northeast2`) does NOT support Vertex AI RAG. You must use Montreal for RAG functionality.

### Q: Does this affect costs?

**A:** Minimal impact:
- Storage costs are similar
- Compute costs are similar
- Network egress to US is slightly higher
- Overall difference: <5%

---

## Summary

✅ **Default Region:** `northamerica-northeast1` (Montreal)  
✅ **Data Residency:** Canadian data stays in Canada  
✅ **RAG Support:** Full Vertex AI RAG Engine available  
✅ **Compliance:** Supports PIPEDA and provincial laws  
✅ **Performance:** Low latency for Canadian users  
✅ **Cost:** Similar to US regions  

**All bootstrap scripts and code now default to Montreal for Canadian data residency.**

---

**Last Updated:** November 2025  
**Status:** Production Ready  
**Region:** northamerica-northeast1 (Montreal, Canada)
