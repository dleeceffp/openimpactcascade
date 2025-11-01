#!/usr/bin/env python3
"""
Create Vertex AI RAG Corpus for OpenImpactCascade

This script creates a RAG corpus in GCP Vertex AI for the risk assessment platform.
Can be run from Cloud Shell or any environment with gcloud authentication.

Usage:
    python create_rag_corpus.py --project-id PROJECT_ID --display-name CORPUS_NAME
    
Example:
    python create_rag_corpus.py --project-id oicsbx --display-name risk-assessment-kb
"""

import argparse
import sys
import os
from typing import Optional

try:
    from vertexai import rag
    import vertexai
    VERTEXAI_AVAILABLE = True
except ImportError:
    VERTEXAI_AVAILABLE = False
    print("ERROR: vertexai library not installed")
    print("Install with: pip install google-cloud-aiplatform")
    sys.exit(1)


def create_rag_corpus(
    project_id: str,
    display_name: str,
    location: str = "northamerica-northeast1",
    description: Optional[str] = None,
    embedding_model: Optional[str] = None
) -> str:
    """
    Create a RAG corpus in Vertex AI.
    
    Args:
        project_id: GCP project ID
        display_name: Display name for the corpus
        location: GCP region (must support RAG Engine)
        description: Optional description
        embedding_model: Optional embedding model (defaults to text-embedding-005)
        
    Returns:
        Corpus resource name
    """
    
    print(f"Initializing Vertex AI...")
    print(f"  Project: {project_id}")
    print(f"  Location: {location}")
    
    try:
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)
        print("✓ Vertex AI initialized")
    except Exception as e:
        print(f"✗ Failed to initialize Vertex AI: {e}")
        print("\nTroubleshooting:")
        print("  1. Verify project ID is correct")
        print("  2. Ensure Vertex AI API is enabled:")
        print("     gcloud services enable aiplatform.googleapis.com --project=" + project_id)
        print("  3. Check authentication:")
        print("     gcloud auth application-default login")
        sys.exit(1)
    
    print(f"\nCreating RAG Corpus...")
    print(f"  Display Name: {display_name}")
    if description:
        print(f"  Description: {description}")
    if embedding_model:
        print(f"  Embedding Model: {embedding_model}")
    else:
        print(f"  Embedding Model: text-embedding-005 (default)")
    
    try:
        # Configure embedding model
        embedding_config = rag.EmbeddingModelConfig()
        if embedding_model:
            embedding_config.publisher_model = embedding_model
        
        # Create corpus
        corpus = rag.RagCorpus.create(
            display_name=display_name,
            description=description or f"RAG corpus for {display_name}",
            embedding_model_config=embedding_config,
            # Using managed vector database (default)
            # For custom vector DB, add: vector_db_config=rag.RagVectorDbConfig(...)
        )
        
        print(f"\n✓ Successfully created RAG Corpus!")
        print(f"  Corpus Name: {corpus.name}")
        print(f"  Resource ID: {corpus.resource_name}")
        
        return corpus.name
        
    except Exception as e:
        print(f"\n✗ Failed to create RAG corpus: {e}")
        print("\nTroubleshooting:")
        print("  1. Verify location supports RAG Engine:")
        print("     Supported: northamerica-northeast1, us-central1, us-east4, europe-west1, asia-southeast1")
        print("  2. Check IAM permissions:")
        print("     Required role: roles/aiplatform.user")
        print("  3. Verify API is enabled:")
        print("     gcloud services list --enabled --project=" + project_id)
        sys.exit(1)


def list_existing_corpora(project_id: str, location: str = "northamerica-northeast1") -> None:
    """
    List existing RAG corpora in the project.
    
    Args:
        project_id: GCP project ID
        location: GCP region
    """
    print(f"\nListing existing RAG corpora in {project_id}...")
    
    try:
        vertexai.init(project=project_id, location=location)
        
        # List corpora
        corpora = rag.RagCorpus.list()
        
        if not corpora:
            print("  No existing corpora found")
        else:
            print(f"  Found {len(corpora)} corpus(es):")
            for corpus in corpora:
                print(f"    - {corpus.display_name} ({corpus.name})")
                
    except Exception as e:
        print(f"  Warning: Could not list corpora: {e}")


def verify_corpus(corpus_name: str, project_id: str, location: str = "northamerica-northeast1") -> bool:
    """
    Verify that a corpus was created successfully.
    
    Args:
        corpus_name: Corpus resource name
        project_id: GCP project ID
        location: GCP region
        
    Returns:
        True if corpus exists and is accessible
    """
    print(f"\nVerifying corpus creation...")
    
    try:
        vertexai.init(project=project_id, location=location)
        
        # Try to get the corpus
        corpus = rag.RagCorpus(corpus_name)
        
        print(f"✓ Corpus verified successfully")
        print(f"  Display Name: {corpus.display_name}")
        print(f"  State: Ready for document import")
        
        return True
        
    except Exception as e:
        print(f"✗ Corpus verification failed: {e}")
        return False


def main():
    """Main entry point."""
    
    parser = argparse.ArgumentParser(
        description="Create a Vertex AI RAG Corpus for OpenImpactCascade",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create corpus with default settings (Montreal, Canada)
  python create_rag_corpus.py --project-id oicsbx --display-name oic-rarag-kb
  
  # Create corpus with custom location and description
  python create_rag_corpus.py \
    --project-id oicsbx \
    --display-name oic-rarag-kb \
    --location northamerica-northeast1 \
    --description "Knowledge base for cybersecurity risk assessment"
  
  # List existing corpora
  python create_rag_corpus.py --project-id oicsbx --list-only
  
  # Use custom embedding model
  python create_rag_corpus.py \
    --project-id oicsbx \
    --display-name oic-rarag-kb \
    --embedding-model text-embedding-004

Supported Locations:
  - northamerica-northeast1 (Montreal, Canada) - Default
  - us-central1 (Iowa)
  - us-east4 (Virginia)
  - europe-west1 (Belgium)
  - asia-southeast1 (Singapore)
        """
    )
    
    parser.add_argument(
        "--project-id",
        required=True,
        help="GCP project ID (e.g., oicsbx)"
    )
    
    parser.add_argument(
        "--display-name",
        help="Display name for the corpus (e.g., risk-assessment-kb)"
    )
    
    parser.add_argument(
        "--location",
        default="northamerica-northeast1",
        help="GCP region (default: northamerica-northeast1)"
    )
    
    parser.add_argument(
        "--description",
        help="Description of the corpus"
    )
    
    parser.add_argument(
        "--embedding-model",
        help="Embedding model to use (default: text-embedding-005)"
    )
    
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Only list existing corpora, don't create new one"
    )
    
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify corpus after creation"
    )
    
    args = parser.parse_args()
    
    # Check if vertexai is available
    if not VERTEXAI_AVAILABLE:
        print("ERROR: vertexai library not available")
        sys.exit(1)
    
    print("=" * 60)
    print("  Vertex AI RAG Corpus Creation")
    print("  OpenImpactCascade Risk Assessment Platform")
    print("=" * 60)
    
    # List existing corpora if requested
    if args.list_only:
        list_existing_corpora(args.project_id, args.location)
        sys.exit(0)
    
    # Validate required arguments for creation
    if not args.display_name:
        print("\nERROR: --display-name is required for corpus creation")
        print("Use --list-only to only list existing corpora")
        parser.print_help()
        sys.exit(1)
    
    # List existing corpora first
    list_existing_corpora(args.project_id, args.location)
    
    # Create the corpus
    corpus_name = create_rag_corpus(
        project_id=args.project_id,
        display_name=args.display_name,
        location=args.location,
        description=args.description,
        embedding_model=args.embedding_model
    )
    
    # Verify if requested
    if args.verify:
        verify_corpus(corpus_name, args.project_id, args.location)
    
    # Print next steps
    print("\n" + "=" * 60)
    print("  Next Steps")
    print("=" * 60)
    print("\n1. Update your .env.gcp file:")
    print(f"   VERTEX_RAG_CORPUS={args.display_name}")
    print(f"   GCP_REGION={args.location}")
    
    print("\n2. Upload documents to the corpus:")
    print("   python knowledge_base_manager.py")
    
    print("\n3. Test RAG engine:")
    print("   python vertex_rag.py")
    
    print("\n4. Integrate into application:")
    print("   See documentation/VERTEX_RAG_INTEGRATION.md")
    
    print("\n" + "=" * 60)
    print("✓ Corpus creation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
