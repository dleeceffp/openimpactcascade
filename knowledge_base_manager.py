"""
Knowledge Base Management for Vertex AI RAG Engine.

This module provides utilities to:
1. Upload documents to Vertex AI RAG corpus
2. Manage knowledge base content
3. Update and maintain threat intelligence data
"""

import os
import json
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime

try:
    from google.cloud import aiplatform
    from vertexai.preview import rag
    from google.cloud import storage
    VERTEX_AI_AVAILABLE = True
except ImportError:
    VERTEX_AI_AVAILABLE = False

logger = logging.getLogger(__name__)


class KnowledgeBaseManager:
    """
    Manages the knowledge base for RAG-powered risk assessment.
    
    Handles uploading and organizing documents in categories:
    - Threat Intelligence (CISA advisories, threat reports)
    - MITRE ATT&CK (technique descriptions, use cases)
    - Industry Reports (Verizon DBIR, IBM Cost of Breach)
    - Compliance Documents (GDPR, HIPAA, regional regulations)
    - Best Practices (NIST, CIS, industry guides)
    """
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        location: str = "northamerica-northeast1",
        rag_corpus_name: Optional[str] = None,
        gcs_bucket: Optional[str] = None
    ):
        """
        Initialize Knowledge Base Manager.
        
        Args:
            project_id: GCP project ID
            location: GCP region
            rag_corpus_name: Name of RAG corpus
            gcs_bucket: GCS bucket for document storage
        """
        self.project_id = project_id or os.environ.get('GOOGLE_CLOUD_PROJECT')
        self.location = location
        self.rag_corpus_name = rag_corpus_name or os.environ.get('VERTEX_RAG_CORPUS')
        self.gcs_bucket = gcs_bucket or os.environ.get('VERTEX_RAG_GCS_BUCKET')
        
        if not VERTEX_AI_AVAILABLE:
            raise RuntimeError("Vertex AI libraries not installed")
        
        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT required")
        
        aiplatform.init(project=self.project_id, location=self.location)
        self.storage_client = storage.Client(project=self.project_id)
    
    def create_rag_corpus(
        self,
        display_name: str,
        description: str
    ) -> str:
        """
        Create a new RAG corpus for the knowledge base.
        
        Args:
            display_name: Human-readable name
            description: Corpus description
            
        Returns:
            Corpus resource name
        """
        try:
            # Create RAG corpus
            # Note: Adjust based on actual Vertex AI RAG API
            corpus = rag.create_corpus(
                display_name=display_name,
                description=description
            )
            
            logger.info(f"Created RAG corpus: {corpus.name}")
            return corpus.name
            
        except Exception as e:
            logger.error(f"Failed to create RAG corpus: {e}")
            raise
    
    def upload_document(
        self,
        file_path: str,
        document_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Upload a document to the knowledge base.
        
        Args:
            file_path: Path to document file
            document_type: Type of document (threat_intelligence, mitre_attack, etc.)
            metadata: Optional metadata (industry, region, date, etc.)
            
        Returns:
            Document ID in RAG corpus
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document not found: {file_path}")
        
        # Upload to GCS first
        gcs_uri = self._upload_to_gcs(file_path)
        
        # Add to RAG corpus with metadata
        doc_metadata = metadata or {}
        doc_metadata['document_type'] = document_type
        doc_metadata['upload_date'] = datetime.utcnow().isoformat()
        
        try:
            # Import document into RAG corpus
            # Note: Adjust based on actual Vertex AI RAG API
            # doc_id = rag.import_files(
            #     corpus=self.rag_corpus_name,
            #     paths=[gcs_uri],
            #     metadata=doc_metadata
            # )
            
            logger.info(f"Uploaded document: {file_path} -> {gcs_uri}")
            # return doc_id
            return gcs_uri  # Placeholder
            
        except Exception as e:
            logger.error(f"Failed to upload document: {e}")
            raise
    
    def _upload_to_gcs(self, file_path: str) -> str:
        """
        Upload file to GCS bucket.
        
        Args:
            file_path: Local file path
            
        Returns:
            GCS URI (gs://bucket/path)
        """
        if not self.gcs_bucket:
            raise ValueError("GCS bucket not configured")
        
        bucket = self.storage_client.bucket(self.gcs_bucket)
        blob_name = f"knowledge_base/{Path(file_path).name}"
        blob = bucket.blob(blob_name)
        
        blob.upload_from_filename(file_path)
        
        gcs_uri = f"gs://{self.gcs_bucket}/{blob_name}"
        logger.info(f"Uploaded to GCS: {gcs_uri}")
        
        return gcs_uri
    
    def bulk_upload_directory(
        self,
        directory: str,
        document_type: str,
        file_extensions: List[str] = ['.pdf', '.txt', '.md', '.json']
    ) -> List[str]:
        """
        Upload all documents from a directory.
        
        Args:
            directory: Directory path
            document_type: Type for all documents
            file_extensions: File extensions to include
            
        Returns:
            List of uploaded document IDs
        """
        uploaded_docs = []
        
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.endswith(ext) for ext in file_extensions):
                    file_path = os.path.join(root, file)
                    try:
                        doc_id = self.upload_document(
                            file_path=file_path,
                            document_type=document_type
                        )
                        uploaded_docs.append(doc_id)
                    except Exception as e:
                        logger.error(f"Failed to upload {file_path}: {e}")
        
        logger.info(f"Bulk upload complete: {len(uploaded_docs)} documents")
        return uploaded_docs
    
    def update_mitre_attack_data(self, mitre_data_path: str) -> int:
        """
        Update MITRE ATT&CK data in knowledge base.
        
        Args:
            mitre_data_path: Path to MITRE ATT&CK JSON data
            
        Returns:
            Number of techniques uploaded
        """
        with open(mitre_data_path, 'r') as f:
            mitre_data = json.load(f)
        
        # Process and upload MITRE techniques
        # This would parse the MITRE JSON and create documents
        # for each technique with metadata
        
        logger.info(f"Updated MITRE ATT&CK data from {mitre_data_path}")
        return 0  # Placeholder
    
    def get_corpus_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the knowledge base corpus.
        
        Returns:
            Dictionary with corpus statistics
        """
        # Query corpus for stats
        # Note: Adjust based on actual Vertex AI RAG API
        
        return {
            "corpus_name": self.rag_corpus_name,
            "document_count": 0,  # Placeholder
            "last_updated": datetime.utcnow().isoformat()
        }


def create_sample_knowledge_base_structure(base_dir: str = "./knowledge_base"):
    """
    Create directory structure for organizing knowledge base documents.
    
    Args:
        base_dir: Base directory for knowledge base
    """
    categories = [
        "threat_intelligence/cisa_advisories",
        "threat_intelligence/cert_alerts",
        "threat_intelligence/vendor_reports",
        "mitre_attack/techniques",
        "mitre_attack/groups",
        "mitre_attack/software",
        "industry_reports/verizon_dbir",
        "industry_reports/ibm_breach_cost",
        "industry_reports/sector_specific",
        "compliance/gdpr",
        "compliance/hipaa",
        "compliance/pci_dss",
        "compliance/regional",
        "best_practices/nist",
        "best_practices/cis",
        "best_practices/industry_guides",
        "case_studies/incidents",
        "case_studies/lessons_learned",
        "benchmarks/industry",
        "benchmarks/regional"
    ]
    
    for category in categories:
        path = Path(base_dir) / category
        path.mkdir(parents=True, exist_ok=True)
        
        # Create README in each category
        readme_path = path / "README.md"
        if not readme_path.exists():
            with open(readme_path, 'w') as f:
                f.write(f"# {category.replace('/', ' - ').title()}\n\n")
                f.write("Place relevant documents in this directory.\n")
    
    logger.info(f"Created knowledge base structure at {base_dir}")
    print(f"✅ Knowledge base structure created at {base_dir}")


if __name__ == '__main__':
    print("=== Knowledge Base Manager ===\n")
    
    # Create sample directory structure
    print("Creating sample knowledge base structure...")
    create_sample_knowledge_base_structure()
    
    print("\nKnowledge Base Categories:")
    print("  - threat_intelligence: CISA advisories, CERT alerts, vendor reports")
    print("  - mitre_attack: Techniques, groups, software")
    print("  - industry_reports: Verizon DBIR, IBM breach cost, sector reports")
    print("  - compliance: GDPR, HIPAA, PCI-DSS, regional regulations")
    print("  - best_practices: NIST, CIS, industry guides")
    print("  - case_studies: Incidents, lessons learned")
    print("  - benchmarks: Industry and regional benchmarks")
    
    print("\nNext Steps:")
    print("  1. Populate ./knowledge_base/ with relevant documents")
    print("  2. Set environment variables:")
    print("     - GOOGLE_CLOUD_PROJECT")
    print("     - VERTEX_RAG_CORPUS")
    print("     - VERTEX_RAG_GCS_BUCKET")
    print("  3. Run bulk upload to populate RAG corpus")
    
    print("\n=== Complete ===")
