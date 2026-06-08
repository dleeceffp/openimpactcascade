"""
BigQuery Schema Definitions for RAG Catalog.

Tables:
- documents: Document metadata with rich classification
- chunks: Text chunks with context and denormalized metadata
- embeddings: Vector embeddings for similarity search
- retrieval_logs: Query logging for quality feedback loops
"""

import os
import logging
from typing import Optional
from google.cloud import bigquery

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT')
DEFAULT_DATASET = 'oic_rag_catalog'
DEFAULT_LOCATION = 'US'


# SQL Schema Definitions
DOCUMENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.documents` (
  -- Identity
  document_id      STRING NOT NULL,
  source_path      STRING,
  title            STRING,
  content_hash     STRING,
  version          INT64,
  
  -- Core classification
  industry         STRING,              -- from folder, editable
  region           STRING,              -- Canada, EU, US, global, multi
  doc_type         STRING,              -- standard, guideline, runbook, incident_report, etc.
  publication_year INT64,
  date_effective   DATE,
  source_type      STRING,              -- internal_policy, external_framework, vendor_marketing, regulator, standards_body
  
  -- Risk/security facets
  primary_domain   STRING,              -- Identity, Network, Endpoint, Cloud, DevSecOps, OT/ICS, Physical, Governance/ESRM
  scenario_tags    ARRAY<STRING>,       -- [ransomware, BEC, data_exfil, insider_threat, ...]
  lifecycle_stage  ARRAY<STRING>,       -- [strategy, design, implementation, operations, incident_response, audit]
  
  -- Quality & trust
  sensitivity      STRING,              -- public, internal, confidential
  quality_rating   INT64,               -- 1-5: marketing-ish → gold standard
  license_usage    STRING,              -- ok_to_train, restricted, attribution_required, etc.
  curator_notes    STRING,              -- curator wisdom on why this doc matters
  
  -- System fields
  ingested_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  last_updated     TIMESTAMP,
  status           STRING,              -- pending, active, archived, error, deprecated
  
  -- Flexible overflow
  metadata         JSON                 -- for experimentation without schema changes
)
"""

CHUNKS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.chunks` (
  chunk_id         STRING NOT NULL,
  document_id      STRING NOT NULL,
  
  -- Chunk content
  chunk_index      INT64,
  chunk_text       STRING,
  token_count      INT64,
  
  -- Context fields (auto-derived during chunking)
  page_number      INT64,
  section_number   STRING,              -- e.g. "3.2.1"
  section_title    STRING,              -- heading text if detected
  chunk_type       STRING,              -- paragraph, table, list, code_block, etc.
  
  -- Inherited from parent doc (denormalized for query performance)
  industry         STRING,
  primary_domain   STRING,
  doc_type         STRING,
  quality_rating   INT64,
  
  -- System fields
  embedding_id     STRING,
  created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
"""

EMBEDDINGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.embeddings` (
  embedding_id     STRING NOT NULL,
  chunk_id         STRING NOT NULL,
  
  -- Embedding data
  embedding        ARRAY<FLOAT64>,      -- Vector embedding (768-dim for text-embedding-004)
  model_id         STRING,              -- e.g. "text-embedding-004"
  model_version    STRING,
  
  -- System fields
  created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
"""

RETRIEVAL_LOGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.retrieval_logs` (
  query_id         STRING NOT NULL,
  
  -- Query info
  query_text       STRING,
  query_embedding  ARRAY<FLOAT64>,
  
  -- Context
  user_id          STRING,
  session_id       STRING,
  industry_filter  STRING,
  region_filter    STRING,
  domain_filter    STRING,
  
  -- Query metadata
  result_count     INT64,               -- How many chunks returned
  max_similarity   FLOAT64,             -- Best match score
  min_similarity   FLOAT64,             -- Worst match score
  
  -- Aggregate feedback (updated after user interaction)
  overall_rating   INT64,               -- 1-5 if user rates overall result quality
  was_helpful      BOOL,
  
  -- System fields
  created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
"""

RETRIEVAL_LOG_RESULTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.retrieval_log_results` (
  query_id         STRING NOT NULL,
  rank             INT64 NOT NULL,      -- Position in result set (1 = top result)
  chunk_id         STRING NOT NULL,
  
  -- Scoring
  similarity_score FLOAT64,
  
  -- User interaction tracking
  was_displayed    BOOL DEFAULT TRUE,   -- Was this chunk shown to user?
  was_clicked      BOOL,                -- Did user click/expand this chunk?
  was_copied       BOOL,                -- Did user copy content from this chunk?
  dwell_time_ms    INT64,               -- How long user viewed this chunk
  
  -- Explicit feedback
  was_useful       BOOL,                -- User marked as useful/not useful
  feedback_notes   STRING,              -- Optional user comment
  
  -- Chunk context at query time (for analysis without joins)
  chunk_doc_type   STRING,
  chunk_quality    INT64,
  chunk_industry   STRING,
  
  -- System fields
  created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
"""


class BQSchemaManager:
    """
    Manages BigQuery schema for RAG catalog.
    
    Usage:
        manager = BQSchemaManager(project_id="my-project")
        manager.create_dataset()
        manager.create_all_tables()
    """
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        dataset_id: str = DEFAULT_DATASET,
        location: str = DEFAULT_LOCATION
    ):
        """
        Initialize schema manager.
        
        Args:
            project_id: GCP project ID (defaults to GOOGLE_CLOUD_PROJECT env var)
            dataset_id: BigQuery dataset name
            location: BigQuery dataset location
        """
        self.project_id = project_id or DEFAULT_PROJECT
        if not self.project_id:
            raise ValueError("project_id required (or set GOOGLE_CLOUD_PROJECT env var)")
        
        self.dataset_id = dataset_id
        self.location = location
        self.client = bigquery.Client(project=self.project_id)
        
        logger.info(f"BQSchemaManager initialized: project={self.project_id}, dataset={self.dataset_id}")
    
    @property
    def dataset_ref(self) -> str:
        """Full dataset reference."""
        return f"{self.project_id}.{self.dataset_id}"
    
    def create_dataset(self, exists_ok: bool = True) -> bigquery.Dataset:
        """
        Create the RAG catalog dataset.
        
        Args:
            exists_ok: If True, don't error if dataset exists
            
        Returns:
            Created or existing Dataset object
        """
        dataset = bigquery.Dataset(self.dataset_ref)
        dataset.location = self.location
        dataset.description = "OpenImpactCascade RAG Knowledge Base Catalog"
        
        try:
            dataset = self.client.create_dataset(dataset, exists_ok=exists_ok)
            logger.info(f"✅ Dataset created/verified: {self.dataset_ref}")
            return dataset
        except Exception as e:
            logger.error(f"Failed to create dataset: {e}")
            raise
    
    def create_table(self, table_sql: str, table_name: str) -> None:
        """
        Create a table using DDL SQL.
        
        Args:
            table_sql: CREATE TABLE SQL statement
            table_name: Table name for logging
        """
        sql = table_sql.format(project=self.project_id, dataset=self.dataset_id)
        
        try:
            job = self.client.query(sql)
            job.result()  # Wait for completion
            logger.info(f"✅ Table created/verified: {table_name}")
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {e}")
            raise
    
    def create_all_tables(self) -> None:
        """Create all RAG catalog tables."""
        tables = [
            (DOCUMENTS_TABLE_SQL, "documents"),
            (CHUNKS_TABLE_SQL, "chunks"),
            (EMBEDDINGS_TABLE_SQL, "embeddings"),
            (RETRIEVAL_LOGS_TABLE_SQL, "retrieval_logs"),
            (RETRIEVAL_LOG_RESULTS_TABLE_SQL, "retrieval_log_results"),
        ]
        
        for sql, name in tables:
            self.create_table(sql, name)
        
        logger.info(f"✅ All tables created in {self.dataset_ref}")
    
    def drop_all_tables(self, confirm: bool = False) -> None:
        """
        Drop all RAG catalog tables. USE WITH CAUTION.
        
        Args:
            confirm: Must be True to actually drop tables
        """
        if not confirm:
            logger.warning("drop_all_tables called without confirm=True, skipping")
            return
        
        tables = ["retrieval_logs", "embeddings", "chunks", "documents"]
        
        for table_name in tables:
            table_ref = f"{self.dataset_ref}.{table_name}"
            try:
                self.client.delete_table(table_ref, not_found_ok=True)
                logger.info(f"🗑️  Dropped table: {table_name}")
            except Exception as e:
                logger.error(f"Failed to drop table {table_name}: {e}")
    
    def get_table_stats(self) -> dict:
        """
        Get row counts for all tables.
        
        Returns:
            Dict mapping table name to row count
        """
        tables = ["documents", "chunks", "embeddings", "retrieval_logs"]
        stats = {}
        
        for table_name in tables:
            sql = f"SELECT COUNT(*) as cnt FROM `{self.dataset_ref}.{table_name}`"
            try:
                result = self.client.query(sql).result()
                for row in result:
                    stats[table_name] = row.cnt
            except Exception:
                stats[table_name] = -1  # Table doesn't exist or error
        
        return stats


def setup_schema(
    project_id: Optional[str] = None,
    dataset_id: str = DEFAULT_DATASET,
    location: str = DEFAULT_LOCATION
) -> BQSchemaManager:
    """
    Convenience function to set up the full RAG catalog schema.
    
    Args:
        project_id: GCP project ID
        dataset_id: BigQuery dataset name
        location: BigQuery dataset location
        
    Returns:
        Configured BQSchemaManager instance
    """
    manager = BQSchemaManager(
        project_id=project_id,
        dataset_id=dataset_id,
        location=location
    )
    manager.create_dataset()
    manager.create_all_tables()
    
    return manager


if __name__ == "__main__":
    # CLI for schema setup
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description="Setup BigQuery RAG catalog schema")
    parser.add_argument("--project", help="GCP project ID")
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Dataset name")
    parser.add_argument("--location", default=DEFAULT_LOCATION, help="Dataset location")
    parser.add_argument("--drop", action="store_true", help="Drop existing tables first")
    parser.add_argument("--stats", action="store_true", help="Show table stats only")
    
    args = parser.parse_args()
    
    manager = BQSchemaManager(
        project_id=args.project,
        dataset_id=args.dataset,
        location=args.location
    )
    
    if args.stats:
        stats = manager.get_table_stats()
        print("\n📊 Table Statistics:")
        for table, count in stats.items():
            print(f"  {table}: {count:,} rows")
    else:
        if args.drop:
            print("⚠️  Dropping existing tables...")
            manager.drop_all_tables(confirm=True)
        
        manager.create_dataset()
        manager.create_all_tables()
        
        print("\n✅ Schema setup complete!")
        stats = manager.get_table_stats()
        print("\n📊 Table Statistics:")
        for table, count in stats.items():
            print(f"  {table}: {count:,} rows")
