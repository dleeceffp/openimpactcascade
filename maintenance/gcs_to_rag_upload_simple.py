#!/usr/bin/env python3
"""
Upload GCS documents to Vertex AI RAG Corpus (SIMPLIFIED API VERSION)

This version uses the simplest possible API call to avoid parameter issues.
"""

import os
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import time

# Google Cloud
from google.cloud import storage
from google.auth import default
from google.auth.exceptions import DefaultCredentialsError
from vertexai import rag
import vertexai

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RAGCorpusUploader:
    """Upload documents from GCS to Vertex AI RAG corpus."""
    
    def __init__(
        self,
        corpus_display_name: str,
        project_id: str,
        location: str = "northamerica-northeast1",
        metadata_dir: str = "./processed_metadata",
        corpus_id: Optional[str] = None
    ):
        """Initialize uploader."""
        self.corpus_display_name = corpus_display_name
        self.project_id = project_id
        self.location = location
        self.metadata_dir = Path(metadata_dir)
        self.corpus_id = corpus_id
        
        # Initialize authentication
        logger.info("Initializing authentication...")
        self._init_auth()
        
        # Find or construct corpus
        if corpus_id:
            logger.info(f"Using corpus ID: {corpus_id}")
            corpus_name = f"projects/{project_id}/locations/{location}/ragCorpora/{corpus_id}"
            self.corpus = self._get_corpus_by_name(corpus_name)
        else:
            logger.info(f"Looking up corpus by display name: {corpus_display_name}")
            self.corpus = self._find_corpus()
            
        if not self.corpus:
            raise ValueError(f"Corpus '{corpus_display_name}' not found")
        
        logger.info(f"✓ Found corpus: {self.corpus.name}")
        logger.info(f"  Display name: {self.corpus.display_name}")
        
        # Progress tracking
        self.progress_file = self.metadata_dir / "upload_progress.json"
        self.uploaded_files = self._load_progress()
        
        logger.info(f"Previously uploaded: {len(self.uploaded_files)} files")
    
    def _init_auth(self):
        """Initialize authentication."""
        try:
            credentials, auth_project = default()
            logger.info(f"✓ Authentication successful")
            logger.info(f"  Auth project: {auth_project}")
            logger.info(f"  Credentials type: {type(credentials).__name__}")
            
            vertexai.init(
                project=self.project_id,
                location=self.location,
                credentials=credentials
            )
            
            self.storage_client = storage.Client(
                project=self.project_id,
                credentials=credentials
            )
            
        except DefaultCredentialsError as e:
            logger.error("=" * 60)
            logger.error("AUTHENTICATION ERROR")
            logger.error("=" * 60)
            logger.error("Could not find credentials.")
            logger.error("\nPlease ensure GOOGLE_APPLICATION_CREDENTIALS is set")
            logger.error("=" * 60)
            raise
        except Exception as e:
            logger.error(f"Unexpected authentication error: {e}")
            raise
    
    def _get_corpus_by_name(self, corpus_name: str):
        """Get corpus by full name."""
        try:
            return rag.get_corpus(name=corpus_name)
        except Exception as e:
            logger.error(f"Error getting corpus by name: {e}")
            return None
    
    def _find_corpus(self):
        """Find corpus by display name."""
        try:
            logger.info("Listing corpora...")
            corpora_pager = rag.list_corpora()
            
            corpora_list = list(corpora_pager)
            logger.info(f"Found {len(corpora_list)} total corpora")
            
            for corpus in corpora_list:
                if corpus.display_name == self.corpus_display_name:
                    return corpus
            
            logger.error(f"No corpus found with display name: {self.corpus_display_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error listing corpora: {e}")
            raise
    
    def _load_progress(self) -> set:
        """Load upload progress."""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                data = json.load(f)
                return set(data.get('uploaded_files', []))
        return set()
    
    def _save_progress(self):
        """Save upload progress."""
        with open(self.progress_file, 'w') as f:
            json.dump({
                'uploaded_files': list(self.uploaded_files),
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
    
    def load_metadata_files(self) -> List[Dict]:
        """Load all metadata files."""
        metadata_files = []
        
        for metadata_path in self.metadata_dir.glob("*.metadata.json"):
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    metadata['_metadata_path'] = str(metadata_path)
                    metadata_files.append(metadata)
            except Exception as e:
                logger.error(f"Error loading {metadata_path}: {e}")
        
        logger.info(f"Loaded {len(metadata_files)} metadata files")
        return metadata_files
    
    def upload_document(self, metadata: Dict) -> bool:
        """Upload single document to RAG corpus."""
        
        gcs_path = metadata.get('gcs_path')
        if not gcs_path:
            logger.error("No gcs_path in metadata")
            return False
        
        # Skip if already uploaded
        if gcs_path in self.uploaded_files:
            logger.info(f"Skipping already uploaded: {gcs_path}")
            return True
        
        logger.info(f"Uploading: {gcs_path}")
        
        try:
            # Build GCS URI
            gcs_uri = metadata.get('gcs_url', f"gs://{metadata['gcs_bucket']}/{gcs_path}")
            
            # SIMPLIFIED: Use minimal parameters - let SDK use defaults
            response = rag.import_files(
                corpus_name=self.corpus.name,
                paths=[gcs_uri]
            )
            
            logger.info(f"  ✓ Uploaded: {gcs_path}")
            
            # Mark as uploaded
            self.uploaded_files.add(gcs_path)
            self._save_progress()
            
            return True
            
        except Exception as e:
            logger.error(f"Error uploading {gcs_path}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def upload_batch(
        self,
        metadata_list: List[Dict],
        batch_size: int = 10,
        delay_seconds: float = 2.0
    ):
        """Upload documents in batches."""
        
        # Filter out already uploaded
        to_upload = [m for m in metadata_list if m.get('gcs_path') not in self.uploaded_files]
        
        logger.info(f"Uploading {len(to_upload)} documents in batches of {batch_size}...")
        
        successful = 0
        failed = 0
        
        for i in range(0, len(to_upload), batch_size):
            batch = to_upload[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(to_upload) - 1) // batch_size + 1
            
            logger.info(f"\nBatch {batch_num}/{total_batches}")
            
            for metadata in batch:
                if self.upload_document(metadata):
                    successful += 1
                else:
                    failed += 1
            
            # Rate limiting between batches
            if i + batch_size < len(to_upload):
                logger.info(f"  Waiting {delay_seconds} seconds...")
                time.sleep(delay_seconds)
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("Upload Complete!")
        logger.info("="*60)
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Total uploaded: {len(self.uploaded_files)}")
        logger.info("="*60)
    
    def verify_uploads(self, sample_size: int = 5):
        """Verify uploads by testing retrieval."""
        logger.info(f"\nVerifying uploads with {sample_size} sample queries...")
        
        test_queries = [
            "ransomware healthcare",
            "MITRE ATT&CK techniques",
            "vulnerability management",
            "incident response",
            "risk assessment"
        ][:sample_size]
        
        for query in test_queries:
            try:
                response = rag.retrieval_query(
                    rag_resources=[
                        rag.RagResource(rag_corpus=self.corpus.name)
                    ],
                    text=query
                )
                
                count = len(response.contexts.contexts) if response.contexts else 0
                logger.info(f"  Query: '{query}' → {count} results")
                
            except Exception as e:
                logger.error(f"  Query failed: {e}")
        
        logger.info("\n✓ Verification complete")


def main():
    """Main entry point."""
    
    parser = argparse.ArgumentParser(
        description="Upload GCS documents to Vertex AI RAG corpus",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--corpus', help='RAG corpus display name')
    parser.add_argument('--corpus-id', help='RAG corpus ID (faster than display name)')
    parser.add_argument('--project', required=True, help='GCP project ID')
    parser.add_argument('--location', default='northamerica-northeast1', help='GCP region')
    parser.add_argument('--metadata-dir', default='./processed_metadata', help='Metadata directory')
    parser.add_argument('--batch-size', type=int, default=10, help='Documents per batch')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between batches (seconds)')
    parser.add_argument('--verify', action='store_true', help='Verify uploads after completion')
    parser.add_argument('--resume', action='store_true', help='Resume from previous run')
    
    args = parser.parse_args()
    
    if not args.corpus and not args.corpus_id:
        parser.error("Either --corpus or --corpus-id must be specified")
    
    # Initialize uploader
    try:
        uploader = RAGCorpusUploader(
            corpus_display_name=args.corpus or "unknown",
            project_id=args.project,
            location=args.location,
            metadata_dir=args.metadata_dir,
            corpus_id=args.corpus_id
        )
    except Exception as e:
        logger.error(f"Failed to initialize uploader: {e}")
        return 1
    
    # Load metadata
    metadata_list = uploader.load_metadata_files()
    
    if not metadata_list:
        logger.error("No metadata files found")
        return 1
    
    # Upload documents
    uploader.upload_batch(
        metadata_list=metadata_list,
        batch_size=args.batch_size,
        delay_seconds=args.delay
    )
    
    # Verify if requested
    if args.verify:
        uploader.verify_uploads()
    
    return 0


if __name__ == '__main__':
    exit(main())
