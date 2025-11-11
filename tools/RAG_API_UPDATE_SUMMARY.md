# RAG API Update Summary

## Overview

All Vertex AI RAG API calls have been updated to work correctly with the `northamerica-northeast1` region. The key issue was that this region requires parameters to be wrapped in `RagRetrievalConfig` objects rather than passed directly.

---

## Critical Discovery

### Regional API Limitation

The `northamerica-northeast1` region **does not support direct parameter passing** to `retrieval_query()`:

**❌ Does NOT Work:**
```python
response = rag.retrieval_query(
    rag_resources=[...],
    text="query",
    similarity_top_k=10,  # ❌ TypeError
    top_k=10,  # ❌ TypeError
    vector_distance_threshold=0.5  # ❌ TypeError
)
```

**✅ Works:**
```python
response = rag.retrieval_query(
    rag_resources=[...],
    text="query",
    rag_retrieval_config=rag.RagRetrievalConfig(
        top_k=10,
        filter=rag.Filter(vector_distance_threshold=0.5)
    )
)
```

---

## Files Updated

### 1. ✅ `vertex_rag.py`

**Changes:**
- Import: `from vertexai import rag` (not `vertexai.preview.rag`)
- Import: `from vertexai.generative_models import GenerativeModel` (not `preview.generative_models`)
- Added: `import vertexai`
- Init: `vertexai.init()` instead of `aiplatform.init()`
- Query: Implemented actual RAG retrieval with `RagRetrievalConfig`

**Key Update:**
```python
def _query_rag_corpus(self, query: str, max_results: int = 5, ...):
    response = rag.retrieval_query(
        rag_resources=[
            rag.RagResource(rag_corpus=self.rag_corpus_name)
        ],
        text=query,
        rag_retrieval_config=rag.RagRetrievalConfig(
            top_k=max_results,
            filter=rag.Filter(vector_distance_threshold=0.5)
        ),
    )
    
    contexts = []
    if response and response.contexts:
        for result in response.contexts.contexts:
            contexts.append(RAGContext(
                content=result.text,
                source=result.source_uri,
                relevance_score=result.distance,
                metadata=filter_metadata or {}
            ))
    
    return contexts
```

### 2. ✅ `knowledge_base_manager.py`

**Changes:**
- Import: `from vertexai import rag` (not `vertexai.preview.rag`)
- Added: `import vertexai`
- Init: `vertexai.init()` instead of `aiplatform.init()`

### 3. ✅ `infra/scripts/create_rag_corpus.py`

**Changes:**
- Import: `from vertexai import rag` (not `vertexai.preview.rag`)
- Create: `rag.create_corpus()` (not `rag.RagCorpus.create()`)
- List: `rag.list_corpora()` (not `rag.RagCorpus.list()`)
- Config: `rag.RagEmbeddingModelConfig()` with `rag.VertexPredictionEndpoint()`

---

## New Files Created

### 1. ✅ `VERTEX_RAG_API_MIGRATION.md`

Comprehensive migration guide covering:
- Regional API differences
- Correct usage patterns
- Common errors and solutions
- Complete working examples
- Migration checklist

### 2. ✅ `test_rag_retrieval.py`

Working test script that demonstrates:
- Correct API usage for northamerica-northeast1
- Multiple query examples
- Different configuration options
- Proper error handling
- Result parsing

### 3. ✅ `infra/scripts/VERTEX_RAG_API_UPDATE.md`

Documentation of the create_rag_corpus.py updates:
- Old vs new API comparison
- Migration steps
- Usage examples

---

## Correct API Pattern

### Complete Working Example

```python
from vertexai import rag
import vertexai

# 1. Initialize
vertexai.init(
    project="oic-dev-free",
    location="northamerica-northeast1"
)

# 2. List corpora
corpora_pager = rag.list_corpora()
corpora_list = list(corpora_pager)
corpus = corpora_list[0]

# 3. Query with RagRetrievalConfig
response = rag.retrieval_query(
    rag_resources=[
        rag.RagResource(rag_corpus=corpus.name)
    ],
    text="What are ransomware attack vectors?",
    rag_retrieval_config=rag.RagRetrievalConfig(
        top_k=5,
        filter=rag.Filter(vector_distance_threshold=0.5)
    )
)

# 4. Process results
if response and response.contexts:
    for context in response.contexts.contexts:
        print(f"Source: {context.source_uri}")
        print(f"Distance: {context.distance}")
        print(f"Text: {context.text}")
```

---

## Response Structure

```python
# Response object
response.contexts.contexts  # List of context objects

# Each context has:
context.text           # Retrieved text content
context.source_uri     # Source file (e.g., gs://bucket/file.txt)
context.distance       # Vector distance (lower = more similar)
```

---

## Testing

### Run Test Script

```bash
python test_rag_retrieval.py
```

### Expected Output

```
✓ Vertex AI initialized
✓ Found corpus: oic-rarag-kb
✓ Query successful
  Response type: RetrieveContextsResponse
  Contexts found: 0-N
```

### Verify Integration

```bash
# Test vertex_rag.py
python vertex_rag.py

# Test knowledge_base_manager.py
python knowledge_base_manager.py
```

---

## Integration Points

### 1. Questionnaire Generation

In `ai_question_generator.py`:

```python
from vertex_rag import get_rag_engine

# Get RAG engine
rag_engine = get_rag_engine()

# Retrieve grounding context
contexts = rag_engine.retrieve_risk_identification_context(
    industry="Healthcare",
    region="Canada",
    organization_size="500 employees"
)

# Format for prompt
context_text = rag_engine.format_context_for_prompt(contexts)

# Include in Claude prompt
prompt = f"{context_text}\n\n{original_prompt}"
```

### 2. Chat Assistant

In `flask_app_chat.py`:

```python
from vertex_rag import get_rag_engine

# Get RAG engine
rag_engine = get_rag_engine()

# Retrieve coaching context
contexts = rag_engine.retrieve_coaching_context(
    user_question=user_message,
    industry=session_data['industry'],
    region=session_data['region'],
    fair_component="LEF"
)

# Format and include in response
context_text = rag_engine.format_context_for_prompt(contexts)
```

---

## Migration Checklist

- [x] Update imports from `vertexai.preview` to `vertexai`
- [x] Change `aiplatform.init()` to `vertexai.init()`
- [x] Update `rag.RagCorpus.create()` to `rag.create_corpus()`
- [x] Update `rag.RagCorpus.list()` to `rag.list_corpora()`
- [x] Wrap retrieval parameters in `RagRetrievalConfig`
- [x] Move `top_k` inside `RagRetrievalConfig`
- [x] Move `vector_distance_threshold` inside `rag.Filter()`
- [x] Update response parsing to use `response.contexts.contexts`
- [x] Use `result.distance` for relevance score
- [x] Test with northamerica-northeast1 region
- [x] Create test scripts
- [x] Update documentation

---

## Next Steps

### 1. Populate Corpus

```bash
# Upload documents to the RAG corpus
python knowledge_base_manager.py
```

### 2. Test Retrieval

```bash
# Test RAG retrieval
python test_rag_retrieval.py
```

### 3. Integrate into Application

```bash
# Test full integration
python vertex_rag.py
```

### 4. Monitor Performance

- Check retrieval quality
- Adjust `top_k` and `vector_distance_threshold` as needed
- Monitor costs in GCP console

---

## Troubleshooting

### No Results Returned

**Cause:** Corpus is empty or query doesn't match content

**Solution:**
1. Upload documents: `python knowledge_base_manager.py`
2. Verify corpus has files: Check GCP console
3. Adjust `vector_distance_threshold` (try 0.7 for broader results)

### TypeError: unexpected keyword argument

**Cause:** Using direct parameters instead of `RagRetrievalConfig`

**Solution:** Wrap parameters in config object (see examples above)

### Import Error: No module named 'vertexai.preview'

**Cause:** Using old import path

**Solution:** Change to `from vertexai import rag`

---

## References

- **Migration Guide:** `VERTEX_RAG_API_MIGRATION.md`
- **Test Script:** `test_rag_retrieval.py`
- **Main Integration:** `vertex_rag.py`
- **Corpus Management:** `knowledge_base_manager.py`
- **Corpus Creation:** `infra/scripts/create_rag_corpus.py`

---

**Status:** ✅ Complete and Tested  
**Date:** November 2025  
**Region:** northamerica-northeast1 (Montreal, Canada)  
**API Version:** Stable (v1beta1)  
**Files Updated:** 3 core files + 3 new documentation files
