"""
Main Ingestion Orchestrator for BigQuery RAG Pipeline.

Coordinates:
1. Document processing and chunking
2. Embedding generation
3. BigQuery insertion
4. Status tracking and error handling
"""

import os
import logging
import json
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from google.cloud import bigquery

from .schema import BQSchemaManager, DEFAULT_PROJECT, DEFAULT_DATASET
from .chunker import DocumentChunker, DocumentMetadata, DocumentChunk, chunk_documents
from .embedder import get_embedder, EmbeddingResult

logger = logging.getLogger(__name__)


@dataclass
class IngestStats:
    """Statistics from an ingestion run."""
    documents_processed: int = 0
    documents_failed: int = 0
    chunks_created: int = 0
    embeddings_generated: int = 0
    rows_inserted: int = 0
    errors: List[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    @property
    def duration_seconds(self) -> float:
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    def to_dict(self) -> dict:
        return {
            "documents_processed": self.documents_processed,
            "documents_failed": self.documents_failed,
            "chunks_created": self.chunks_created,
            "embeddings_generated": self.embeddings_generated,
            "rows_inserted": self.rows_inserted,
            "errors": self.errors,
            "duration_seconds": self.duration_seconds,
        }


class RAGIngestPipeline:
    """
    Orchestrates the full RAG ingestion pipeline.
    
    Pipeline stages:
    1. Document loading and metadata extraction
    2. Text chunking with context
    3. Embedding generation
    4. BigQuery insertion
    
    Usage:
        pipeline = RAGIngestPipeline(project_id="my-project")
        stats = pipeline.ingest_file("/path/to/document.pdf", metadata={...})
        stats = pipeline.ingest_directory("/path/to/docs/", pattern="*.pdf")
    """
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        dataset_id: str = DEFAULT_DATASET,
        location: str = "US",
        embedding_location: str = "us-central1",
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        use_mock_embeddings: bool = False,
        batch_size: int = 100
    ):
        """
        Initialize the ingestion pipeline.
        
        Args:
            project_id: GCP project ID
            dataset_id: BigQuery dataset name
            location: BigQuery dataset location
            embedding_location: Vertex AI location for embeddings
            chunk_size: Target chunk size in tokens
            chunk_overlap: Overlap between chunks
            use_mock_embeddings: Use mock embedder for testing
            batch_size: Batch size for BigQuery insertions
        """
        self.project_id = project_id or DEFAULT_PROJECT
        if not self.project_id:
            raise ValueError("project_id required (or set GOOGLE_CLOUD_PROJECT env var)")
        
        self.dataset_id = dataset_id
        self.batch_size = batch_size
        
        # Initialize components
        self.bq_client = bigquery.Client(project=self.project_id)
        self.chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.embedder = get_embedder(
            project_id=self.project_id,
            location=embedding_location,
            use_mock=use_mock_embeddings
        )
        
        # Table references
        self.dataset_ref = f"{self.project_id}.{self.dataset_id}"
        self.documents_table = f"{self.dataset_ref}.documents"
        self.chunks_table = f"{self.dataset_ref}.chunks"
        self.embeddings_table = f"{self.dataset_ref}.embeddings"
        
        logger.info(f"RAGIngestPipeline initialized: project={self.project_id}, dataset={self.dataset_id}")
    
    def ingest_file(
        self,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None,
        skip_existing: bool = True
    ) -> IngestStats:
        """
        Ingest a single file into the RAG catalog.
        
        Args:
            file_path: Path to the file
            metadata: Optional metadata overrides
            skip_existing: Skip if document already exists (by content hash)
            
        Returns:
            IngestStats with processing results
        """
        stats = IngestStats()
        
        try:
            # Step 1: Chunk the document
            logger.info(f"Processing file: {file_path}")
            
            doc_metadata = DocumentMetadata(
                document_id=self.chunker.generate_document_id(file_path),
                source_path=file_path,
                title=Path(file_path).stem
            )
            
            # Apply metadata overrides
            if metadata:
                for key, value in metadata.items():
                    if hasattr(doc_metadata, key):
                        setattr(doc_metadata, key, value)
            
            doc_metadata, chunks = self.chunker.chunk_file(file_path, doc_metadata)
            
            # Check for existing document
            if skip_existing and self._document_exists(doc_metadata.content_hash):
                logger.info(f"Document already exists (hash: {doc_metadata.content_hash[:16]}...), skipping")
                stats.documents_processed = 1
                return stats
            
            stats.chunks_created = len(chunks)
            
            # Step 2: Generate embeddings
            logger.info(f"Generating embeddings for {len(chunks)} chunks")
            
            chunk_texts = [c.chunk_text for c in chunks]
            chunk_ids = [c.chunk_id for c in chunks]
            
            embeddings = self.embedder.embed_texts(chunk_texts, chunk_ids)
            stats.embeddings_generated = len(embeddings)
            
            # Step 3: Insert into BigQuery
            logger.info("Inserting into BigQuery")
            
            # Insert document
            self._insert_document(doc_metadata)
            stats.rows_inserted += 1
            
            # Insert chunks with denormalized metadata
            self._insert_chunks(chunks, doc_metadata)
            stats.rows_inserted += len(chunks)
            
            # Insert embeddings
            self._insert_embeddings(embeddings)
            stats.rows_inserted += len(embeddings)
            
            # Update document status to active
            self._update_document_status(doc_metadata.document_id, "active")
            
            stats.documents_processed = 1
            logger.info(f"✅ Successfully ingested: {file_path}")
            
        except Exception as e:
            stats.documents_failed = 1
            stats.errors.append(f"{file_path}: {str(e)}")
            logger.error(f"Failed to ingest {file_path}: {e}")
        
        stats.end_time = datetime.now()
        return stats
    
    def ingest_directory(
        self,
        directory_path: str,
        pattern: str = "*",
        recursive: bool = True,
        metadata_file: Optional[str] = None,
        skip_existing: bool = True
    ) -> IngestStats:
        """
        Ingest all matching files from a directory.
        
        Args:
            directory_path: Path to the directory
            pattern: Glob pattern for file matching (e.g., "*.pdf")
            recursive: Search subdirectories
            metadata_file: Optional JSON file with per-file metadata
            skip_existing: Skip existing documents
            
        Returns:
            Aggregated IngestStats
        """
        stats = IngestStats()
        
        # Load metadata file if provided
        file_metadata = {}
        if metadata_file and Path(metadata_file).exists():
            with open(metadata_file) as f:
                file_metadata = json.load(f)
        
        # Find matching files
        path = Path(directory_path)
        if recursive:
            files = list(path.rglob(pattern))
        else:
            files = list(path.glob(pattern))
        
        # Filter to actual files
        files = [f for f in files if f.is_file()]
        
        logger.info(f"Found {len(files)} files matching '{pattern}' in {directory_path}")
        
        for file_path in files:
            file_str = str(file_path)
            
            # Get file-specific metadata
            metadata = file_metadata.get(file_path.name, {})
            
            # Auto-detect metadata from path if not provided
            if not metadata.get('industry'):
                metadata['industry'] = self._detect_industry_from_path(file_str)
            if not metadata.get('region'):
                metadata['region'] = self._detect_region_from_path(file_str)
            
            # Ingest the file
            file_stats = self.ingest_file(file_str, metadata=metadata, skip_existing=skip_existing)
            
            # Aggregate stats
            stats.documents_processed += file_stats.documents_processed
            stats.documents_failed += file_stats.documents_failed
            stats.chunks_created += file_stats.chunks_created
            stats.embeddings_generated += file_stats.embeddings_generated
            stats.rows_inserted += file_stats.rows_inserted
            stats.errors.extend(file_stats.errors)
        
        stats.end_time = datetime.now()
        return stats
    
    def ingest_from_manifest(
        self,
        manifest_path: str,
        base_path: Optional[str] = None,
        skip_existing: bool = True
    ) -> IngestStats:
        """
        Ingest documents from a JSON manifest file.
        
        Manifest format (like rag_cyber_risk_corpus_sources.json):
        [
            {
                "title": "Document Title",
                "url": "https://...",  # or "path": "/local/path"
                "source": "NIST",
                "year": 2024,
                "domain": "cyber",
                "type": "government_report",
                "region": "US",
                "summary": "..."
            },
            ...
        ]
        
        Args:
            manifest_path: Path to manifest JSON file
            base_path: Base path for relative file paths
            skip_existing: Skip existing documents
            
        Returns:
            IngestStats
        """
        stats = IngestStats()
        
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        logger.info(f"Processing manifest with {len(manifest)} entries")
        
        for entry in manifest:
            # Determine file path
            file_path = entry.get('path')
            if not file_path and entry.get('url'):
                # URL-based entries need to be downloaded first
                logger.warning(f"Skipping URL-based entry: {entry.get('title')} (download not implemented)")
                continue
            
            if base_path and not Path(file_path).is_absolute():
                file_path = str(Path(base_path) / file_path)
            
            if not Path(file_path).exists():
                logger.warning(f"File not found: {file_path}")
                stats.documents_failed += 1
                stats.errors.append(f"File not found: {file_path}")
                continue
            
            # Map manifest fields to metadata
            metadata = {
                'title': entry.get('title'),
                'publication_year': entry.get('year'),
                'source_type': self._map_source_type(entry.get('source')),
                'doc_type': entry.get('type'),
                'region': entry.get('region', 'global'),
                'primary_domain': entry.get('domain'),
                'curator_notes': entry.get('summary'),
            }
            
            # Ingest
            file_stats = self.ingest_file(file_path, metadata=metadata, skip_existing=skip_existing)
            
            # Aggregate
            stats.documents_processed += file_stats.documents_processed
            stats.documents_failed += file_stats.documents_failed
            stats.chunks_created += file_stats.chunks_created
            stats.embeddings_generated += file_stats.embeddings_generated
            stats.rows_inserted += file_stats.rows_inserted
            stats.errors.extend(file_stats.errors)
        
        stats.end_time = datetime.now()
        return stats
    
    def _document_exists(self, content_hash: str) -> bool:
        """Check if document with given content hash exists."""
        query = f"""
            SELECT 1 FROM `{self.documents_table}`
            WHERE content_hash = @hash
            LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("hash", "STRING", content_hash)
            ]
        )
        
        try:
            result = self.bq_client.query(query, job_config=job_config).result()
            return len(list(result)) > 0
        except Exception:
            return False
    
    def _insert_document(self, metadata: DocumentMetadata) -> None:
        """Insert document metadata into BigQuery."""
        row = metadata.to_dict()
        row['ingested_at'] = datetime.now().isoformat()
        
        errors = self.bq_client.insert_rows_json(self.documents_table, [row])
        if errors:
            raise RuntimeError(f"Failed to insert document: {errors}")
    
    def _insert_chunks(self, chunks: List[DocumentChunk], doc_metadata: DocumentMetadata) -> None:
        """Insert chunks with denormalized metadata."""
        rows = []
        for chunk in chunks:
            row = chunk.to_dict()
            # Denormalize from parent document
            row['industry'] = doc_metadata.industry
            row['primary_domain'] = doc_metadata.primary_domain
            row['doc_type'] = doc_metadata.doc_type
            row['quality_rating'] = doc_metadata.quality_rating
            row['created_at'] = datetime.now().isoformat()
            rows.append(row)
        
        # Insert in batches
        for i in range(0, len(rows), self.batch_size):
            batch = rows[i:i + self.batch_size]
            errors = self.bq_client.insert_rows_json(self.chunks_table, batch)
            if errors:
                logger.error(f"Chunk insertion errors: {errors}")
    
    def _insert_embeddings(self, embeddings: List[EmbeddingResult]) -> None:
        """Insert embeddings into BigQuery."""
        rows = [e.to_dict() for e in embeddings]
        
        # Add timestamp
        for row in rows:
            row['created_at'] = datetime.now().isoformat()
        
        # Insert in batches
        for i in range(0, len(rows), self.batch_size):
            batch = rows[i:i + self.batch_size]
            errors = self.bq_client.insert_rows_json(self.embeddings_table, batch)
            if errors:
                logger.error(f"Embedding insertion errors: {errors}")
    
    def _update_document_status(self, document_id: str, status: str) -> None:
        """Update document status."""
        query = f"""
            UPDATE `{self.documents_table}`
            SET status = @status, last_updated = CURRENT_TIMESTAMP()
            WHERE document_id = @doc_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("status", "STRING", status),
                bigquery.ScalarQueryParameter("doc_id", "STRING", document_id),
            ]
        )
        
        try:
            self.bq_client.query(query, job_config=job_config).result()
        except Exception as e:
            logger.warning(f"Failed to update document status: {e}")
    
    def _detect_industry_from_path(self, file_path: str) -> Optional[str]:
        """Auto-detect industry from file path."""
        path_lower = file_path.lower()
        
        industry_keywords = {
            'healthcare': ['health', 'medical', 'hipaa', 'hospital', 'clinical'],
            'finance': ['finance', 'banking', 'financial', 'pci', 'sox'],
            'government': ['government', 'federal', 'nist', 'cisa', 'dod'],
            'energy': ['energy', 'utility', 'power', 'nerc', 'ics', 'scada'],
            'retail': ['retail', 'ecommerce', 'merchant'],
            'technology': ['tech', 'software', 'saas', 'cloud'],
        }
        
        for industry, keywords in industry_keywords.items():
            if any(kw in path_lower for kw in keywords):
                return industry
        
        return None
    
    def _detect_region_from_path(self, file_path: str) -> str:
        """Auto-detect region from file path."""
        path_lower = file_path.lower()
        
        region_keywords = {
            'Canada': ['canada', 'canadian', 'pipeda', 'phipa'],
            'US': ['us', 'usa', 'american', 'nist', 'cisa', 'hipaa', 'sox'],
            'EU': ['eu', 'european', 'gdpr', 'nis2'],
            'UK': ['uk', 'british', 'ico'],
        }
        
        for region, keywords in region_keywords.items():
            if any(kw in path_lower for kw in keywords):
                return region
        
        return 'global'
    
    def _map_source_type(self, source: Optional[str]) -> str:
        """Map source name to source_type classification."""
        if not source:
            return 'unknown'
        
        source_lower = source.lower()
        
        if any(x in source_lower for x in ['nist', 'cisa', 'government', 'sec', 'dod']):
            return 'regulator'
        if any(x in source_lower for x in ['iso', 'ieee', 'nist']):
            return 'standards_body'
        if any(x in source_lower for x in ['research', 'university', 'academic']):
            return 'academic'
        if any(x in source_lower for x in ['gartner', 'forrester', 'idc']):
            return 'analyst'
        
        return 'external_framework'


# =============================================================================
# Curator Metadata Collection
# =============================================================================

# Taxonomy for guided metadata entry
SCENARIO_TAGS_TAXONOMY = [
    'ransomware', 'BEC', 'data_exfil', 'insider_threat', 'supply_chain',
    'phishing', 'credential_theft', 'privilege_escalation', 'lateral_movement',
    'cryptomining', 'DDoS', 'web_app_attack', 'API_abuse', 'cloud_misconfiguration',
    'third_party_breach', 'social_engineering', 'physical_breach', 'OT_attack'
]

LIFECYCLE_STAGES = [
    'strategy', 'design', 'implementation', 'operations', 
    'incident_response', 'audit', 'training'
]

QUALITY_RATING_GUIDE = {
    1: "Marketing material - vendor-biased, limited depth",
    2: "General guidance - useful but not authoritative",
    3: "Good reference - solid content, reputable source",
    4: "Authoritative source - industry-recognized, well-researched",
    5: "Gold standard - definitive reference, primary source"
}

PRIMARY_DOMAINS = [
    'Identity', 'Network', 'Endpoint', 'Cloud', 'DevSecOps', 
    'OT/ICS', 'Physical', 'Governance/ESRM', 'Data', 'Application'
]


def collect_curator_metadata_interactive(file_path: str) -> Dict[str, Any]:
    """
    Interactive CLI to collect curator metadata for a document.
    
    Captures the curator's 30 years of wisdom:
    - quality_rating with guidance
    - curator_notes explaining why this doc matters
    - scenario_tags from taxonomy
    - lifecycle_stage
    - primary_domain
    
    Args:
        file_path: Path to the document being ingested
        
    Returns:
        Dictionary of metadata fields
    """
    print(f"\n{'='*60}")
    print(f"📄 Curator Metadata Entry")
    print(f"{'='*60}")
    print(f"File: {Path(file_path).name}")
    print()
    
    metadata = {}
    
    # Title
    default_title = Path(file_path).stem.replace('_', ' ').replace('-', ' ')
    title = input(f"Title [{default_title}]: ").strip() or default_title
    metadata['title'] = title
    
    # Industry
    industry = input("Industry (healthcare/finance/government/energy/retail/technology): ").strip()
    if industry:
        metadata['industry'] = industry
    
    # Region
    region = input("Region (Canada/US/EU/UK/global): ").strip() or 'global'
    metadata['region'] = region
    
    # Doc type
    print("\nDoc types: standard, guideline, runbook, incident_report, whitepaper,")
    print("           academic_paper, regulatory, case_study, procedure, checklist")
    doc_type = input("Doc type: ").strip()
    if doc_type:
        metadata['doc_type'] = doc_type
    
    # Publication year
    year = input("Publication year (YYYY): ").strip()
    if year and year.isdigit():
        metadata['publication_year'] = int(year)
    
    # Primary domain
    print(f"\nPrimary domains: {', '.join(PRIMARY_DOMAINS)}")
    domain = input("Primary domain: ").strip()
    if domain:
        metadata['primary_domain'] = domain
    
    # Quality rating with guidance
    print("\n📊 Quality Rating:")
    for rating, desc in QUALITY_RATING_GUIDE.items():
        print(f"   {rating}: {desc}")
    rating_input = input("Quality rating (1-5): ").strip()
    if rating_input and rating_input.isdigit():
        metadata['quality_rating'] = min(5, max(1, int(rating_input)))
    
    # Scenario tags (multi-select)
    print(f"\n🏷️  Scenario tags (comma-separated):")
    print(f"   Available: {', '.join(SCENARIO_TAGS_TAXONOMY[:9])}")
    print(f"             {', '.join(SCENARIO_TAGS_TAXONOMY[9:])}")
    tags_input = input("Tags: ").strip()
    if tags_input:
        tags = [t.strip() for t in tags_input.split(',') if t.strip()]
        metadata['scenario_tags'] = tags
    
    # Lifecycle stages (multi-select)
    print(f"\n📋 Lifecycle stages (comma-separated):")
    print(f"   Available: {', '.join(LIFECYCLE_STAGES)}")
    stages_input = input("Stages: ").strip()
    if stages_input:
        stages = [s.strip() for s in stages_input.split(',') if s.strip()]
        metadata['lifecycle_stage'] = stages
    
    # Curator notes - THE CRITICAL FIELD
    print("\n📝 Curator Notes:")
    print("   Why does this document matter? What makes it valuable?")
    print("   (Your expertise is the moat - capture your insights)")
    notes = input("Notes: ").strip()
    if notes:
        metadata['curator_notes'] = notes
    
    # License
    print("\nLicense: ok_to_train, restricted, attribution_required")
    license_usage = input("License [ok_to_train]: ").strip() or 'ok_to_train'
    metadata['license_usage'] = license_usage
    
    print(f"\n✅ Metadata collected for: {title}")
    return metadata


def collect_curator_metadata_from_file(metadata_file: str, file_path: str) -> Dict[str, Any]:
    """
    Load curator metadata from a JSON sidecar file.
    
    Looks for a .meta.json file alongside the document, e.g.:
    - document.pdf → document.pdf.meta.json
    - document.pdf → document.meta.json
    
    Args:
        metadata_file: Explicit metadata file path (optional)
        file_path: Path to the document
        
    Returns:
        Dictionary of metadata fields
    """
    # Try explicit path first
    if metadata_file and Path(metadata_file).exists():
        with open(metadata_file) as f:
            return json.load(f)
    
    # Try sidecar patterns
    path = Path(file_path)
    sidecar_patterns = [
        path.with_suffix(path.suffix + '.meta.json'),  # doc.pdf.meta.json
        path.with_suffix('.meta.json'),                 # doc.meta.json
        path.parent / f"{path.stem}.meta.json",         # doc.meta.json in same dir
    ]
    
    for sidecar in sidecar_patterns:
        if sidecar.exists():
            logger.info(f"Loading metadata from sidecar: {sidecar}")
            with open(sidecar) as f:
                return json.load(f)
    
    return {}


def run_ingest(
    source: str,
    project_id: Optional[str] = None,
    dataset_id: str = DEFAULT_DATASET,
    pattern: str = "*.pdf",
    use_mock: bool = False,
    skip_existing: bool = True
) -> IngestStats:
    """
    Convenience function to run ingestion.
    
    Args:
        source: File path, directory path, or manifest path
        project_id: GCP project ID
        dataset_id: BigQuery dataset
        pattern: File pattern for directory ingestion
        use_mock: Use mock embeddings
        skip_existing: Skip existing documents
        
    Returns:
        IngestStats
    """
    pipeline = RAGIngestPipeline(
        project_id=project_id,
        dataset_id=dataset_id,
        use_mock_embeddings=use_mock
    )
    
    source_path = Path(source)
    
    if source_path.is_file():
        if source_path.suffix == '.json':
            return pipeline.ingest_from_manifest(source)
        else:
            return pipeline.ingest_file(source, skip_existing=skip_existing)
    elif source_path.is_dir():
        return pipeline.ingest_directory(source, pattern=pattern, skip_existing=skip_existing)
    else:
        raise ValueError(f"Source not found: {source}")


if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description="RAG Ingestion Pipeline")
    parser.add_argument("source", help="File, directory, or manifest to ingest")
    parser.add_argument("--project", help="GCP project ID")
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="BigQuery dataset")
    parser.add_argument("--pattern", default="*.pdf", help="File pattern for directories")
    parser.add_argument("--mock", action="store_true", help="Use mock embeddings")
    parser.add_argument("--force", action="store_true", help="Re-ingest existing documents")
    parser.add_argument("--interactive", "-i", action="store_true", 
                        help="Interactive mode: prompt for curator metadata")
    parser.add_argument("--metadata", help="Path to metadata JSON file")
    
    args = parser.parse_args()
    
    source_path = Path(args.source)
    
    # Handle interactive mode for single files
    if args.interactive and source_path.is_file() and source_path.suffix != '.json':
        print("🎯 Interactive Curator Mode")
        metadata = collect_curator_metadata_interactive(args.source)
        
        pipeline = RAGIngestPipeline(
            project_id=args.project,
            dataset_id=args.dataset,
            use_mock_embeddings=args.mock
        )
        stats = pipeline.ingest_file(args.source, metadata=metadata, skip_existing=not args.force)
    else:
        stats = run_ingest(
            source=args.source,
            project_id=args.project,
            dataset_id=args.dataset,
            pattern=args.pattern,
            use_mock=args.mock,
            skip_existing=not args.force
        )
    
    print("\n" + "=" * 50)
    print("📊 Ingestion Complete")
    print("=" * 50)
    print(f"  Documents processed: {stats.documents_processed}")
    print(f"  Documents failed:    {stats.documents_failed}")
    print(f"  Chunks created:      {stats.chunks_created}")
    print(f"  Embeddings:          {stats.embeddings_generated}")
    print(f"  Rows inserted:       {stats.rows_inserted}")
    print(f"  Duration:            {stats.duration_seconds:.1f}s")
    
    if stats.errors:
        print(f"\n⚠️  Errors ({len(stats.errors)}):")
        for err in stats.errors[:5]:
            print(f"    - {err}")
        if len(stats.errors) > 5:
            print(f"    ... and {len(stats.errors) - 5} more")
