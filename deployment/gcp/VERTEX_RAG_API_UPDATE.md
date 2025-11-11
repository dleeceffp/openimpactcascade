# Vertex AI RAG API Update

## Overview

The Vertex AI RAG API has been updated. The `create_rag_corpus.py` script has been migrated from the old preview API to the current stable API.

---

## API Changes

### Old API (Preview - Deprecated)
```python
from vertexai.preview import rag

# Old way - NO LONGER WORKS
embedding_config = rag.EmbeddingModelConfig()
embedding_config.publisher_model = "text-embedding-005"

corpus = rag.RagCorpus.create(
    display_name="my-corpus",
    embedding_model_config=embedding_config
)

corpora = rag.RagCorpus.list()
```

### New API (Current - Stable)
```python
from vertexai import rag

# New way - CURRENT API
embedding_model_config = rag.RagEmbeddingModelConfig(
    vertex_prediction_endpoint=rag.VertexPredictionEndpoint(
        publisher_model="publishers/google/models/text-embedding-005"
    )
)

rag_corpus = rag.create_corpus(
    display_name="my-corpus",
    backend_config=rag.RagVectorDbConfig(
        rag_embedding_model_config=embedding_model_config
    )
)

corpora_pager = rag.list_corpora()
corpora_list = list(corpora_pager)
```

---

## Key Differences

### 1. Import Statement
- **Old:** `from vertexai.preview import rag`
- **New:** `from vertexai import rag`

### 2. Embedding Model Configuration
- **Old:** `rag.EmbeddingModelConfig()`
- **New:** `rag.RagEmbeddingModelConfig()` with `rag.VertexPredictionEndpoint()`

### 3. Model Name Format
- **Old:** `"text-embedding-005"`
- **New:** `"publishers/google/models/text-embedding-005"`

### 4. Corpus Creation
- **Old:** `rag.RagCorpus.create()`
- **New:** `rag.create_corpus()`

### 5. Backend Configuration
- **Old:** `embedding_model_config=...` (direct parameter)
- **New:** `backend_config=rag.RagVectorDbConfig(rag_embedding_model_config=...)`

### 6. Listing Corpora
- **Old:** `rag.RagCorpus.list()` returns list directly
- **New:** `rag.list_corpora()` returns pager object, need to convert to list

### 7. Corpus Verification
- **Old:** `rag.RagCorpus(corpus_name)` to get corpus by name
- **New:** Must list all corpora and find by name (no direct get method)

---

## Updated Script

The `create_rag_corpus.py` script has been updated with:

### ✅ Correct Imports
```python
from vertexai import rag  # Not from vertexai.preview
import vertexai
```

### ✅ Correct Embedding Configuration
```python
embedding_model_config = rag.RagEmbeddingModelConfig(
    vertex_prediction_endpoint=rag.VertexPredictionEndpoint(
        publisher_model="publishers/google/models/text-embedding-005"
    )
)
```

### ✅ Correct Corpus Creation
```python
rag_corpus = rag.create_corpus(
    display_name=display_name,
    description=description,
    backend_config=rag.RagVectorDbConfig(
        rag_embedding_model_config=embedding_model_config
    )
)
```

### ✅ Correct Corpus Listing
```python
corpora_pager = rag.list_corpora()
corpora_list = list(corpora_pager)

for corpus in corpora_list:
    print(f"{corpus.display_name} - {corpus.name}")
```

### ✅ Correct Corpus Verification
```python
corpora_pager = rag.list_corpora()
corpora_list = list(corpora_pager)

corpus_found = None
for corpus in corpora_list:
    if corpus.name == corpus_name:
        corpus_found = corpus
        break
```

---

## Usage Examples

### Create Corpus
```bash
python create_rag_corpus.py \
  --project-id oic-dev-free \
  --display-name oic-dev-free-rarag-kb \
  --location northamerica-northeast1 \
  --description "RAG corpus for OpenImpactCascade dev environment"
```

### List Existing Corpora
```bash
python create_rag_corpus.py \
  --project-id oic-dev-free \
  --list-only
```

### Create with Custom Embedding Model
```bash
python create_rag_corpus.py \
  --project-id oic-dev-free \
  --display-name oic-dev-free-rarag-kb \
  --embedding-model text-embedding-004
```

### Create and Verify
```bash
python create_rag_corpus.py \
  --project-id oic-dev-free \
  --display-name oic-dev-free-rarag-kb \
  --verify
```

---

## Supported Embedding Models

All models must use the full publisher path format:

- `publishers/google/models/text-embedding-005` (default, recommended)
- `publishers/google/models/text-embedding-004`
- `publishers/google/models/textembedding-gecko@003`
- `publishers/google/models/textembedding-gecko@002`
- `publishers/google/models/textembedding-gecko@001`

---

## Supported Locations

RAG Engine is available in these regions:

- `northamerica-northeast1` (Montreal, Canada) - **Default for Canadian data residency**
- `us-central1` (Iowa)
- `us-east4` (Virginia)
- `europe-west1` (Belgium)
- `asia-southeast1` (Singapore)

---

## Troubleshooting

### Error: "No module named 'vertexai.preview'"
**Solution:** Update import to `from vertexai import rag`

### Error: "RagCorpus has no attribute 'create'"
**Solution:** Use `rag.create_corpus()` instead of `rag.RagCorpus.create()`

### Error: "EmbeddingModelConfig is not defined"
**Solution:** Use `rag.RagEmbeddingModelConfig()` instead

### Error: "Invalid embedding model name"
**Solution:** Use full path format: `publishers/google/models/text-embedding-005`

### Error: "Missing backend_config"
**Solution:** Wrap embedding config in `rag.RagVectorDbConfig()`

---

## Migration Checklist

If you have existing code using the old API:

- [ ] Change import from `vertexai.preview` to `vertexai`
- [ ] Replace `rag.EmbeddingModelConfig()` with `rag.RagEmbeddingModelConfig()`
- [ ] Add `rag.VertexPredictionEndpoint()` wrapper
- [ ] Update model names to full publisher path format
- [ ] Replace `rag.RagCorpus.create()` with `rag.create_corpus()`
- [ ] Add `backend_config=rag.RagVectorDbConfig()` wrapper
- [ ] Replace `rag.RagCorpus.list()` with `rag.list_corpora()`
- [ ] Convert pager results to list: `list(rag.list_corpora())`
- [ ] Update corpus verification to use list and search

---

## References

- [Vertex AI RAG Quickstart](https://cloud.google.com/vertex-ai/generative-ai/docs/rag-engine/rag-quickstart)
- [RAG Engine API Reference](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/rag-api)
- [List Corpora Sample](https://cloud.google.com/vertex-ai/generative-ai/docs/samples/generativeaionvertexai-rag-list-corpora)
- [Vertex AI Python SDK](https://cloud.google.com/python/docs/reference/aiplatform/latest)

---

**Status:** ✅ Updated  
**Date:** November 2025  
**API Version:** Stable (v1beta1)  
**Script:** `create_rag_corpus.py`
