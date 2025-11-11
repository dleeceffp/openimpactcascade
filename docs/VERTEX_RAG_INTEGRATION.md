# Vertex AI RAG Engine Integration Guide

## Overview

This document describes the integration of GCP Vertex AI RAG (Retrieval-Augmented Generation) engine into the OpenImpactCascade risk assessment platform.

**Purpose**: Provide grounding context from a curated knowledge base for:
1. **Preliminary risk identification** during questionnaire generation
2. **Risk analysis coaching** during chat assistance

---

## Architecture

### High-Level Flow

```
User Input (Industry + Region)
         ↓
    ┌────────────────────────────┐
    │ AI Question Generator      │
    │ (ai_question_generator.py) │
    └────────┬───────────────────┘
             │
             ├─→ Vertex AI RAG Engine
             │   └─→ Knowledge Base Query
             │       ├─ Threat Intelligence
             │       ├─ MITRE ATT&CK Data
             │       ├─ Industry Reports
             │       └─ Compliance Docs
             │
             ├─→ Retrieved Context
             │   (Grounding Information)
             │
             ├─→ Claude Sonnet 4 API
             │   (with RAG context in prompt)
             │
             └─→ Generated Questionnaire
```

### Components

| Component | File | Purpose |
|-----------|------|---------|
| RAG Engine | `vertex_rag.py` | Core RAG integration |
| Knowledge Base Manager | `knowledge_base_manager.py` | Upload/manage documents |
| AI Generator (Enhanced) | `ai_question_generator.py` | Uses RAG for grounding |
| Chat Assistant (Enhanced) | `flask_app_chat.py` | Uses RAG for coaching |

---

## Setup Instructions

### 1. Prerequisites

**GCP Requirements:**
- GCP project with Vertex AI API enabled
- Service account with permissions:
  - `aiplatform.ragCorpora.create`
  - `aiplatform.ragCorpora.get`
  - `aiplatform.ragFiles.import`
  - `storage.objects.create`
  - `storage.objects.get`

**Python Dependencies:**
```bash
pip install google-cloud-aiplatform google-cloud-storage
```

### 2. Environment Configuration

Add to `.env` or export:

```bash
# GCP Configuration
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
export VERTEX_RAG_CORPUS="risk-assessment-kb"
export VERTEX_RAG_GCS_BUCKET="your-rag-bucket"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"

# Existing Anthropic Configuration
export ANTHROPIC_API_KEY="your-anthropic-key"
export SECRET_KEY="your-flask-secret"
```

### 3. Create RAG Corpus

```python
from knowledge_base_manager import KnowledgeBaseManager

# Initialize manager
kb_manager = KnowledgeBaseManager(
    project_id="your-project-id",
    location="us-central1"
)

# Create corpus
corpus_name = kb_manager.create_rag_corpus(
    display_name="Risk Assessment Knowledge Base",
    description="Curated knowledge base for cybersecurity risk assessment"
)

print(f"Created corpus: {corpus_name}")
```

### 4. Populate Knowledge Base

**Option A: Bulk Upload Directory**

```python
# Upload threat intelligence documents
kb_manager.bulk_upload_directory(
    directory="./knowledge_base/threat_intelligence",
    document_type="threat_intelligence"
)

# Upload MITRE ATT&CK data
kb_manager.bulk_upload_directory(
    directory="./knowledge_base/mitre_attack",
    document_type="mitre_attack"
)

# Upload industry reports
kb_manager.bulk_upload_directory(
    directory="./knowledge_base/industry_reports",
    document_type="benchmarks"
)
```

**Option B: Individual Document Upload**

```python
# Upload specific document with metadata
kb_manager.upload_document(
    file_path="./docs/cisa_aa24_249a.pdf",
    document_type="threat_intelligence",
    metadata={
        "industry": "Healthcare",
        "region": "United States",
        "source": "CISA",
        "date": "2024-09-05"
    }
)
```

---

## Knowledge Base Structure

### Recommended Directory Organization

```
knowledge_base/
├── threat_intelligence/
│   ├── cisa_advisories/          # CISA alerts and advisories
│   ├── cert_alerts/               # Regional CERT alerts
│   └── vendor_reports/            # Threat vendor reports
├── mitre_attack/
│   ├── techniques/                # ATT&CK technique descriptions
│   ├── groups/                    # Threat actor profiles
│   └── software/                  # Malware and tool descriptions
├── industry_reports/
│   ├── verizon_dbir/             # Verizon Data Breach Reports
│   ├── ibm_breach_cost/          # IBM Cost of Data Breach
│   └── sector_specific/          # Industry-specific reports
├── compliance/
│   ├── gdpr/                     # GDPR guidance
│   ├── hipaa/                    # HIPAA requirements
│   ├── pci_dss/                  # PCI-DSS standards
│   └── regional/                 # Regional regulations
├── best_practices/
│   ├── nist/                     # NIST frameworks
│   ├── cis/                      # CIS benchmarks
│   └── industry_guides/          # Industry best practices
├── case_studies/
│   ├── incidents/                # Real incident reports
│   └── lessons_learned/          # Post-incident analysis
└── benchmarks/
    ├── industry/                 # Industry benchmarks
    └── regional/                 # Regional statistics
```

### Document Metadata Schema

Each document should include metadata for filtering:

```json
{
  "document_type": "threat_intelligence",
  "industry": ["Healthcare", "Finance"],
  "region": ["United States", "Canada"],
  "source": "CISA",
  "date": "2024-09-05",
  "threat_types": ["ransomware", "phishing"],
  "mitre_techniques": ["T1566.001", "T1486"],
  "relevance_score": 0.95
}
```

---

## Integration Points

### 1. Questionnaire Generation (Risk Identification)

**File**: `ai_question_generator.py`

**Integration Point**: `_build_contextual_prompt()` method

```python
from vertex_rag import get_rag_engine

def _build_contextual_prompt(self, context: Dict) -> str:
    """Build prompt with RAG grounding context."""
    
    # Get RAG engine
    rag_engine = get_rag_engine()
    
    # Retrieve grounding context
    rag_contexts = rag_engine.retrieve_risk_identification_context(
        industry=context['industry'],
        region=context['region'],
        organization_size=context.get('organization_size'),
        max_results=5
    )
    
    # Format context for prompt
    grounding_context = rag_engine.format_context_for_prompt(rag_contexts)
    
    # Build prompt with grounding
    prompt = f"""Create a comprehensive risk assessment questionnaire...
    
{grounding_context}

**Organization Context:**
- Industry: {context['industry']}
- Region: {context['region']}
...
"""
    
    return prompt
```

### 2. Chat Assistance (Risk Analysis Coaching)

**File**: `flask_app_chat.py`

**Integration Point**: `chat_assist()` and `chat_results()` endpoints

```python
from vertex_rag import get_rag_engine

@app.route('/chat/assist', methods=['POST'])
def chat_assist():
    """AI chat assistant with RAG grounding."""
    
    data = request.get_json()
    user_message = data.get('message')
    context = data.get('context', {})
    
    # Get RAG coaching context
    rag_engine = get_rag_engine()
    rag_contexts = rag_engine.retrieve_coaching_context(
        user_question=user_message,
        industry=context.get('industry'),
        region=context.get('region'),
        fair_component=context.get('fair_component'),
        max_results=3
    )
    
    # Format grounding context
    grounding = rag_engine.format_context_for_prompt(rag_contexts)
    
    # Build enhanced system prompt
    system_prompt = build_chat_system_prompt(context)
    enhanced_prompt = f"{system_prompt}\n\n{grounding}"
    
    # Call Claude with grounded context
    response = ai_generator.client.messages.create(
        model="claude-sonnet-4-20250514",
        system=enhanced_prompt,
        messages=[{"role": "user", "content": user_message}]
    )
    
    return jsonify({'response': response.content[0].text})
```

---

## Usage Examples

### Example 1: Risk Identification with RAG

```python
from vertex_rag import get_rag_engine

# Initialize RAG engine
rag = get_rag_engine()

# Retrieve context for healthcare in Canada
contexts = rag.retrieve_risk_identification_context(
    industry="Healthcare",
    region="Canada",
    organization_size="500 employees",
    max_results=5
)

# Review retrieved context
for ctx in contexts:
    print(f"Source: {ctx.source}")
    print(f"Relevance: {ctx.relevance_score}")
    print(f"Content: {ctx.content[:200]}...")
    print()
```

**Expected Output:**
```
Source: gs://rag-bucket/cisa_aa24_249a_healthcare.pdf
Relevance: 0.92
Content: CISA Advisory AA24-249A: Ransomware attacks targeting healthcare 
organizations in North America. Common attack vectors include...

Source: gs://rag-bucket/mitre_attack_t1486.json
Relevance: 0.88
Content: MITRE ATT&CK Technique T1486 (Data Encrypted for Impact): 
Adversaries may encrypt data on target systems to interrupt availability...
```

### Example 2: Coaching Context for Chat

```python
# User asks about ransomware frequency estimation
contexts = rag.retrieve_coaching_context(
    user_question="How often do ransomware attacks happen in healthcare?",
    industry="Healthcare",
    region="Canada",
    fair_component="LEF",
    max_results=3
)

# Format for prompt
formatted = rag.format_context_for_prompt(contexts)
print(formatted)
```

**Expected Output:**
```
**Grounding Context from Knowledge Base:**

**Source 1** (Relevance: 0.94):
- Source: Verizon 2024 DBIR - Healthcare Sector
- Content: Healthcare organizations experienced an average of 2.3 ransomware 
  incidents per year, with 67% reporting at least one incident...
- Metadata: {'industry': 'Healthcare', 'year': 2024}

**Source 2** (Relevance: 0.89):
- Source: IBM Cost of Data Breach 2024 - Healthcare
- Content: Healthcare sector shows 15% increase in ransomware frequency 
  compared to 2023, with average time to detect of 236 days...

**Use this grounding context to inform your response.**
```

---

## Benefits of RAG Integration

### 1. **Improved Accuracy**
- Grounded in authoritative, curated sources
- Reduces hallucination risk
- Provides verifiable citations

### 2. **Current Threat Intelligence**
- Knowledge base updated with latest advisories
- Real-time threat landscape awareness
- Regional and industry-specific context

### 3. **Consistent Coaching**
- Standardized guidance based on best practices
- Industry benchmarks for estimation
- Regulatory compliance awareness

### 4. **Reduced API Costs**
- Less reliance on web search during generation
- More efficient context retrieval
- Faster response times

### 5. **Audit Trail**
- Track which sources informed each assessment
- Compliance documentation
- Reproducible risk analyses

---

## Monitoring & Maintenance

### RAG Engine Status Check

```python
from vertex_rag import get_rag_engine

rag = get_rag_engine()
status = rag.get_status()

print(f"RAG Enabled: {status['enabled']}")
print(f"Project: {status['project_id']}")
print(f"Corpus: {status['rag_corpus']}")
```

### Knowledge Base Statistics

```python
from knowledge_base_manager import KnowledgeBaseManager

kb = KnowledgeBaseManager()
stats = kb.get_corpus_stats()

print(f"Documents: {stats['document_count']}")
print(f"Last Updated: {stats['last_updated']}")
```

### Update Workflow

**Monthly Updates:**
1. Download latest CISA advisories
2. Update MITRE ATT&CK data
3. Add new industry reports (Verizon DBIR, IBM)
4. Upload to knowledge base
5. Verify RAG retrieval quality

**Quarterly Reviews:**
1. Review retrieval relevance scores
2. Remove outdated documents
3. Add new compliance requirements
4. Update regional threat intelligence

---

## Fallback Behavior

The RAG engine is designed with graceful degradation:

```python
# RAG engine with fallback enabled (default)
rag = get_rag_engine(enable_fallback=True)

# If RAG unavailable, returns empty contexts
contexts = rag.retrieve_risk_identification_context(...)
# contexts = [] if RAG disabled

# Application continues with existing web search
```

**Fallback Scenarios:**
- Vertex AI libraries not installed → Empty contexts
- GCP credentials not configured → Empty contexts  
- RAG corpus not found → Empty contexts
- Network issues → Empty contexts

**No Fallback (Strict Mode):**
```python
# Raises exceptions if RAG unavailable
rag = get_rag_engine(enable_fallback=False)
```

---

## Cost Considerations

### Vertex AI RAG Pricing

**Storage:**
- $0.10 per GB per month (corpus storage)
- Estimated: 10 GB knowledge base = $1/month

**Queries:**
- $0.001 per query (retrieval)
- Estimated: 1,000 queries/month = $1/month

**Total Estimated Cost:**
- Small deployment: $2-5/month
- Medium deployment: $10-20/month
- Large deployment: $50-100/month

**Cost Optimization:**
- Cache frequently retrieved contexts
- Limit max_results per query
- Use metadata filters to reduce search space
- Archive outdated documents

---

## Security Considerations

### Data Privacy

- **No PII in knowledge base**: Only public threat intelligence
- **Access control**: Service account with minimal permissions
- **Encryption**: Data encrypted at rest and in transit
- **Audit logging**: All RAG queries logged

### Compliance

- **GDPR**: No personal data in corpus
- **SOC 2**: Audit trail for all retrievals
- **ISO 27001**: Secure document management

---

## Troubleshooting

### Common Issues

**Issue: RAG engine not initializing**
```bash
# Check environment variables
echo $GOOGLE_CLOUD_PROJECT
echo $VERTEX_RAG_CORPUS

# Verify authentication
gcloud auth application-default login
gcloud auth list
```

**Issue: No contexts retrieved**
```python
# Check corpus exists
kb = KnowledgeBaseManager()
stats = kb.get_corpus_stats()
print(stats)

# Verify documents uploaded
# Check metadata filters match query
```

**Issue: Low relevance scores**
- Review document metadata
- Improve query formulation
- Add more relevant documents to corpus
- Adjust similarity thresholds

---

## Next Steps

1. **Populate Knowledge Base**
   - Collect threat intelligence documents
   - Download MITRE ATT&CK data
   - Gather industry reports

2. **Test Integration**
   - Generate questionnaire with RAG
   - Test chat assistance with RAG
   - Verify context relevance

3. **Monitor Performance**
   - Track retrieval quality
   - Measure response times
   - Monitor costs

4. **Iterate and Improve**
   - Add more documents
   - Refine metadata
   - Optimize queries

---

## References

- [Vertex AI RAG Documentation](https://cloud.google.com/vertex-ai/docs/generative-ai/rag-overview)
- [MITRE ATT&CK](https://attack.mitre.org)
- [CISA Advisories](https://www.cisa.gov/news-events/cybersecurity-advisories)
- [Verizon DBIR](https://www.verizon.com/business/resources/reports/dbir/)

---

**Version**: 1.0.0  
**Last Updated**: November 2025  
**Status**: Implementation Ready
