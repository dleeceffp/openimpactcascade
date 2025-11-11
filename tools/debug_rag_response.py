"""
Debug script to troubleshoot RAG retrieval responses.
This will show us exactly what the API is returning.
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
print("RAG Response Debug Tool")
print("="*80)
print(f"Project: {project_id}")
print(f"Location: {location}")
print(f"Corpus: {corpus_name}")
print()

# Load credentials
if key_path and os.path.exists(key_path):
    credentials = service_account.Credentials.from_service_account_file(
        key_path,
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    vertexai.init(project=project_id, location=location, credentials=credentials)
    print("✅ Using service account authentication")
else:
    vertexai.init(project=project_id, location=location)
    print("✅ Using ADC authentication")

print()

# Find corpus
print("Finding corpus...")
corpora_pager = rag.list_corpora()
corpora_list = list(corpora_pager)

target_corpus = None
for corpus in corpora_list:
    if corpus.display_name == corpus_name:
        target_corpus = corpus
        print(f"✅ Found corpus: {corpus.name}")
        break

if not target_corpus:
    print("❌ Corpus not found!")
    print(f"Available corpora: {[c.display_name for c in corpora_list]}")
    exit(1)

print()

# Test query
test_query = "cybersecurity threats vulnerabilities Healthcare industry Canada region"
print(f"Test Query: {test_query}")
print()

# Make API call
print("Making API call...")
try:
    response = rag.retrieval_query(
        rag_resources=[
            rag.RagResource(
                rag_corpus=target_corpus.name,
            )
        ],
        text=test_query
    )
    
    print("✅ API call successful")
    print()
    
    # Debug: Show response structure
    print("="*80)
    print("RESPONSE STRUCTURE")
    print("="*80)
    print(f"Response type: {type(response)}")
    print(f"Response dir: {[x for x in dir(response) if not x.startswith('_')]}")
    print()
    
    # Check for contexts
    print("="*80)
    print("CONTEXTS CHECK")
    print("="*80)
    
    if hasattr(response, 'contexts'):
        print(f"✅ response.contexts exists")
        print(f"   Type: {type(response.contexts)}")
        print(f"   Dir: {[x for x in dir(response.contexts) if not x.startswith('_')]}")
        print()
        
        if hasattr(response.contexts, 'contexts'):
            print(f"✅ response.contexts.contexts exists")
            contexts_list = response.contexts.contexts
            print(f"   Type: {type(contexts_list)}")
            print(f"   Length: {len(contexts_list)}")
            print()
            
            if len(contexts_list) > 0:
                print("="*80)
                print("FIRST CONTEXT DETAILS")
                print("="*80)
                ctx = contexts_list[0]
                print(f"Context type: {type(ctx)}")
                print(f"Context attributes: {[x for x in dir(ctx) if not x.startswith('_')]}")
                print()
                
                # Try different attribute names
                for attr in ['distance', 'score', 'relevance_score', 'similarity_score']:
                    if hasattr(ctx, attr):
                        print(f"✅ {attr}: {getattr(ctx, attr)}")
                    else:
                        print(f"❌ {attr}: not found")
                
                print()
                
                for attr in ['text', 'content', 'chunk', 'passage']:
                    if hasattr(ctx, attr):
                        val = getattr(ctx, attr)
                        print(f"✅ {attr}: {val[:200] if val else 'None'}...")
                    else:
                        print(f"❌ {attr}: not found")
                
                print()
                
                for attr in ['source_uri', 'source', 'uri', 'document_id']:
                    if hasattr(ctx, attr):
                        print(f"✅ {attr}: {getattr(ctx, attr)}")
                    else:
                        print(f"❌ {attr}: not found")
                
                print()
                print("="*80)
                print("FULL CONTEXT OBJECT")
                print("="*80)
                print(ctx)
                
            else:
                print("⚠️  contexts list is empty!")
                print()
                print("This means the API returned successfully but found no matches.")
                print()
                print("Possible reasons:")
                print("1. Query doesn't match any documents in the corpus")
                print("2. Corpus is empty or not properly indexed")
                print("3. Query processing/embedding failed")
        else:
            print("❌ response.contexts.contexts does not exist")
            print("   Available on response.contexts:", dir(response.contexts))
    else:
        print("❌ response.contexts does not exist")
        print("   Available on response:", dir(response))
    
    print()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print()
print("="*80)
print("Debug Complete")
print("="*80)
