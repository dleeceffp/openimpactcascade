#!/usr/bin/env python3
"""
Test Vertex AI RAG Access using REST API

This version bypasses the buggy vertexai.rag SDK and uses REST API directly.

Usage:
    python test_rag_rest.py --project oicsbx --corpus-id 6917529027641081856
"""

import sys
import argparse
import requests
from google.auth import default
from google.auth.transport.requests import Request
from google.auth.exceptions import DefaultCredentialsError

def test_authentication(project_id: str):
    """Test if authentication is working."""
    print("=" * 60)
    print("TEST 1: Authentication")
    print("=" * 60)
    
    try:
        credentials, auth_project = default()
        
        # Get token
        if not credentials.valid:
            credentials.refresh(Request())
        
        print("✓ Authentication successful")
        print(f"  Auth project: {auth_project}")
        print(f"  Credentials type: {type(credentials).__name__}")
        print(f"  Target project: {project_id}")
        print(f"  Token obtained: {credentials.token[:20]}...")
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

def test_list_corpora_rest(project_id: str, location: str, credentials):
    """Test listing RAG corpora using REST API."""
    print("\n" + "=" * 60)
    print("TEST 2: List RAG Corpora (REST API)")
    print("=" * 60)
    
    try:
        # Get token
        if not credentials.valid:
            credentials.refresh(Request())
        
        url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/ragCorpora"
        headers = {
            'Authorization': f'Bearer {credentials.token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        corpora = data.get('ragCorpora', [])
        
        print(f"✓ Successfully listed corpora via REST API")
        print(f"  Found {len(corpora)} corpora")
        
        if corpora:
            print("\nAvailable corpora:")
            for i, corpus in enumerate(corpora, 1):
                corpus_id = corpus['name'].split('/')[-1]
                print(f"\n  {i}. Display Name: {corpus.get('displayName', 'N/A')}")
                print(f"     Corpus ID:     {corpus_id}")
                print(f"     State:         {corpus.get('corpusStatus', {}).get('state', 'N/A')}")
        
        return True, corpora
    except requests.exceptions.HTTPError as e:
        print(f"✗ HTTP Error: {e}")
        print(f"Response: {e.response.text if e.response else 'No response'}")
        return False, []
    except Exception as e:
        print(f"✗ Failed to list corpora: {e}")
        print(f"Error type: {type(e).__name__}")
        return False, []

def test_get_corpus_rest(corpus_id: str, project_id: str, location: str, credentials):
    """Test getting specific corpus using REST API."""
    print("\n" + "=" * 60)
    print(f"TEST 3: Get Specific Corpus (REST API)")
    print(f"Corpus ID: {corpus_id}")
    print("=" * 60)
    
    corpus_name = f"projects/{project_id}/locations/{location}/ragCorpora/{corpus_id}"
    url = f"https://{location}-aiplatform.googleapis.com/v1/{corpus_name}"
    
    try:
        # Get token
        if not credentials.valid:
            credentials.refresh(Request())
        
        headers = {
            'Authorization': f'Bearer {credentials.token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        corpus = response.json()
        
        print("✓ Successfully retrieved corpus via REST API")
        print(f"  Display Name: {corpus.get('displayName', 'N/A')}")
        print(f"  Description:  {corpus.get('description', 'N/A')}")
        print(f"  Full Name:    {corpus.get('name', 'N/A')}")
        print(f"  State:        {corpus.get('corpusStatus', {}).get('state', 'N/A')}")
        
        return True, corpus
    except requests.exceptions.HTTPError as e:
        print(f"✗ HTTP Error: {e}")
        print(f"Response: {e.response.text if e.response else 'No response'}")
        return False, None
    except Exception as e:
        print(f"✗ Failed to get corpus: {e}")
        return False, None

def test_list_corpus_files_rest(corpus_id: str, project_id: str, location: str, credentials):
    """Test listing files in corpus using REST API."""
    print("\n" + "=" * 60)
    print("TEST 4: List Files in Corpus (REST API)")
    print("=" * 60)
    
    corpus_name = f"projects/{project_id}/locations/{location}/ragCorpora/{corpus_id}"
    url = f"https://{location}-aiplatform.googleapis.com/v1/{corpus_name}/ragFiles"
    
    try:
        # Get token
        if not credentials.valid:
            credentials.refresh(Request())
        
        headers = {
            'Authorization': f'Bearer {credentials.token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        files = data.get('ragFiles', [])
        
        print(f"✓ Successfully listed files via REST API")
        print(f"  Files in corpus: {len(files)}")
        
        if files:
            print("\n  Sample files:")
            for i, file_info in enumerate(files[:5], 1):
                display_name = file_info.get('displayName', 'N/A')
                print(f"    {i}. {display_name}")
        
        return True
    except requests.exceptions.HTTPError as e:
        print(f"✗ HTTP Error: {e}")
        print(f"Response: {e.response.text if e.response else 'No response'}")
        return False
    except Exception as e:
        print(f"✗ Failed to list files: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Test Vertex AI RAG access using REST API (bypasses SDK bug)"
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
        required=True,
        help='Corpus ID to test'
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
    
    # Test 2: List corpora via REST
    list_ok, corpora = test_list_corpora_rest(args.project, args.location, credentials)
    if not list_ok:
        all_passed = False
    
    # Test 3: Get specific corpus
    get_ok, corpus = test_get_corpus_rest(args.corpus_id, args.project, args.location, credentials)
    if not get_ok:
        all_passed = False
    
    # Test 4: List files in corpus
    files_ok = test_list_corpus_files_rest(args.corpus_id, args.project, args.location, credentials)
    if not files_ok:
        all_passed = False
    
    # Final summary
    print("\n" + "=" * 60)
    print("FINAL RESULT")
    print("=" * 60)
    
    if all_passed:
        print("✓ All tests passed using REST API!")
        print("\n✅ The REST API works perfectly.")
        print("❌ The Python SDK (vertexai.rag) has a bug.")
        print("\n👉 Use gcs_to_rag_upload_rest.py instead of the SDK version:")
        print(f"\n  python gcs_to_rag_upload_rest.py \\")
        print(f"    --corpus-id {args.corpus_id} \\")
        print(f"    --project {args.project} \\")
        print(f"    --metadata-dir ./processed_metadata")
        return 0
    else:
        print("✗ Some tests failed")
        print("\nPlease check:")
        print("  1. Run: gcloud auth application-default login")
        print("  2. Verify project ID is correct")
        print("  3. Check IAM permissions")
        print("  4. Verify corpus ID is correct")
        return 1

if __name__ == '__main__':
    sys.exit(main())
