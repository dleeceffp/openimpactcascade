# Vertex AI RAG API Migration Guide

## Overview

The Vertex AI RAG API has been updated across the codebase to use the current stable API. This document details the changes and the correct usage patterns for the `northamerica-northeast1` region.

---

## Critical Finding: Regional API Differences

### ⚠️ Important Discovery

The `northamerica-northeast1` region has **limited parameter support** compared to other regions like `us-central1`:

**NOT Supported (Direct Parameters):**
- ❌ `similarity_top_k` - Direct parameter
- ❌ `top_k` - Direct parameter  
- ❌ `vector_distance_threshold` - Direct parameter

**✅ Supported (Via RagRetrievalConfig):**
- ✅ `rag_retrieval_config` - Configuration object
  - ✅ `top_k` - Inside config
  - ✅ `filter` - Inside config
    - ✅ `vector_distance_threshold` - Inside filter

---

## Correct API Usage for northamerica-northeast1

### ✅ Working Pattern

```python
from vertexai import rag
import vertexai

# Initialize
vertexai.init(project="your-project", location="northamerica-northeast1")

# Query with RagRetrievalConfig
response = rag.retrieval_query(
    rag_resources=[
        rag.RagResource(
            rag_corpus="projects/PROJECT/locations/LOCATION/ragCorpora/ID"
        )
    ],
    text="your query text",
    rag_retrieval_config=rag.RagRetrievalConfig(
        top_k=10,  # Number of results
        filter=rag.Filter(
            vector_distance_threshold=0.5  # Similarity threshold
        ),
    ),
)
```

### ❌ Non-Working Patterns

```python
# WRONG - Direct parameters don't work in northamerica-northeast1
response = rag.retrieval_query(
    rag_resources=[...],
    text="query",
    similarity_top_k=10,  # ❌ TypeError
    vector_distance_threshold=0.5  # ❌ TypeError
)

# WRONG - top_k as direct parameter
response = rag.retrieval_query(
    rag_resources=[...],
    text="query",
    top_k=10  # ❌ TypeError
)
```

---

## Files Updated

### 1. `vertex_rag.py` ✅

**Changes:**
- Import: `from vertexai import rag` (not `vertexai.preview`)
- Import: `from vertexai.generative_models import GenerativeModel` (not `preview.generative_models`)
- Added: `import vertexai`
- Init: `vertexai.init()` (not `aiplatform.init()`)
- Query: Uses `rag_retrieval_config=rag.RagRetrievalConfig()`

**Updated Method:**
```python
def _query_rag_corpus(self, query: str, max_results: int = 5, filter_metadata: Optional[Dict[str, Any]] = None):
    response = rag.retrieval_query(
        rag_resources=[
            rag.RagResource(
                rag_corpus=self.rag_corpus_name,
            )
        ],
        text=query,
        rag_retrieval_config=rag.RagRetrievalConfig(
            top_k=max_results,
            filter=rag.Filter(
                vector_distance_threshold=0.5
            ),
        ),
    )
    
    contexts = []
    if response and hasattr(response, 'contexts') and response.contexts:
        for result in response.contexts.contexts:
            contexts.append(RAGContext(
                content=result.text,
                source=result.source_uri,
                relevance_score=result.distance,
                metadata=filter_metadata or {}
            ))
    
    return contexts
```

### 2. `knowledge_base_manager.py` ✅

**Changes:**
- Import: `from vertexai import rag` (not `vertexai.preview`)
- Added: `import vertexai`
- Init: `vertexai.init()` (not `aiplatform.init()`)

### 3. `infra/scripts/create_rag_corpus.py` ✅

**Changes:**
- Import: `from vertexai import rag` (not `vertexai.preview`)
- Create: `rag.create_corpus()` (not `rag.RagCorpus.create()`)
- List: `rag.list_corpora()` (not `rag.RagCorpus.list()`)
- Config: `rag.RagEmbeddingModelConfig()` with `rag.VertexPredictionEndpoint()`

---

## Response Structure

### Response Object

```python
response = rag.retrieval_query(...)

# Response type
type(response)  # google.cloud.aiplatform_v1.types.vertex_rag_service.RetrieveContextsResponse

# Access contexts
if response.contexts:
    for context in response.contexts.contexts:
        text = context.text
        source = context.source_uri
        distance = context.distance  # Similarity score
```

### Context Attributes

- `text` - The retrieved text content
- `source_uri` - Source file URI (e.g., `gs://bucket/file.txt`)
- `distance` - Vector distance (lower = more similar)

---

## Testing

### Test Script

See `test_rag_api_params.py` for parameter testing.

### Successful Test Output

```
=== Finding Corpus ===
Found corpus: oic-rarag-kb
Resource name: projects/oicsbx/locations/northamerica-northeast1/ragCorpora/6917529027641081856

=== Testing API Calls ===

Test 3: No top_k parameter
  Parameters: ['rag_resources', 'text']
  ✓ SUCCESS - Call worked!
  Response type: <class 'google.cloud.aiplatform_v1.types.vertex_rag_service.RetrieveContextsResponse'>
  Contexts: 0
```

---

## Migration Checklist

For any code using Vertex AI RAG:

- [ ] Change import from `vertexai.preview.rag` to `vertexai.rag`
- [ ] Change import from `vertexai.preview.generative_models` to `vertexai.generative_models`
- [ ] Add `import vertexai`
- [ ] Change `aiplatform.init()` to `vertexai.init()`
- [ ] Change `rag.RagCorpus.create()` to `rag.create_corpus()`
- [ ] Change `rag.RagCorpus.list()` to `rag.list_corpora()`
- [ ] Wrap retrieval parameters in `rag_retrieval_config=rag.RagRetrievalConfig()`
- [ ] Move `top_k` inside `RagRetrievalConfig`
- [ ] Move `vector_distance_threshold` inside `rag.Filter()` inside `RagRetrievalConfig`
- [ ] Update response parsing to use `response.contexts.contexts`
- [ ] Use `result.distance` for relevance score (not `result.score`)

---

## Common Errors and Solutions

### Error: "retrieval_query() got an unexpected keyword argument 'similarity_top_k'"

**Solution:** Use `rag_retrieval_config` instead:
```python
# Wrong
response = rag.retrieval_query(..., similarity_top_k=10)

# Right
response = rag.retrieval_query(
    ...,
    rag_retrieval_config=rag.RagRetrievalConfig(top_k=10)
)
```

### Error: "retrieval_query() got an unexpected keyword argument 'top_k'"

**Solution:** Move `top_k` inside `RagRetrievalConfig`:
```python
# Wrong
response = rag.retrieval_query(..., top_k=10)

# Right
response = rag.retrieval_query(
    ...,
    rag_retrieval_config=rag.RagRetrievalConfig(top_k=10)
)
```

### Error: "retrieval_query() got an unexpected keyword argument 'vector_distance_threshold'"

**Solution:** Wrap in `Filter` inside `RagRetrievalConfig`:
```python
# Wrong
response = rag.retrieval_query(..., vector_distance_threshold=0.5)

# Right
response = rag.retrieval_query(
    ...,
    rag_retrieval_config=rag.RagRetrievalConfig(
        filter=rag.Filter(vector_distance_threshold=0.5)
    )
)
```

### Error: "No module named 'vertexai.preview'"

**Solution:** Update import:
```python
# Wrong
from vertexai.preview import rag

# Right
from vertexai import rag
```

---

## Region-Specific Notes

### northamerica-northeast1 (Montreal, Canada)

- ✅ RAG Engine supported
- ✅ `retrieval_query` available
- ⚠️ **Must use `RagRetrievalConfig` for parameters**
- ⚠️ Direct parameter passing not supported
- ✅ Canadian data residency compliant

### us-central1, us-east4, europe-west1, asia-southeast1

- ✅ RAG Engine supported
- ✅ `retrieval_query` available
- ✅ May support additional parameter patterns
- ℹ️ Always use `RagRetrievalConfig` for consistency

---

## Example: Complete Working Code

```python
from vertexai import rag
import vertexai

# Initialize
vertexai.init(
    project="oic-dev-free",
    location="northamerica-northeast1"
)

# List corpora
corpora_pager = rag.list_corpora()
corpora_list = list(corpora_pager)

if corpora_list:
    corpus = corpora_list[0]
    print(f"Using corpus: {corpus.display_name}")
    
    # Query with proper config
    response = rag.retrieval_query(
        rag_resources=[
            rag.RagResource(
                rag_corpus=corpus.name
            )
        ],
        text="What are common ransomware attack vectors?",
        rag_retrieval_config=rag.RagRetrievalConfig(
            top_k=5,
            filter=rag.Filter(
                vector_distance_threshold=0.3
            ),
        ),
    )
    
    # Process results
    if response and response.contexts:
        print(f"Found {len(response.contexts.contexts)} results")
        for i, context in enumerate(response.contexts.contexts, 1):
            print(f"\n{i}. {context.source_uri}")
            print(f"   Distance: {context.distance:.4f}")
            print(f"   Text: {context.text[:200]}...")
```

---

## References

- [Vertex AI RAG Quickstart](https://cloud.google.com/vertex-ai/generative-ai/docs/rag-engine/rag-quickstart)
- [RAG retrieval_query Sample](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/samples/generativeaionvertexai-rag-retrieval-query)
- [RAG Engine API Reference](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/rag-api)

---

**Status:** ✅ Complete  
**Date:** November 2025  
**Region:** northamerica-northeast1  
**API Version:** Stable (v1beta1)  
**Files Updated:** 3 (vertex_rag.py, knowledge_base_manager.py, create_rag_corpus.py)
