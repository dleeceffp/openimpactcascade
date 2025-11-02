#!/usr/bin/env python3
"""
Test Vertex AI RAG Authentication and Access

Quick test script to verify:
1. Authentication is working
2. Can access Vertex AI API
3. Can list and access RAG corpora

Usage:
    python test_rag_auth.py --project oicsbx --corpus-id 6917529027641081856
"""

import sys
import argparse
from google.auth import default
from google.auth.exceptions import DefaultCredentialsError
import vertexai
from vertexai import rag

def test_authentication(project_id: str):
    """Test if authentication is working."""
    print("=" * 60)
    print("TEST 1: Authentication")
    print("=" * 60)
    
    try:
        credentials, auth_project = default()
        print("✓ Authentication successful")
        print(f"  Auth project: {auth_project}")
        print(f"  Credentials type: {type(credentials).__name__}")
        print(f"  Target project: {project_id}")
        return credentials, True
    except DefaultCredentialsError as e:
        print("✗ Authentication failed")
        print(f"\nError: {e}")
        print("\nPlease run:")
        print("  gcloud auth application-default login")
        return None, False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return None, False

def test_vertexai_init(project_id: str, location: str, credentials):
    """Test Vertex AI initialization."""
    print("\n" + "=" * 60)
    print("TEST 2: Vertex AI Initialization")
    print("=" * 60)
    
    try:
        vertexai.init(
            project=project_id,
            location=location,
            credentials=credentials
        )
        print("✓ Vertex AI initialized successfully")
        print(f"  Project: {project_id}")
        print(f"  Location: {location}")
        return True
    except Exception as e:
        print(f"✗ Vertex AI initialization failed: {e}")
        return False

def test_list_corpora():
    """Test listing RAG corpora."""
    print("\n" + "=" * 60)
    print("TEST 3: List RAG Corpora")
    print("=" * 60)
    
    try:
        corpora_pager = rag.list_corpora()
        corpora_list = list(corpora_pager)
        
        print(f"✓ Successfully listed corpora")
        print(f"  Found {len(corpora_list)} corpora")
        
        if corpora_list:
            print("\nAvailable corpora:")
            for i, corpus in enumerate(corpora_list, 1):
                corpus_id = corpus.name.split('/')[-1]
                print(f"\n  {i}. Display Name: {corpus.display_name}")
                print(f"     Corpus ID:     {corpus_id}")
                print(f"     Full Name:     {corpus.name}")
                print(f"     State:         {corpus.corpus_status.state if hasattr(corpus, 'corpus_status') else 'N/A'}")
        
        return True, corpora_list
    except Exception as e:
        print(f"✗ Failed to list corpora: {e}")
        print(f"\nError type: {type(e).__name__}")
        return False, []

def test_get_corpus(corpus_id: str, project_id: str, location: str):
    """Test getting specific corpus."""
    print("\n" + "=" * 60)
    print(f"TEST 4: Get Specific Corpus (ID: {corpus_id})")
    print("=" * 60)
    
    corpus_name = f"projects/{project_id}/locations/{location}/ragCorpora/{corpus_id}"
    
    try:
        corpus = rag.get_corpus(name=corpus_name)
        print("✓ Successfully retrieved corpus")
        print(f"  Display Name: {corpus.display_name}")
        print(f"  Description:  {corpus.description if hasattr(corpus, 'description') else 'N/A'}")
        print(f"  Full Name:    {corpus.name}")
        
        if hasattr(corpus, 'corpus_status'):
            print(f"  State:        {corpus.corpus_status.state}")
        
        return True
    except Exception as e:
        print(f"✗ Failed to get corpus: {e}")
        return False

def test_search_corpus(corpus_name: str):
    """Test searching in corpus."""
    print("\n" + "=" * 60)
    print("TEST 5: Test RAG Query")
    print("=" * 60)
    
    test_query = "test query"
    print(f"Query: '{test_query}'")
    
    try:
        response = rag.retrieval_query(
            rag_resources=[
                rag.RagResource(rag_corpus=corpus_name)
            ],
            text=test_query
        )
        
        count = len(response.contexts.contexts) if response.contexts else 0
        print(f"✓ Query successful")
        print(f"  Results: {count} contexts found")
        
        if count > 0:
            print("\n  Sample results:")
            for i, ctx in enumerate(response.contexts.contexts[:3], 1):
                text = ctx.text[:100] + "..." if len(ctx.text) > 100 else ctx.text
                print(f"    {i}. {text}")
        
        return True
    except Exception as e:
        print(f"✗ Query failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Test Vertex AI RAG authentication and access"
    )
    
    parser.add_argument(
        '--project',
        required=True,
        help='GCP project ID'
    )
    
    parser.add_argument(
        '--location',
        default='northamerica-northeast1',
        help='GCP region'
    )
    
    parser.add_argument(
        '--corpus-id',
        help='Corpus ID to test (optional)'
    )
    
    args = parser.parse_args()
    
    # Track results
    all_passed = True
    
    # Test 1: Authentication
    credentials, auth_ok = test_authentication(args.project)
    if not auth_ok:
        print("\n" + "=" * 60)
        print("RESULT: Authentication failed - stopping tests")
        print("=" * 60)
        return 1
    
    # Test 2: Vertex AI init
    init_ok = test_vertexai_init(args.project, args.location, credentials)
    if not init_ok:
        all_passed = False
    
    # Test 3: List corpora
    list_ok, corpora = test_list_corpora()
    if not list_ok:
        all_passed = False
    
    # Test 4: Get specific corpus (if provided)
    if args.corpus_id:
        get_ok = test_get_corpus(args.corpus_id, args.project, args.location)
        if not get_ok:
            all_passed = False
        
        # Test 5: Search in corpus
        if get_ok:
            corpus_name = f"projects/{args.project}/locations/{args.location}/ragCorpora/{args.corpus_id}"
            search_ok = test_search_corpus(corpus_name)
            if not search_ok:
                all_passed = False
    
    # Final summary
    print("\n" + "=" * 60)
    print("FINAL RESULT")
    print("=" * 60)
    
    if all_passed:
        print("✓ All tests passed!")
        print("\nYou can now run:")
        if args.corpus_id:
            print(f"  python gcs_to_rag_upload_fixed.py \\")
            print(f"    --corpus-id {args.corpus_id} \\")
            print(f"    --project {args.project} \\")
            print(f"    --metadata-dir ./processed_metadata")
        else:
            print(f"  python gcs_to_rag_upload_fixed.py \\")
            print(f"    --corpus <display-name> \\")
            print(f"    --project {args.project} \\")
            print(f"    --metadata-dir ./processed_metadata")
        return 0
    else:
        print("✗ Some tests failed")
        print("\nPlease check:")
        print("  1. Run: gcloud auth application-default login")
        print("  2. Verify project ID is correct")
        print("  3. Check IAM permissions")
        print("  4. See TROUBLESHOOTING.md for more help")
        return 1

if __name__ == '__main__':
    sys.exit(main())
