"""
Document Chunking with Context Extraction.

Handles:
- PDF text extraction with page tracking
- Markdown/text parsing with section detection
- Semantic chunking with overlap
- Chunk type classification (paragraph, table, list, code_block)
"""

import os
import re
import hashlib
import logging
from typing import List, Dict, Optional, Tuple, Generator
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Chunking configuration
DEFAULT_CHUNK_SIZE = 1000  # tokens (approximate)
DEFAULT_CHUNK_OVERLAP = 100  # tokens
CHARS_PER_TOKEN = 4  # rough estimate for English text

# Doc-type specific chunking strategies
# Different document types benefit from different chunk sizes to preserve context
DOC_TYPE_CHUNK_STRATEGIES = {
    # Incident reports: Smaller chunks to preserve scenario integrity
    'incident_report': {'chunk_size': 500, 'overlap': 75},
    'case_study': {'chunk_size': 500, 'overlap': 75},
    
    # Standards/frameworks: Medium chunks for context
    'standard': {'chunk_size': 1000, 'overlap': 100},
    'framework': {'chunk_size': 1000, 'overlap': 100},
    'guideline': {'chunk_size': 1000, 'overlap': 100},
    'regulatory': {'chunk_size': 1000, 'overlap': 100},
    
    # Academic/whitepapers: Larger chunks for arguments and reasoning
    'academic_paper': {'chunk_size': 1500, 'overlap': 150},
    'whitepaper': {'chunk_size': 1200, 'overlap': 120},
    'research': {'chunk_size': 1500, 'overlap': 150},
    
    # Runbooks/procedures: Smaller chunks, preserve step integrity
    'runbook': {'chunk_size': 400, 'overlap': 50},
    'procedure': {'chunk_size': 400, 'overlap': 50},
    'checklist': {'chunk_size': 300, 'overlap': 30},
    
    # Default fallback
    'default': {'chunk_size': 1000, 'overlap': 100},
}


@dataclass
class ChunkContext:
    """Context information for a chunk."""
    page_number: Optional[int] = None
    section_number: Optional[str] = None
    section_title: Optional[str] = None
    chunk_type: str = "paragraph"  # paragraph, table, list, code_block, heading


@dataclass
class DocumentChunk:
    """A chunk of document text with context."""
    chunk_id: str
    document_id: str
    chunk_index: int
    chunk_text: str
    token_count: int
    context: ChunkContext = field(default_factory=ChunkContext)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for BigQuery insertion."""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "chunk_text": self.chunk_text,
            "token_count": self.token_count,
            "page_number": self.context.page_number,
            "section_number": self.context.section_number,
            "section_title": self.context.section_title,
            "chunk_type": self.context.chunk_type,
        }


@dataclass
class DocumentMetadata:
    """Metadata extracted or provided for a document."""
    document_id: str
    source_path: str
    title: Optional[str] = None
    content_hash: Optional[str] = None
    
    # Classification (can be auto-detected or provided)
    industry: Optional[str] = None
    region: Optional[str] = None
    doc_type: Optional[str] = None
    publication_year: Optional[int] = None
    source_type: Optional[str] = None
    primary_domain: Optional[str] = None
    scenario_tags: List[str] = field(default_factory=list)
    lifecycle_stage: List[str] = field(default_factory=list)
    
    # Quality
    sensitivity: str = "public"
    quality_rating: Optional[int] = None
    license_usage: str = "ok_to_train"
    curator_notes: Optional[str] = None
    
    # Extra
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for BigQuery insertion."""
        return {
            "document_id": self.document_id,
            "source_path": self.source_path,
            "title": self.title,
            "content_hash": self.content_hash,
            "version": 1,
            "industry": self.industry,
            "region": self.region,
            "doc_type": self.doc_type,
            "publication_year": self.publication_year,
            "source_type": self.source_type,
            "primary_domain": self.primary_domain,
            "scenario_tags": self.scenario_tags,
            "lifecycle_stage": self.lifecycle_stage,
            "sensitivity": self.sensitivity,
            "quality_rating": self.quality_rating,
            "license_usage": self.license_usage,
            "curator_notes": self.curator_notes,
            "status": "pending",
            "metadata": self.metadata,
        }


class DocumentChunker:
    """
    Chunks documents into smaller pieces with context extraction.
    
    Supports:
    - Plain text (.txt)
    - Markdown (.md)
    - PDF (requires PyMuPDF/fitz)
    
    Features:
    - Doc-type aware chunking (incident reports get smaller chunks, academic papers get larger)
    - Section and heading detection
    - Chunk type classification (paragraph, table, list, code_block)
    
    Usage:
        chunker = DocumentChunker()
        chunks = chunker.chunk_file("/path/to/document.pdf", doc_metadata)
    """
    
    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        use_doc_type_strategy: bool = True
    ):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Default target chunk size in tokens (overridden by doc_type strategy)
            chunk_overlap: Default overlap between chunks in tokens
            use_doc_type_strategy: If True, adjust chunk size based on document type
        """
        self.default_chunk_size = chunk_size
        self.default_chunk_overlap = chunk_overlap
        self.use_doc_type_strategy = use_doc_type_strategy
        
        # Will be set per-document based on doc_type
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.char_limit = chunk_size * CHARS_PER_TOKEN
        self.overlap_chars = chunk_overlap * CHARS_PER_TOKEN
        
        # Section detection patterns
        self.heading_patterns = [
            # Markdown headings
            (r'^(#{1,6})\s+(.+)$', 'markdown'),
            # Numbered sections (1., 1.1, 1.1.1, etc.)
            (r'^(\d+(?:\.\d+)*)\s+(.+)$', 'numbered'),
            # ALL CAPS headings
            (r'^([A-Z][A-Z\s]{5,})$', 'caps'),
        ]
        
        # Chunk type patterns
        self.table_pattern = re.compile(r'^\|.*\|$', re.MULTILINE)
        self.list_pattern = re.compile(r'^[\s]*[-*•]\s+', re.MULTILINE)
        self.code_pattern = re.compile(r'^```|^    \S', re.MULTILINE)
    
    def generate_chunk_id(self, document_id: str, chunk_index: int, chunk_text: str) -> str:
        """Generate unique chunk ID."""
        content_hash = hashlib.md5(chunk_text.encode()).hexdigest()[:8]
        return f"{document_id}_chunk_{chunk_index:04d}_{content_hash}"
    
    def generate_document_id(self, source_path: str) -> str:
        """Generate unique document ID from source path."""
        path_hash = hashlib.md5(source_path.encode()).hexdigest()[:12]
        filename = Path(source_path).stem[:20]
        # Clean filename for ID
        filename = re.sub(r'[^a-zA-Z0-9_-]', '_', filename)
        return f"doc_{filename}_{path_hash}"
    
    def compute_content_hash(self, content: str) -> str:
        """Compute SHA256 hash of content for deduplication."""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count from text."""
        return len(text) // CHARS_PER_TOKEN
    
    def _apply_doc_type_strategy(self, doc_type: Optional[str]) -> None:
        """
        Apply doc-type specific chunking strategy.
        
        Different document types benefit from different chunk sizes:
        - incident_report: Smaller (500) to preserve scenario integrity
        - academic_paper: Larger (1500) for arguments and reasoning
        - runbook: Smaller (400) to preserve step integrity
        - standard: Medium (1000) for balanced context
        
        Args:
            doc_type: Document type from metadata
        """
        if not self.use_doc_type_strategy or not doc_type:
            # Use defaults
            self.chunk_size = self.default_chunk_size
            self.chunk_overlap = self.default_chunk_overlap
        else:
            # Look up strategy
            strategy = DOC_TYPE_CHUNK_STRATEGIES.get(
                doc_type.lower(),
                DOC_TYPE_CHUNK_STRATEGIES['default']
            )
            self.chunk_size = strategy['chunk_size']
            self.chunk_overlap = strategy['overlap']
            logger.info(f"Applied {doc_type} chunking strategy: size={self.chunk_size}, overlap={self.chunk_overlap}")
        
        # Update derived values
        self.char_limit = self.chunk_size * CHARS_PER_TOKEN
        self.overlap_chars = self.chunk_overlap * CHARS_PER_TOKEN
    
    def detect_chunk_type(self, text: str) -> str:
        """Detect the type of content in a chunk."""
        if self.table_pattern.search(text):
            return "table"
        if self.code_pattern.search(text):
            return "code_block"
        if len(self.list_pattern.findall(text)) > 2:
            return "list"
        return "paragraph"
    
    def extract_section_info(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract section number and title from text.
        
        Returns:
            Tuple of (section_number, section_title)
        """
        lines = text.strip().split('\n')
        if not lines:
            return None, None
        
        first_line = lines[0].strip()
        
        for pattern, pattern_type in self.heading_patterns:
            match = re.match(pattern, first_line)
            if match:
                if pattern_type == 'markdown':
                    level = len(match.group(1))
                    title = match.group(2)
                    return str(level), title
                elif pattern_type == 'numbered':
                    section_num = match.group(1)
                    title = match.group(2)
                    return section_num, title
                elif pattern_type == 'caps':
                    return None, match.group(1).strip()
        
        return None, None
    
    def chunk_text(
        self,
        text: str,
        document_id: str,
        page_numbers: Optional[Dict[int, int]] = None
    ) -> List[DocumentChunk]:
        """
        Chunk text into smaller pieces with overlap.
        
        Args:
            text: Full document text
            document_id: Parent document ID
            page_numbers: Optional mapping of char position to page number
            
        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        
        # Split into paragraphs first
        paragraphs = re.split(r'\n\s*\n', text)
        
        current_chunk = ""
        current_section_num = None
        current_section_title = None
        chunk_index = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Check for section heading
            section_num, section_title = self.extract_section_info(para)
            if section_num or section_title:
                current_section_num = section_num or current_section_num
                current_section_title = section_title or current_section_title
            
            # Check if adding this paragraph exceeds chunk size
            if len(current_chunk) + len(para) > self.char_limit:
                # Save current chunk if not empty
                if current_chunk.strip():
                    chunk = self._create_chunk(
                        current_chunk,
                        document_id,
                        chunk_index,
                        current_section_num,
                        current_section_title,
                        page_numbers
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                
                # Start new chunk with overlap
                if self.overlap_chars > 0 and current_chunk:
                    overlap_text = current_chunk[-self.overlap_chars:]
                    current_chunk = overlap_text + "\n\n" + para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
        
        # Don't forget the last chunk
        if current_chunk.strip():
            chunk = self._create_chunk(
                current_chunk,
                document_id,
                chunk_index,
                current_section_num,
                current_section_title,
                page_numbers
            )
            chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} chunks from document {document_id}")
        return chunks
    
    def _create_chunk(
        self,
        text: str,
        document_id: str,
        chunk_index: int,
        section_num: Optional[str],
        section_title: Optional[str],
        page_numbers: Optional[Dict[int, int]]
    ) -> DocumentChunk:
        """Create a DocumentChunk with context."""
        chunk_id = self.generate_chunk_id(document_id, chunk_index, text)
        
        # Determine page number if available
        page_num = None
        if page_numbers:
            # Find the page for the start of this chunk
            # This is approximate - would need char position tracking for accuracy
            page_num = 1  # Default to page 1 if we can't determine
        
        context = ChunkContext(
            page_number=page_num,
            section_number=section_num,
            section_title=section_title,
            chunk_type=self.detect_chunk_type(text)
        )
        
        return DocumentChunk(
            chunk_id=chunk_id,
            document_id=document_id,
            chunk_index=chunk_index,
            chunk_text=text,
            token_count=self.estimate_tokens(text),
            context=context
        )
    
    def chunk_file(
        self,
        file_path: str,
        metadata: Optional[DocumentMetadata] = None
    ) -> Tuple[DocumentMetadata, List[DocumentChunk]]:
        """
        Chunk a file and extract metadata.
        
        Args:
            file_path: Path to the file
            metadata: Optional pre-populated metadata
            
        Returns:
            Tuple of (DocumentMetadata, List[DocumentChunk])
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Generate document ID if not provided
        document_id = metadata.document_id if metadata else self.generate_document_id(file_path)
        
        # Extract text based on file type
        suffix = path.suffix.lower()
        
        if suffix == '.pdf':
            text, page_map = self._extract_pdf(file_path)
        elif suffix in ['.md', '.txt', '.text']:
            text = path.read_text(encoding='utf-8')
            page_map = None
        else:
            logger.warning(f"Unknown file type {suffix}, treating as text")
            text = path.read_text(encoding='utf-8')
            page_map = None
        
        # Create or update metadata
        if metadata is None:
            metadata = DocumentMetadata(
                document_id=document_id,
                source_path=str(file_path),
                title=path.stem
            )
        
        metadata.content_hash = self.compute_content_hash(text)
        
        # Apply doc-type specific chunking strategy
        self._apply_doc_type_strategy(metadata.doc_type)
        
        # Chunk the text
        chunks = self.chunk_text(text, document_id, page_map)
        
        return metadata, chunks
    
    def _extract_pdf(self, file_path: str) -> Tuple[str, Dict[int, int]]:
        """
        Extract text from PDF with page tracking.
        
        Returns:
            Tuple of (full_text, page_map) where page_map maps char position to page number
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError("PyMuPDF (fitz) required for PDF processing. Install with: pip install PyMuPDF")
        
        doc = fitz.open(file_path)
        full_text = ""
        page_map = {}
        
        for page_num, page in enumerate(doc, start=1):
            page_start = len(full_text)
            page_text = page.get_text()
            full_text += page_text + "\n\n"
            page_map[page_start] = page_num
        
        doc.close()
        return full_text, page_map


def chunk_documents(
    file_paths: List[str],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
) -> Generator[Tuple[DocumentMetadata, List[DocumentChunk]], None, None]:
    """
    Convenience generator to chunk multiple documents.
    
    Args:
        file_paths: List of file paths to process
        chunk_size: Target chunk size in tokens
        chunk_overlap: Overlap between chunks
        
    Yields:
        Tuple of (DocumentMetadata, List[DocumentChunk]) for each file
    """
    chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    for file_path in file_paths:
        try:
            metadata, chunks = chunker.chunk_file(file_path)
            yield metadata, chunks
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            continue


if __name__ == "__main__":
    # CLI for testing chunker
    import argparse
    import json
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description="Test document chunker")
    parser.add_argument("file", help="File to chunk")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="Chunk size in tokens")
    parser.add_argument("--overlap", type=int, default=DEFAULT_CHUNK_OVERLAP, help="Overlap in tokens")
    parser.add_argument("--output", help="Output JSON file for chunks")
    
    args = parser.parse_args()
    
    chunker = DocumentChunker(chunk_size=args.chunk_size, chunk_overlap=args.overlap)
    metadata, chunks = chunker.chunk_file(args.file)
    
    print(f"\n📄 Document: {metadata.title}")
    print(f"   ID: {metadata.document_id}")
    print(f"   Hash: {metadata.content_hash[:16]}...")
    print(f"   Chunks: {len(chunks)}")
    
    print(f"\n📦 Chunks:")
    for chunk in chunks[:5]:  # Show first 5
        print(f"   [{chunk.chunk_index}] {chunk.chunk_id}")
        print(f"       Type: {chunk.context.chunk_type}, Tokens: {chunk.token_count}")
        print(f"       Section: {chunk.context.section_number} - {chunk.context.section_title}")
        preview = chunk.chunk_text[:100].replace('\n', ' ')
        print(f"       Preview: {preview}...")
        print()
    
    if len(chunks) > 5:
        print(f"   ... and {len(chunks) - 5} more chunks")
    
    if args.output:
        output_data = {
            "metadata": metadata.to_dict(),
            "chunks": [c.to_dict() for c in chunks]
        }
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)
        print(f"\n✅ Output written to {args.output}")
