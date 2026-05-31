# BigQuery RAG Ingest Pipeline

A prototype pipeline for ingesting documents into BigQuery for RAG (Retrieval Augmented Generation).

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Documents     │────▶│    Chunker      │────▶│   Embedder      │
│  (PDF, MD, TXT) │     │  (with context) │     │  (Vertex AI)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                        BigQuery                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  documents   │  │    chunks    │  │  embeddings  │          │
│  │  (metadata)  │◀─│  (text +     │◀─│  (vectors)   │          │
│  │              │  │   context)   │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

## Schema

### documents
Rich metadata for each document:
- **Identity**: document_id, source_path, title, content_hash, version
- **Classification**: industry, region, doc_type, publication_year, source_type
- **Risk facets**: primary_domain, scenario_tags, lifecycle_stage
- **Quality**: sensitivity, quality_rating, license_usage, curator_notes
- **System**: ingested_at, last_updated, status

### chunks
Text chunks with context:
- **Content**: chunk_id, document_id, chunk_index, chunk_text, token_count
- **Context**: page_number, section_number, section_title, chunk_type
- **Denormalized**: industry, primary_domain, doc_type, quality_rating

### embeddings
Vector embeddings for similarity search:
- embedding_id, chunk_id, embedding (ARRAY<FLOAT64>), model_id, model_version

### retrieval_logs
Query-level logging:
- query_id, query_text, query_embedding
- Filters: industry_filter, region_filter, domain_filter
- Stats: result_count, max_similarity, min_similarity
- Feedback: overall_rating, was_helpful

### retrieval_log_results
**Per-chunk feedback for quality loops:**
- query_id, rank, chunk_id, similarity_score
- User interaction: was_displayed, was_clicked, was_copied, dwell_time_ms
- Explicit feedback: was_useful, feedback_notes
- Chunk context: chunk_doc_type, chunk_quality, chunk_industry

This enables analysis like:
- "Which chunks rank high but get poor feedback?" → quality_rating needs adjustment
- "Which queries return low similarity scores?" → corpus gaps to fill

## Installation

```bash
cd tools/bq_rag_ingest
pip install -r requirements.txt
```

## Usage

### 1. Setup Schema

```bash
# Create dataset and tables
python -m bq_rag_ingest.schema --project YOUR_PROJECT_ID

# Check table stats
python -m bq_rag_ingest.schema --project YOUR_PROJECT_ID --stats

# Drop and recreate (CAUTION)
python -m bq_rag_ingest.schema --project YOUR_PROJECT_ID --drop
```

### 2. Test Chunker

```bash
# Chunk a document and see results
python -m bq_rag_ingest.chunker /path/to/document.pdf

# Output to JSON
python -m bq_rag_ingest.chunker /path/to/document.pdf --output chunks.json
```

### 3. Test Embedder

```bash
# Test with real Vertex AI
python -m bq_rag_ingest.embedder --project YOUR_PROJECT_ID

# Test with mock embeddings
python -m bq_rag_ingest.embedder --mock
```

### 4. Run Ingestion

```bash
# Ingest a single file
python -m bq_rag_ingest.ingest /path/to/document.pdf --project YOUR_PROJECT_ID

# Ingest a directory
python -m bq_rag_ingest.ingest /path/to/docs/ --pattern "*.pdf" --project YOUR_PROJECT_ID

# Ingest from manifest (like rag_cyber_risk_corpus_sources.json)
python -m bq_rag_ingest.ingest /path/to/manifest.json --project YOUR_PROJECT_ID

# Use mock embeddings for testing
python -m bq_rag_ingest.ingest /path/to/docs/ --mock --project YOUR_PROJECT_ID

# Force re-ingest existing documents
python -m bq_rag_ingest.ingest /path/to/docs/ --force --project YOUR_PROJECT_ID

# Interactive curator mode (prompts for metadata)
python -m bq_rag_ingest.ingest /path/to/document.pdf --interactive --project YOUR_PROJECT_ID
```

### 5. Interactive Curator Mode

For high-value documents, use interactive mode to capture your expertise:

```bash
python -m bq_rag_ingest.ingest important_doc.pdf -i --project YOUR_PROJECT_ID
```

This prompts for:
- **Title, Industry, Region, Doc Type**
- **Quality Rating** (1-5 with guidance)
- **Scenario Tags** (from taxonomy: ransomware, BEC, insider_threat, etc.)
- **Lifecycle Stages** (strategy, design, implementation, operations, etc.)
- **Curator Notes** - YOUR 30 years of wisdom on why this doc matters

### 6. Sidecar Metadata Files

For batch ingestion with curator metadata, create `.meta.json` sidecar files:

```
documents/
├── nist_framework.pdf
├── nist_framework.pdf.meta.json   # ← Sidecar metadata
├── incident_report_2024.pdf
└── incident_report_2024.meta.json
```

Example sidecar file:
```json
{
  "title": "NIST Cybersecurity Framework 2.0",
  "industry": "government",
  "region": "US",
  "doc_type": "standard",
  "publication_year": 2024,
  "primary_domain": "Governance/ESRM",
  "quality_rating": 5,
  "scenario_tags": ["ransomware", "supply_chain", "insider_threat"],
  "lifecycle_stage": ["strategy", "design", "audit"],
  "curator_notes": "Gold standard framework. Updated in 2024 with supply chain focus. Essential for any US-based risk program.",
  "license_usage": "ok_to_train"
}
```

## Programmatic Usage

```python
from bq_rag_ingest.schema import setup_schema
from bq_rag_ingest.ingest import RAGIngestPipeline

# Setup schema (one-time)
setup_schema(project_id="your-project")

# Create pipeline
pipeline = RAGIngestPipeline(
    project_id="your-project",
    dataset_id="oic_rag_catalog",
    chunk_size=1000,
    chunk_overlap=100
)

# Ingest with metadata
stats = pipeline.ingest_file(
    "/path/to/document.pdf",
    metadata={
        "industry": "healthcare",
        "region": "Canada",
        "doc_type": "standard",
        "quality_rating": 5,
        "curator_notes": "Gold standard HIPAA guidance"
    }
)

print(f"Chunks created: {stats.chunks_created}")
print(f"Embeddings: {stats.embeddings_generated}")
```

## Environment Variables

```bash
# Required
export GOOGLE_CLOUD_PROJECT=your-project-id

# Optional (for service account auth)
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

## Metadata Fields

### industry
- healthcare, finance, government, energy, retail, technology, manufacturing

### region
- Canada, US, EU, UK, global, multi

### doc_type
- standard, guideline, runbook, incident_report, whitepaper, academic_paper, regulatory

### source_type
- internal_policy, external_framework, vendor_marketing, regulator, standards_body, academic, analyst

### primary_domain
- Identity, Network, Endpoint, Cloud, DevSecOps, OT/ICS, Physical, Governance/ESRM

### scenario_tags (array)
- ransomware, BEC, data_exfil, insider_threat, supply_chain, phishing, etc.

### lifecycle_stage (array)
- strategy, design, implementation, operations, incident_response, audit, training

### quality_rating (1-5)
1. Marketing material - vendor-biased, limited depth
2. General guidance - useful but not authoritative
3. Good reference - solid content, reputable source
4. Authoritative source - industry-recognized, well-researched
5. Gold standard - definitive reference, primary source

## Doc-Type Aware Chunking

The chunker automatically adjusts chunk size based on document type:

| Doc Type | Chunk Size | Overlap | Rationale |
|----------|------------|---------|-----------|
| incident_report, case_study | 500 | 75 | Preserve scenario integrity |
| standard, framework, guideline, regulatory | 1000 | 100 | Balanced context |
| academic_paper, whitepaper, research | 1200-1500 | 120-150 | Preserve arguments |
| runbook, procedure | 400 | 50 | Preserve step integrity |
| checklist | 300 | 30 | Keep items together |

## Next Steps

1. **Retrieval module** - Query BigQuery with vector similarity search
2. **Integration** - Connect to existing `vertex_rag_v211.py` interface
3. **Quality feedback** - Use retrieval_logs for continuous improvement
