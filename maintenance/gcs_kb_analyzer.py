#!/usr/bin/env python3
"""
GCS Knowledge Base Analyzer and Metadata Generator

Scans GCS bucket, extracts document content, uses Claude to generate summaries
and classifications, then creates metadata files for RAG corpus upload.

Usage:
    python gcs_kb_analyzer.py --bucket gs://dev-rarag-kb --prefix knowledgebase
    
Features:
    - Scans GCS bucket recursively
    - Extracts text from PDF, DOCX, TXT
    - Uses Claude for intelligent analysis
    - Generates metadata matching RAG schema
    - Tracks progress and costs
    - Supports resume on failure
"""

import os
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import time

# Google Cloud Storage
from google.cloud import storage

# Anthropic API
import anthropic

# Document processing
import PyPDF2
from docx import Document as DocxDocument
import io

# Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocumentAnalyzer:
    """Analyzes documents using Claude API."""
    
    # Folder to document type mapping
    FOLDER_TYPE_MAP = {
        'threat_intelligence': 'threat_intelligence',
        'vulnerabilities': 'vulnerability_report',
        'industry_reports': 'industry_report',
        'compliance': 'regulatory',
        'frameworks': 'framework',
        'advisories': 'threat_intelligence',
        'research': 'academic_paper',
        'whitepapers': 'whitepaper',
        'guides': 'guidance',
        'standards': 'framework',
        'case_studies': 'case_study',
        'mitre': 'mitre_attack',
        'nist': 'framework'
    }
    
    # Folder to industry mapping
    FOLDER_INDUSTRY_MAP = {
        'healthcare': ['Healthcare'],
        'financial': ['Financial Services'],
        'manufacturing': ['Manufacturing'],
        'energy': ['Energy', 'Utilities'],
        'government': ['Government'],
        'retail': ['Retail'],
        'technology': ['Technology'],
    }
    
    def __init__(self, anthropic_api_key: str):
        """
        Initialize analyzer.
        
        Args:
            anthropic_api_key: Anthropic API key
        """
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.total_tokens = 0
        self.total_cost = 0.0
        
    def analyze_document(
        self,
        content: str,
        filename: str,
        folder_path: str
    ) -> Dict:
        """
        Analyze document using Claude to extract metadata.
        
        Args:
            content: Document text content
            filename: Original filename
            folder_path: GCS folder path
            
        Returns:
            Dictionary with analysis results
        """
        
        # Truncate content if too long (Claude context limit)
        max_content_chars = 50000  # ~12k tokens
        if len(content) > max_content_chars:
            content_preview = content[:max_content_chars] + "\n\n[Content truncated for analysis]"
        else:
            content_preview = content
        
        # Build analysis prompt
        prompt = self._build_analysis_prompt(content_preview, filename, folder_path)
        
        try:
            logger.info(f"Analyzing document with Claude: {filename}")
            
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                temperature=0,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Track usage
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            self.total_tokens += (input_tokens + output_tokens)
            
            # Estimate cost (Claude Sonnet 4 pricing)
            input_cost = (input_tokens / 1_000_000) * 3.00
            output_cost = (output_tokens / 1_000_000) * 15.00
            cost = input_cost + output_cost
            self.total_cost += cost
            
            logger.info(f"  Tokens: {input_tokens + output_tokens}, Cost: ${cost:.4f}")
            
            # Parse response
            analysis_text = response.content[0].text
            analysis = self._parse_analysis(analysis_text)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing document: {e}")
            return self._get_fallback_analysis(filename, folder_path)
    
    def _build_analysis_prompt(
        self,
        content: str,
        filename: str,
        folder_path: str
    ) -> str:
        """Build prompt for Claude analysis."""
        
        prompt = f"""Analyze this cybersecurity document and extract structured metadata for a RAG knowledge base.

Document: {filename}
Category: {folder_path}

Content:
{content}

Please analyze and provide:

1. **Title**: Clear, descriptive title (if not obvious from filename)
2. **Summary**: 2-3 sentence summary of key content and purpose
3. **Document Type**: One of:
   - threat_intelligence (threat reports, advisories, IOCs)
   - vulnerability_report (CVE, security bulletins)
   - industry_report (sector analysis, benchmarks)
   - regulatory (compliance, legal requirements)
   - framework (standards, methodologies)
   - guidance (best practices, how-to)
   - whitepaper (technical deep-dive)
   - academic_paper (research)
   - case_study (incident analysis, lessons learned)
   - mitre_attack (ATT&CK techniques)

4. **Industries**: List of applicable industries (Healthcare, Financial Services, Manufacturing, etc.) or ["All"] if universal
5. **Regions**: Geographic focus (US, Canada, EU, Global, etc.)
6. **Tags**: 5-10 relevant keywords (lowercase, underscore-separated)
7. **Threat Actors** (if applicable): Named threat groups mentioned
8. **Techniques** (if applicable): MITRE ATT&CK technique IDs mentioned (e.g., T1566, T1059)
9. **Vulnerabilities** (if applicable): CVE IDs mentioned (e.g., CVE-2024-1234)
10. **Key Topics**: Main subjects covered

Format your response as valid JSON:
```json
{{
  "title": "Clear document title",
  "summary": "2-3 sentence summary",
  "document_type": "threat_intelligence",
  "industries": ["Healthcare", "Financial Services"],
  "regions": ["US", "Canada"],
  "tags": ["ransomware", "healthcare", "incident_response"],
  "threat_actors": ["APT29", "Lazarus Group"],
  "techniques": ["T1566.001", "T1059.001"],
  "cves": ["CVE-2024-1234"],
  "key_topics": ["ransomware", "data exfiltration", "detection"]
}}
```

IMPORTANT: 
- Return ONLY valid JSON, no other text
- Be specific and accurate
- Use exact MITRE technique IDs if mentioned
- Use exact CVE IDs if mentioned
- Tags should be technical and searchable
"""
        
        return prompt
    
    def _parse_analysis(self, analysis_text: str) -> Dict:
        """Parse Claude's JSON response."""
        
        try:
            # Extract JSON from response (in case Claude adds markdown)
            if "```json" in analysis_text:
                json_start = analysis_text.find("```json") + 7
                json_end = analysis_text.find("```", json_start)
                json_text = analysis_text[json_start:json_end].strip()
            elif "```" in analysis_text:
                json_start = analysis_text.find("```") + 3
                json_end = analysis_text.find("```", json_start)
                json_text = analysis_text[json_start:json_end].strip()
            else:
                json_text = analysis_text.strip()
            
            analysis = json.loads(json_text)
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            logger.error(f"Response was: {analysis_text[:500]}")
            return {}
    
    def _get_fallback_analysis(self, filename: str, folder_path: str) -> Dict:
        """
        Generate basic metadata when Claude analysis fails.
        
        Args:
            filename: Document filename
            folder_path: GCS folder path
            
        Returns:
            Basic metadata dictionary
        """
        
        # Infer type from folder
        doc_type = "guidance"
        for folder, dtype in self.FOLDER_TYPE_MAP.items():
            if folder.lower() in folder_path.lower():
                doc_type = dtype
                break
        
        # Infer industry from folder
        industries = ["All"]
        for folder, ind_list in self.FOLDER_INDUSTRY_MAP.items():
            if folder.lower() in folder_path.lower():
                industries = ind_list
                break
        
        return {
            "title": filename,
            "summary": f"Document from {folder_path}",
            "document_type": doc_type,
            "industries": industries,
            "regions": ["Global"],
            "tags": [folder_path.split('/')[0].lower() if '/' in folder_path else "general"],
            "threat_actors": [],
            "techniques": [],
            "cves": [],
            "key_topics": []
        }
    
    def get_cost_summary(self) -> Dict:
        """Get usage and cost summary."""
        return {
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "estimated_cost_per_doc": self.total_cost / max(1, len(self.analyzed_docs)) if hasattr(self, 'analyzed_docs') else 0
        }


class GCSKnowledgeBaseProcessor:
    """Process GCS bucket and generate metadata."""
    
    SUPPORTED_EXTENSIONS = {'.pdf', '.txt', '.docx', '.md'}
    
    def __init__(
        self,
        bucket_name: str,
        prefix: str,
        anthropic_api_key: str,
        output_dir: str = "./processed_metadata"
    ):
        """
        Initialize processor.
        
        Args:
            bucket_name: GCS bucket name (without gs://)
            prefix: Prefix/folder in bucket
            anthropic_api_key: Anthropic API key
            output_dir: Local directory for metadata files
        """
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize clients
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(bucket_name)
        self.analyzer = DocumentAnalyzer(anthropic_api_key)
        
        # Progress tracking
        self.progress_file = self.output_dir / "progress.json"
        self.processed_files = self._load_progress()
        
        logger.info(f"Initialized processor for gs://{bucket_name}/{prefix}")
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"Previously processed: {len(self.processed_files)} files")
    
    def _load_progress(self) -> set:
        """Load progress from previous run."""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                data = json.load(f)
                return set(data.get('processed_files', []))
        return set()
    
    def _save_progress(self):
        """Save progress to disk."""
        with open(self.progress_file, 'w') as f:
            json.dump({
                'processed_files': list(self.processed_files),
                'last_updated': datetime.now().isoformat(),
                'total_cost': self.analyzer.total_cost,
                'total_tokens': self.analyzer.total_tokens
            }, f, indent=2)
    
    def list_documents(self) -> List[storage.Blob]:
        """
        List all processable documents in bucket.
        
        Returns:
            List of blob objects
        """
        logger.info(f"Scanning gs://{self.bucket_name}/{self.prefix}...")
        
        blobs = self.bucket.list_blobs(prefix=self.prefix)
        
        documents = []
        for blob in blobs:
            ext = Path(blob.name).suffix.lower()
            if ext in self.SUPPORTED_EXTENSIONS:
                documents.append(blob)
        
        logger.info(f"Found {len(documents)} processable documents")
        return documents
    
    def extract_text(self, blob: storage.Blob) -> Optional[str]:
        """
        Extract text content from document.
        
        Args:
            blob: GCS blob object
            
        Returns:
            Extracted text or None if failed
        """
        ext = Path(blob.name).suffix.lower()
        
        try:
            content_bytes = blob.download_as_bytes()
            
            if ext == '.txt' or ext == '.md':
                return content_bytes.decode('utf-8', errors='ignore')
            
            elif ext == '.pdf':
                return self._extract_pdf_text(content_bytes)
            
            elif ext == '.docx':
                return self._extract_docx_text(content_bytes)
            
            else:
                logger.warning(f"Unsupported file type: {ext}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting text from {blob.name}: {e}")
            return None
    
    def _extract_pdf_text(self, content_bytes: bytes) -> str:
        """Extract text from PDF."""
        pdf_file = io.BytesIO(content_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text_parts = []
        for page in pdf_reader.pages:
            text_parts.append(page.extract_text())
        
        return '\n'.join(text_parts)
    
    def _extract_docx_text(self, content_bytes: bytes) -> str:
        """Extract text from DOCX."""
        docx_file = io.BytesIO(content_bytes)
        doc = DocxDocument(docx_file)
        
        text_parts = []
        for paragraph in doc.paragraphs:
            text_parts.append(paragraph.text)
        
        return '\n'.join(text_parts)
    
    def create_metadata(
        self,
        blob: storage.Blob,
        analysis: Dict
    ) -> Dict:
        """
        Create complete metadata file.
        
        Args:
            blob: GCS blob object
            analysis: Analysis results from Claude
            
        Returns:
            Complete metadata dictionary
        """
        
        # Extract folder path for categorization
        relative_path = blob.name.replace(self.prefix, '').lstrip('/')
        folder_parts = relative_path.split('/')[:-1]
        folder_path = '/'.join(folder_parts) if folder_parts else 'root'
        
        # Build metadata
        metadata = {
            "title": analysis.get('title', Path(blob.name).stem),
            "summary": analysis.get('summary', ''),
            "document_type": analysis.get('document_type', 'guidance'),
            "source": "Internal Knowledge Base",
            "date": blob.time_created.strftime('%Y-%m-%d'),
            "industries": analysis.get('industries', ['All']),
            "regions": analysis.get('regions', ['Global']),
            "tags": analysis.get('tags', []),
            "language": "en",
            
            # GCS metadata
            "gcs_bucket": self.bucket_name,
            "gcs_path": blob.name,
            "gcs_url": f"gs://{self.bucket_name}/{blob.name}",
            "category_path": folder_path,
            "file_size_bytes": blob.size,
            "content_type": blob.content_type,
            
            # Analysis metadata
            "threat_actors": analysis.get('threat_actors', []),
            "mitre_techniques": analysis.get('techniques', []),
            "cves": analysis.get('cves', []),
            "key_topics": analysis.get('key_topics', []),
            
            # Processing metadata
            "processed_date": datetime.now().isoformat(),
            "analyzer_version": "1.0"
        }
        
        return metadata
    
    def process_document(self, blob: storage.Blob) -> bool:
        """
        Process single document.
        
        Args:
            blob: GCS blob object
            
        Returns:
            True if successful
        """
        
        # Skip if already processed
        if blob.name in self.processed_files:
            logger.info(f"Skipping already processed: {blob.name}")
            return True
        
        logger.info(f"Processing: {blob.name}")
        
        try:
            # Extract text
            content = self.extract_text(blob)
            if not content:
                logger.warning(f"Could not extract text from {blob.name}")
                return False
            
            logger.info(f"  Extracted {len(content)} characters")
            
            # Analyze with Claude
            folder_path = '/'.join(blob.name.split('/')[:-1])
            analysis = self.analyzer.analyze_document(
                content=content,
                filename=Path(blob.name).name,
                folder_path=folder_path
            )
            
            # Create metadata
            metadata = self.create_metadata(blob, analysis)
            
            # Save metadata locally
            safe_name = Path(blob.name).name.replace(' ', '_')
            metadata_filename = f"{safe_name}.metadata.json"
            metadata_path = self.output_dir / metadata_filename
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"  ✓ Metadata saved: {metadata_filename}")
            
            # Mark as processed
            self.processed_files.add(blob.name)
            self._save_progress()
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing {blob.name}: {e}", exc_info=True)
            return False
    
    def process_all(
        self,
        max_documents: Optional[int] = None,
        delay_seconds: float = 1.0
    ):
        """
        Process all documents in bucket.
        
        Args:
            max_documents: Maximum number to process (for testing)
            delay_seconds: Delay between documents (rate limiting)
        """
        
        documents = self.list_documents()
        
        # Filter out already processed
        to_process = [d for d in documents if d.name not in self.processed_files]
        
        if max_documents:
            to_process = to_process[:max_documents]
        
        logger.info(f"Processing {len(to_process)} documents...")
        
        successful = 0
        failed = 0
        
        for i, blob in enumerate(to_process, 1):
            logger.info(f"\n[{i}/{len(to_process)}] Processing {blob.name}")
            
            if self.process_document(blob):
                successful += 1
            else:
                failed += 1
            
            # Rate limiting
            if i < len(to_process):
                time.sleep(delay_seconds)
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("Processing Complete!")
        logger.info("="*60)
        logger.info(f"Total processed: {successful}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Total documents: {len(self.processed_files)}")
        logger.info(f"\nCost Summary:")
        logger.info(f"  Total tokens: {self.analyzer.total_tokens:,}")
        logger.info(f"  Total cost: ${self.analyzer.total_cost:.2f}")
        logger.info(f"  Avg cost per doc: ${self.analyzer.total_cost/max(1, successful):.4f}")
        logger.info(f"\nMetadata files: {self.output_dir}")
        logger.info("="*60)


def main():
    """Main entry point."""
    
    parser = argparse.ArgumentParser(
        description="Analyze GCS knowledge base and generate metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process full bucket
  python gcs_kb_analyzer.py \\
    --bucket dev-rarag-kb \\
    --prefix knowledgebase \\
    --api-key sk-ant-...

  # Test with 5 documents
  python gcs_kb_analyzer.py \\
    --bucket dev-rarag-kb \\
    --prefix knowledgebase \\
    --api-key sk-ant-... \\
    --max-docs 5

  # Resume previous run
  python gcs_kb_analyzer.py \\
    --bucket dev-rarag-kb \\
    --prefix knowledgebase \\
    --api-key sk-ant-... \\
    --resume
        """
    )
    
    parser.add_argument(
        '--bucket',
        required=True,
        help='GCS bucket name (without gs://)'
    )
    
    parser.add_argument(
        '--prefix',
        required=True,
        help='Prefix/folder in bucket (e.g., knowledgebase)'
    )
    
    parser.add_argument(
        '--api-key',
        help='Anthropic API key (or set ANTHROPIC_API_KEY env var)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='./processed_metadata',
        help='Output directory for metadata files'
    )
    
    parser.add_argument(
        '--max-docs',
        type=int,
        help='Maximum documents to process (for testing)'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Delay between documents in seconds (rate limiting)'
    )
    
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from previous run'
    )
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        logger.error("Anthropic API key required (--api-key or ANTHROPIC_API_KEY env var)")
        return 1
    
    # Initialize processor
    processor = GCSKnowledgeBaseProcessor(
        bucket_name=args.bucket,
        prefix=args.prefix,
        anthropic_api_key=api_key,
        output_dir=args.output_dir
    )
    
    # Process documents
    processor.process_all(
        max_documents=args.max_docs,
        delay_seconds=args.delay
    )
    
    return 0


if __name__ == '__main__':
    exit(main())
