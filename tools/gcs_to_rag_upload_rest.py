#!/usr/bin/env python3
"""
Upload GCS documents to Vertex AI RAG Corpus using REST API

This version bypasses the buggy vertexai.rag SDK and uses REST API directly.
Works around the "string indices must be integers" error.

Usage:
    python gcs_to_rag_upload_rest.py \\
        --corpus-id 6917529027641081856 \\
        --metadata-dir ./processed_metadata \\
        --project oicsbx \\
        --location northamerica-northeast1
"""

import os
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import time
import requests

# Google Auth only
from google.auth import default
from google.auth.transport.requests import Request

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RAGCorpusUploaderREST:
    """Upload documents from GCS to Vertex AI RAG corpus using REST API."""
    
    def __init__(
        self,
        corpus_id: str,
        project_id: str,
        location: str = "northamerica-northeast1",
        metadata_dir: str = "./processed_metadata"
    ):
        """
        Initialize uploader.
        
        Args:
            corpus_id: RAG corpus ID (not display name)
            project_id: GCP project ID
            location: GCP region
            metadata_dir: Directory with metadata files
        """
        self.corpus_id = corpus_id
        self.project_id = project_id
        self.location = location
        self.metadata_dir = Path(metadata_dir)
        
        # Build corpus name
        self.corpus_name = f"projects/{project_id}/locations/{location}/ragCorpora/{corpus_id}"
        
        # API endpoint
        self.api_base = f"https://{location}-aiplatform.googleapis.com/v1"
        
        # Initialize authentication
        logger.info("Initializing authentication...")
        self._init_auth()
        
        # Verify corpus exists
        logger.info(f"Verifying corpus: {corpus_id}")
        corpus_info = self._get_corpus()
        if not corpus_info:
            raise ValueError(f"Corpus '{corpus_id}' not found or not accessible")
        
        logger.info(f"✓ Found corpus: {corpus_info.get('displayName', 'Unknown')}")
        logger.info(f"  State: {corpus_info.get('corpusStatus', {}).get('state', 'Unknown')}")
        
        # Progress tracking
        self.progress_file = self.metadata_dir / "upload_progress.json"
        self.uploaded_files = self._load_progress()
        
        logger.info(f"Previously uploaded: {len(self.uploaded_files)} files")
    
    def _init_auth(self):
        """Initialize authentication."""
        try:
            self.credentials, auth_project = default()
            logger.info(f"✓ Authentication successful")
            logger.info(f"  Auth project: {auth_project}")
            logger.info(f"  Credentials type: {type(self.credentials).__name__}")
            
            # Get initial token
            if not self.credentials.valid:
                self.credentials.refresh(Request())
            
        except Exception as e:
            logger.error("=" * 60)
            logger.error("AUTHENTICATION ERROR")
            logger.error("=" * 60)
            logger.error(f"Error: {e}")
            logger.error("\nPlease run:")
            logger.error("  gcloud auth application-default login")
            logger.error("=" * 60)
            raise
    
    def _get_access_token(self) -> str:
        """Get valid access token."""
        if not self.credentials.valid:
            self.credentials.refresh(Request())
        return self.credentials.token
    
    def _make_request(self, method: str, url: str, json_data: dict = None) -> dict:
        """Make authenticated API request."""
        headers = {
            'Authorization': f'Bearer {self._get_access_token()}',
            'Content-Type': 'application/json'
        }
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=json_data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json() if response.content else {}
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error: {e}")
            logger.error(f"Response: {e.response.text if e.response else 'No response'}")
            raise
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise
    
    def _get_corpus(self) -> Optional[dict]:
        """Get corpus information."""
        url = f"{self.api_base}/{self.corpus_name}"
        try:
            return self._make_request('GET', url)
        except Exception as e:
            logger.error(f"Failed to get corpus: {e}")
            return None
    
    def _list_corpus_files(self) -> List[dict]:
        """List files in corpus."""
        url = f"{self.api_base}/{self.corpus_name}/ragFiles"
        try:
            response = self._make_request('GET', url)
            return response.get('ragFiles', [])
        except Exception as e:
            logger.error(f"Failed to list corpus files: {e}")
            return []
    
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
        """
        Load all metadata files.
        
        Returns:
            List of metadata dictionaries with file paths
        """
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
        """
        Upload single document to RAG corpus.
        
        Args:
            metadata: Document metadata
            
        Returns:
            True if successful
        """
        
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
            
            # Import files using REST API
            url = f"{self.api_base}/{self.corpus_name}/ragFiles:import"
            
            payload = {
                "import_rag_files_config": {
                    "gcs_source": {
                        "uris": [gcs_uri]
                    },
                    "rag_file_chunking_config": {
                        "chunk_size": 512,
                        "chunk_overlap": 100
                    }
                }
            }
            
            response = self._make_request('POST', url, payload)
            
            logger.info(f"  ✓ Uploaded: {gcs_path}")
            logger.info(f"    Response: {response.get('name', 'Operation started')}")
            
            # Mark as uploaded
            self.uploaded_files.add(gcs_path)
            self._save_progress()
            
            return True
            
        except Exception as e:
            logger.error(f"Error uploading {gcs_path}: {e}")
            return False
    
    def upload_batch(
        self,
        metadata_list: List[Dict],
        batch_size: int = 10,
        delay_seconds: float = 2.0
    ):
        """
        Upload documents in batches.
        
        Args:
            metadata_list: List of metadata dictionaries
            batch_size: Documents per batch
            delay_seconds: Delay between batches
        """
        
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
    
    def verify_uploads(self):
        """Verify uploads by listing files."""
        logger.info(f"\nVerifying uploads...")
        
        files = self._list_corpus_files()
        logger.info(f"  Files in corpus: {len(files)}")
        
        if files:
            logger.info("\n  Sample files:")
            for i, file_info in enumerate(files[:5], 1):
                name = file_info.get('name', 'Unknown')
                display_name = file_info.get('displayName', 'N/A')
                logger.info(f"    {i}. {display_name}")
        
        logger.info("\n✓ Verification complete")


def main():
    """Main entry point."""
    
    parser = argparse.ArgumentParser(
        description="Upload GCS documents to Vertex AI RAG corpus using REST API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload all processed documents
  python gcs_to_rag_upload_rest.py \\
    --corpus-id 6917529027641081856 \\
    --metadata-dir ./processed_metadata \\
    --project oicsbx \\
    --location northamerica-northeast1

  # Upload with custom batch size
  python gcs_to_rag_upload_rest.py \\
    --corpus-id 6917529027641081856 \\
    --metadata-dir ./processed_metadata \\
    --project oicsbx \\
    --batch-size 20

  # Resume previous upload
  python gcs_to_rag_upload_rest.py \\
    --corpus-id 6917529027641081856 \\
    --metadata-dir ./processed_metadata \\
    --project oicsbx \\
    --resume
        """
    )
    
    parser.add_argument(
        '--corpus-id',
        required=True,
        help='RAG corpus ID (e.g., 6917529027641081856)'
    )
    
    parser.add_argument(
        '--project',
        required=True,
        help='GCP project ID'
    )
    
    parser.add_argument(
        '--location',
        default='northamerica-northeast1',
        help='GCP region (default: northamerica-northeast1)'
    )
    
    parser.add_argument(
        '--metadata-dir',
        default='./processed_metadata',
        help='Directory with metadata files'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Documents per batch'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=2.0,
        help='Delay between batches (seconds)'
    )
    
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify uploads after completion'
    )
    
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from previous run'
    )
    
    args = parser.parse_args()
    
    # Initialize uploader
    try:
        uploader = RAGCorpusUploaderREST(
            corpus_id=args.corpus_id,
            project_id=args.project,
            location=args.location,
            metadata_dir=args.metadata_dir
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
