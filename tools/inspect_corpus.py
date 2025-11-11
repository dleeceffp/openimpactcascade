"""
Check what's actually in the RAG corpus.
"""

import os
from vertexai import rag
import vertexai
from google.oauth2 import service_account

# Initialize
project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
location = os.environ.get('GCP_REGION', 'us-east1')
corpus_name = os.environ.get('VERTEX_RAG_CORPUS')
key_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

print("="*80)
print("RAG Corpus Inspection Tool")
print("="*80)
print()

# Load credentials
if key_path and os.path.exists(key_path):
    credentials = service_account.Credentials.from_service_account_file(
        key_path,
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    vertexai.init(project=project_id, location=location, credentials=credentials)
else:
    vertexai.init(project=project_id, location=location)

# Find corpus
corpora_pager = rag.list_corpora()
corpora_list = list(corpora_pager)

print(f"Found {len(corpora_list)} corpora in project")
print()

target_corpus = None
for corpus in corpora_list:
    print(f"Corpus: {corpus.display_name}")
    print(f"  Name: {corpus.name}")
    
    if corpus.display_name == corpus_name:
        target_corpus = corpus
        print(f"  👉 THIS IS YOUR TARGET CORPUS")
    
    # Show corpus details
    print(f"  Attributes: {[x for x in dir(corpus) if not x.startswith('_')]}")
    
    # Try to get file count
    for attr in ['file_count', 'files', 'documents', 'chunks']:
        if hasattr(corpus, attr):
            val = getattr(corpus, attr)
            print(f"  {attr}: {val}")
    
    print()

if not target_corpus:
    print("❌ Target corpus not found!")
    exit(1)

print("="*80)
print("CHECKING CORPUS FILES")
print("="*80)
print()

# Try to list files in corpus
try:
    print(f"Attempting to list files in: {target_corpus.name}")
    
    # Try different methods to get files
    if hasattr(rag, 'list_rag_files'):
        print("Using rag.list_rag_files()...")
        files = rag.list_rag_files(corpus_name=target_corpus.name)
        files_list = list(files)
        print(f"Found {len(files_list)} files")
        
        for i, f in enumerate(files_list[:5], 1):
            print(f"\nFile {i}:")
            print(f"  Attributes: {[x for x in dir(f) if not x.startswith('_')]}")
            for attr in ['name', 'display_name', 'size_bytes', 'create_time']:
                if hasattr(f, attr):
                    print(f"  {attr}: {getattr(f, attr)}")
    
    elif hasattr(target_corpus, 'list_files'):
        print("Using corpus.list_files()...")
        files = target_corpus.list_files()
        files_list = list(files)
        print(f"Found {len(files_list)} files")
    
    else:
        print("⚠️  No method found to list files")
        print(f"Available methods on rag module: {[x for x in dir(rag) if 'list' in x.lower()]}")

except Exception as e:
    print(f"Error listing files: {e}")
    import traceback
    traceback.print_exc()

print()
print("="*80)
print("TESTING SIMPLE QUERY")
print("="*80)
print()

# Try a very simple query
simple_queries = [
    "healthcare",
    "cybersecurity",
    "threat",
    "risk"
]

for query in simple_queries:
    print(f"Query: '{query}'")
    try:
        response = rag.retrieval_query(
            rag_resources=[
                rag.RagResource(
                    rag_corpus=target_corpus.name,
                )
            ],
            text=query
        )
        
        # Count results
        if hasattr(response, 'contexts') and response.contexts:
            if hasattr(response.contexts, 'contexts'):
                count = len(response.contexts.contexts)
                print(f"  Results: {count}")
                if count > 0:
                    print(f"  ✅ Got results!")
            else:
                print(f"  ⚠️  No contexts.contexts attribute")
        else:
            print(f"  ⚠️  No contexts attribute")
    
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print()

print("="*80)
print("Inspection Complete")
print("="*80)
