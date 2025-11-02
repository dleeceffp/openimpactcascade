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
            logger.info("="*60)
            logger.info("AUTHENTICATION")
            logger.info("="*60)
            
            credentials, auth_project = default()
            logger.info(f"✓ Authentication successful")
            logger.info(f"  Auth project: {auth_project}")
            logger.info(f"  Target project: {self.project_id}")
            logger.info(f"  Credentials type: {type(credentials).__name__}")
            logger.info(f"  Credentials valid: {credentials.valid}")
            
            logger.info(f"\nInitializing Vertex AI...")
            logger.info(f"  Project: {self.project_id}")
            logger.info(f"  Location: {self.location}")
            
            vertexai.init(
                project=self.project_id,
                location=self.location,
                credentials=credentials
            )
            logger.info(f"✓ Vertex AI initialized")
            
            logger.info(f"\nInitializing Storage client...")
            self.storage_client = storage.Client(
                project=self.project_id,
                credentials=credentials
            )
            logger.info(f"✓ Storage client initialized")
            logger.info("="*60)
            
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
            logger.info("="*60)
            logger.info("FINDING CORPUS")
            logger.info("="*60)
            logger.info(f"Looking for: {self.corpus_display_name}")
            logger.info(f"Listing corpora in {self.project_id}/{self.location}...")
            
            corpora_pager = rag.list_corpora()
            corpora_list = list(corpora_pager)
            
            logger.info(f"\nFound {len(corpora_list)} total corpora:")
            for i, corpus in enumerate(corpora_list, 1):
                logger.info(f"  {i}. {corpus.display_name}")
                logger.info(f"     Name: {corpus.name}")
                if corpus.display_name == self.corpus_display_name:
                    logger.info(f"     ✓ MATCH!")
                    logger.info("="*60)
                    return corpus
            
            logger.error(f"\n✗ No corpus found with display name: {self.corpus_display_name}")
            logger.info("="*60)
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
        logger.info("="*60)
        logger.info("LOADING METADATA FILES")
        logger.info("="*60)
        logger.info(f"Metadata directory: {self.metadata_dir}")
        logger.info(f"Directory exists: {self.metadata_dir.exists()}")
        
        if not self.metadata_dir.exists():
            logger.error(f"✗ Metadata directory does not exist: {self.metadata_dir}")
            return []
        
        metadata_files = []
        all_json_files = list(self.metadata_dir.glob("*.metadata.json"))
        logger.info(f"Found {len(all_json_files)} .metadata.json files")
        
        for i, metadata_path in enumerate(all_json_files, 1):
            try:
                logger.info(f"  Loading {i}/{len(all_json_files)}: {metadata_path.name}")
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    metadata['_metadata_path'] = str(metadata_path)
                    
                    # Debug: show key fields
                    gcs_path = metadata.get('gcs_path', 'MISSING')
                    gcs_bucket = metadata.get('gcs_bucket', 'MISSING')
                    logger.info(f"    GCS bucket: {gcs_bucket}")
                    logger.info(f"    GCS path: {gcs_path}")
                    
                    metadata_files.append(metadata)
            except Exception as e:
                logger.error(f"  ✗ Error loading {metadata_path}: {e}")
        
        logger.info(f"\n✓ Successfully loaded {len(metadata_files)} metadata files")
        logger.info("="*60)
        return metadata_files
    
    def upload_document(self, metadata: Dict) -> bool:
        """Upload single document to RAG corpus."""
        
        logger.info("\n" + "-"*60)
        
        gcs_path = metadata.get('gcs_path')
        if not gcs_path:
            logger.error("✗ No gcs_path in metadata")
            logger.error(f"   Metadata keys: {list(metadata.keys())}")
            return False
        
        # Skip if already uploaded
        if gcs_path in self.uploaded_files:
            logger.info(f"⊘ Skipping already uploaded: {gcs_path}")
            return True
        
        logger.info(f"📤 UPLOADING DOCUMENT")
        logger.info(f"   GCS path: {gcs_path}")
        
        try:
            # Build GCS URI
            gcs_bucket = metadata.get('gcs_bucket')
            if not gcs_bucket:
                logger.error("✗ No gcs_bucket in metadata")
                return False
            
            gcs_uri = metadata.get('gcs_url', f"gs://{gcs_bucket}/{gcs_path}")
            logger.info(f"   GCS URI: {gcs_uri}")
            
            # Verify file exists in GCS
            logger.info(f"   Verifying file exists in GCS...")
            try:
                bucket = self.storage_client.bucket(gcs_bucket)
                blob = bucket.blob(gcs_path)
                if not blob.exists():
                    logger.error(f"✗ File does not exist in GCS: {gcs_uri}")
                    return False
                logger.info(f"   ✓ File exists (size: {blob.size} bytes)")
            except Exception as e:
                logger.error(f"✗ Error checking GCS file: {e}")
                return False
            
            # Import to RAG corpus
            logger.info(f"   Calling rag.import_files()...")
            logger.info(f"   Corpus: {self.corpus.name}")
            logger.info(f"   Path: {gcs_uri}")
            
            response = rag.import_files(
                corpus_name=self.corpus.name,
                paths=[gcs_uri]
            )
            
            logger.info(f"   Response type: {type(response)}")
            logger.info(f"   Response: {response}")
            
            # Check if response indicates success
            if hasattr(response, 'name'):
                logger.info(f"   Operation name: {response.name}")
            if hasattr(response, 'done'):
                logger.info(f"   Operation done: {response.done}")
            if hasattr(response, 'error'):
                if response.error:
                    logger.error(f"   ✗ Operation error: {response.error}")
                    return False
            
            logger.info(f"   ✓ Import call successful")
            
            # Mark as uploaded
            self.uploaded_files.add(gcs_path)
            self._save_progress()
            logger.info(f"   ✓ Progress saved")
            
            logger.info(f"✓ UPLOAD COMPLETE: {gcs_path}")
            return True
            
        except Exception as e:
            logger.error(f"✗ ERROR uploading {gcs_path}")
            logger.error(f"   Exception type: {type(e).__name__}")
            logger.error(f"   Exception message: {e}")
            import traceback
            logger.error("   Full traceback:")
            for line in traceback.format_exc().split('\n'):
                logger.error(f"   {line}")
            return False
    
    def upload_batch(
        self,
        metadata_list: List[Dict],
        batch_size: int = 10,
        delay_seconds: float = 2.0
    ):
        """Upload documents in batches."""
        
        logger.info("\n" + "="*60)
        logger.info("UPLOAD BATCH")
        logger.info("="*60)
        logger.info(f"Total metadata files: {len(metadata_list)}")
        logger.info(f"Already uploaded: {len(self.uploaded_files)}")
        
        # Filter out already uploaded
        to_upload = [m for m in metadata_list if m.get('gcs_path') not in self.uploaded_files]
        
        logger.info(f"Documents to upload: {len(to_upload)}")
        logger.info(f"Batch size: {batch_size}")
        logger.info(f"Delay between batches: {delay_seconds}s")
        
        if not to_upload:
            logger.info("\n✓ All documents already uploaded!")
            return
        
        logger.info("="*60)
        
        successful = 0
        failed = 0
        
        for i in range(0, len(to_upload), batch_size):
            batch = to_upload[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(to_upload) - 1) // batch_size + 1
            
            logger.info(f"\n" + "="*60)
            logger.info(f"BATCH {batch_num}/{total_batches}")
            logger.info(f"Documents in this batch: {len(batch)}")
            logger.info("="*60)
            
            for j, metadata in enumerate(batch, 1):
                logger.info(f"\n[Batch {batch_num}, Doc {j}/{len(batch)}]")
                if self.upload_document(metadata):
                    successful += 1
                else:
                    failed += 1
                
                # Delay between individual uploads
                if j < len(batch):
                    logger.info(f"   ⏱️  Waiting 2 seconds before next document...")
                    time.sleep(15.0)
            
            # Rate limiting between batches
            if i + batch_size < len(to_upload):
                logger.info(f"\n⏱️  Waiting {delay_seconds} seconds before next batch...")
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
    
    print("="*60)
    print("GCS TO RAG CORPUS UPLOADER")
    print("="*60)
    print(f"Start time: {datetime.now().isoformat()}")
    print("="*60)
    
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
        logger.info("\nInitializing uploader...")
        logger.info(f"  Corpus: {args.corpus or args.corpus_id}")
        logger.info(f"  Project: {args.project}")
        logger.info(f"  Location: {args.location}")
        logger.info(f"  Metadata dir: {args.metadata_dir}")
        
        uploader = RAGCorpusUploader(
            corpus_display_name=args.corpus or "unknown",
            project_id=args.project,
            location=args.location,
            metadata_dir=args.metadata_dir,
            corpus_id=args.corpus_id
        )
        logger.info("✓ Uploader initialized successfully")
    except Exception as e:
        logger.error(f"\n✗ Failed to initialize uploader: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    
    # Load metadata
    logger.info("\nLoading metadata files...")
    metadata_list = uploader.load_metadata_files()
    
    if not metadata_list:
        logger.error("\n✗ No metadata files found")
        logger.error(f"   Check directory: {args.metadata_dir}")
        return 1
    
    logger.info(f"✓ Loaded {len(metadata_list)} metadata files")
    
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
