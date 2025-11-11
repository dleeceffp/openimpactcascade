#!/usr/bin/env python3
"""
Test Vertex AI RAG retrieval with correct API for northamerica-northeast1.

This script demonstrates the correct way to query the RAG corpus.
"""

import sys
from vertexai import rag
import vertexai

def main():
    print("=" * 70)
    print("  Vertex AI RAG Retrieval Test")
    print("  Region: northamerica-northeast1")
    print("=" * 70)
    
    # Initialize
    try:
        vertexai.init(project="oicsbx", location="northamerica-northeast1")
        print("\n✓ Vertex AI initialized")
    except Exception as e:
        print(f"\n✗ Failed to initialize: {e}")
        sys.exit(1)
    
    # List corpora
    print("\n" + "=" * 70)
    print("  Finding RAG Corpus")
    print("=" * 70)
    
    try:
        corpora_pager = rag.list_corpora()
        corpora_list = list(corpora_pager)
        
        if not corpora_list:
            print("\n✗ No corpora found")
            print("\nCreate a corpus first:")
            print("  cd infra/scripts")
            print("  python create_rag_corpus.py --project-id oicsbx --display-name oic-rarag-kb")
            sys.exit(1)
        
        corpus = corpora_list[0]
        print(f"\n✓ Found corpus: {corpus.display_name}")
        print(f"  Resource name: {corpus.name}")
        
    except Exception as e:
        print(f"\n✗ Error listing corpora: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Test retrieval with correct API
    print("\n" + "=" * 70)
    print("  Testing RAG Retrieval")
    print("=" * 70)
    
    test_queries = [
        "What are common ransomware attack vectors in healthcare?",
        "How to estimate loss event frequency for cyber incidents?",
        "MITRE ATT&CK techniques for initial access"
    ]
    
    for i, query_text in enumerate(test_queries, 1):
        print(f"\n--- Test Query {i} ---")
        print(f"Query: {query_text}")
        
        try:
            # Correct API usage for northamerica-northeast1
            response = rag.retrieval_query(
                rag_resources=[
                    rag.RagResource(
                        rag_corpus=corpus.name
                    )
                ],
                text=query_text,
                rag_retrieval_config=rag.RagRetrievalConfig(
                    top_k=3,  # Get top 3 results
                    filter=rag.Filter(
                        vector_distance_threshold=0.5  # Similarity threshold
                    ),
                ),
            )
            
            print(f"✓ Query successful")
            print(f"  Response type: {type(response).__name__}")
            
            # Process results
            if response and hasattr(response, 'contexts') and response.contexts:
                num_contexts = len(response.contexts.contexts)
                print(f"  Contexts found: {num_contexts}")
                
                if num_contexts > 0:
                    print("\n  Results:")
                    for j, context in enumerate(response.contexts.contexts, 1):
                        print(f"\n  {j}. Source: {context.source_uri if hasattr(context, 'source_uri') else 'unknown'}")
                        print(f"     Distance: {context.distance if hasattr(context, 'distance') else 'N/A'}")
                        
                        if hasattr(context, 'text'):
                            text_preview = context.text[:150] + "..." if len(context.text) > 150 else context.text
                            print(f"     Text: {text_preview}")
                else:
                    print("  ℹ️  No matching contexts found (corpus may be empty)")
            else:
                print("  ℹ️  No contexts in response (corpus may be empty)")
                
        except Exception as e:
            print(f"✗ Query failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Test with different configurations
    print("\n" + "=" * 70)
    print("  Testing Different Configurations")
    print("=" * 70)
    
    configs = [
        {
            "name": "High precision (low threshold)",
            "config": rag.RagRetrievalConfig(
                top_k=5,
                filter=rag.Filter(vector_distance_threshold=0.3)
            )
        },
        {
            "name": "Balanced",
            "config": rag.RagRetrievalConfig(
                top_k=10,
                filter=rag.Filter(vector_distance_threshold=0.5)
            )
        },
        {
            "name": "High recall (high threshold)",
            "config": rag.RagRetrievalConfig(
                top_k=15,
                filter=rag.Filter(vector_distance_threshold=0.7)
            )
        },
        {
            "name": "No filter",
            "config": rag.RagRetrievalConfig(
                top_k=5
            )
        }
    ]
    
    test_query = "cybersecurity risk assessment best practices"
    
    for config_test in configs:
        print(f"\n--- {config_test['name']} ---")
        
        try:
            response = rag.retrieval_query(
                rag_resources=[rag.RagResource(rag_corpus=corpus.name)],
                text=test_query,
                rag_retrieval_config=config_test['config']
            )
            
            num_results = 0
            if response and hasattr(response, 'contexts') and response.contexts:
                num_results = len(response.contexts.contexts)
            
            print(f"  ✓ Results: {num_results}")
            
        except Exception as e:
            print(f"  ✗ Failed: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    print("  Test Complete")
    print("=" * 70)
    print("\n✓ All tests completed")
    print("\nKey Findings:")
    print("  • Use rag_retrieval_config=rag.RagRetrievalConfig()")
    print("  • Set top_k inside RagRetrievalConfig")
    print("  • Set vector_distance_threshold inside rag.Filter()")
    print("  • Direct parameters (similarity_top_k, top_k) don't work")
    print("\nNext Steps:")
    print("  1. Upload documents to corpus:")
    print("     python knowledge_base_manager.py")
    print("  2. Integrate into application:")
    print("     See vertex_rag.py for usage examples")
    print()

if __name__ == "__main__":
    main()
