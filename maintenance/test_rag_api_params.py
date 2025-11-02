#!/usr/bin/env python3
"""
Test script to find correct Vertex AI RAG API parameters.

This will help us determine the correct parameter names for retrieval_query().
"""

import sys
from vertexai import rag
import vertexai
import inspect

# Initialize
try:
    vertexai.init(project="oicsbx", location="northamerica-northeast1")
    print("✓ Vertex AI initialized\n")
except Exception as e:
    print(f"✗ Failed to initialize: {e}")
    sys.exit(1)

# Inspect retrieval_query function
print("=== retrieval_query API Signature ===")
print(f"Function: {rag.retrieval_query}")
print(f"\nSignature: {inspect.signature(rag.retrieval_query)}")

# Get detailed parameter info
sig = inspect.signature(rag.retrieval_query)
print("\nParameters:")
for param_name, param in sig.parameters.items():
    print(f"  {param_name}")
    if param.default != inspect.Parameter.empty:
        print(f"    default: {param.default}")
    if param.annotation != inspect.Parameter.empty:
        print(f"    type: {param.annotation}")

# Try to get docstring
print(f"\n=== Documentation ===")
if rag.retrieval_query.__doc__:
    print(rag.retrieval_query.__doc__)
else:
    print("No docstring available")

# List corpus to get one for testing
print("\n=== Finding Corpus ===")
try:
    corpora_pager = rag.list_corpora()
    corpora_list = list(corpora_pager)
    
    if corpora_list:
        corpus = corpora_list[0]
        print(f"Found corpus: {corpus.display_name}")
        print(f"Resource name: {corpus.name}")
        
        # Try different parameter combinations
        print("\n=== Testing API Calls ===")
        
        test_cases = [
            {
                "name": "Test 1: similarity_top_k",
                "params": {
                    "rag_resources": [rag.RagResource(rag_corpus=corpus.name)],
                    "text": "test query",
                    "similarity_top_k": 3
                }
            },
            {
                "name": "Test 2: top_k",
                "params": {
                    "rag_resources": [rag.RagResource(rag_corpus=corpus.name)],
                    "text": "test query",
                    "top_k": 3
                }
            },
            {
                "name": "Test 3: No top_k parameter",
                "params": {
                    "rag_resources": [rag.RagResource(rag_corpus=corpus.name)],
                    "text": "test query"
                }
            },
            {
                "name": "Test 4: With vector_distance_threshold",
                "params": {
                    "rag_resources": [rag.RagResource(rag_corpus=corpus.name)],
                    "text": "test query",
                    "vector_distance_threshold": 0.5
                }
            }
        ]
        
        for test in test_cases:
            print(f"\n{test['name']}")
            print(f"  Parameters: {list(test['params'].keys())}")
            try:
                response = rag.retrieval_query(**test['params'])
                print(f"  ✓ SUCCESS - Call worked!")
                print(f"  Response type: {type(response)}")
                if hasattr(response, 'contexts'):
                    print(f"  Contexts: {len(response.contexts.contexts) if response.contexts else 0}")
            except TypeError as e:
                print(f"  ✗ FAILED - {e}")
            except Exception as e:
                print(f"  ✗ ERROR - {e}")
    else:
        print("No corpora found")
        
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Test Complete ===")
