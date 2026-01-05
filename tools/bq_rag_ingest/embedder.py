"""
Embedding Generation using Vertex AI.

Generates vector embeddings for text chunks using Google's text-embedding models.
Supports batching for efficient processing of large document sets.
"""

import os
import logging
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import hashlib

logger = logging.getLogger(__name__)

# Configuration
DEFAULT_MODEL = "text-embedding-004"
DEFAULT_BATCH_SIZE = 250  # Vertex AI limit
DEFAULT_TASK_TYPE = "RETRIEVAL_DOCUMENT"  # Optimized for RAG
EMBEDDING_DIMENSION = 768  # text-embedding-004 output dimension


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    embedding_id: str
    chunk_id: str
    embedding: List[float]
    model_id: str
    model_version: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary for BigQuery insertion."""
        return {
            "embedding_id": self.embedding_id,
            "chunk_id": self.chunk_id,
            "embedding": self.embedding,
            "model_id": self.model_id,
            "model_version": self.model_version,
        }


class VertexEmbedder:
    """
    Generates embeddings using Vertex AI text-embedding models.
    
    Usage:
        embedder = VertexEmbedder(project_id="my-project")
        results = embedder.embed_texts(["text1", "text2"], ["chunk_id1", "chunk_id2"])
    """
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        location: str = "us-central1",
        model_id: str = DEFAULT_MODEL,
        task_type: str = DEFAULT_TASK_TYPE
    ):
        """
        Initialize Vertex AI embedder.
        
        Args:
            project_id: GCP project ID (defaults to GOOGLE_CLOUD_PROJECT env var)
            location: Vertex AI location
            model_id: Embedding model ID
            task_type: Task type for embeddings (RETRIEVAL_DOCUMENT, RETRIEVAL_QUERY, etc.)
        """
        self.project_id = project_id or os.environ.get('GOOGLE_CLOUD_PROJECT')
        if not self.project_id:
            raise ValueError("project_id required (or set GOOGLE_CLOUD_PROJECT env var)")
        
        self.location = location
        self.model_id = model_id
        self.task_type = task_type
        self.model_version = "001"  # Will be updated from API response
        
        # Initialize Vertex AI
        self._init_vertex()
        
        logger.info(f"VertexEmbedder initialized: model={model_id}, location={location}")
    
    def _init_vertex(self):
        """Initialize Vertex AI SDK."""
        try:
            import vertexai
            from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
            
            vertexai.init(project=self.project_id, location=self.location)
            self.model = TextEmbeddingModel.from_pretrained(self.model_id)
            self.TextEmbeddingInput = TextEmbeddingInput
            self._available = True
            
            logger.info(f"✅ Vertex AI initialized: {self.model_id}")
            
        except ImportError as e:
            logger.warning(f"Vertex AI SDK not available: {e}")
            self._available = False
            self.model = None
            self.TextEmbeddingInput = None
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}")
            self._available = False
            self.model = None
            self.TextEmbeddingInput = None
    
    @property
    def available(self) -> bool:
        """Check if embedder is available."""
        return self._available
    
    def generate_embedding_id(self, chunk_id: str, model_id: str) -> str:
        """Generate unique embedding ID."""
        hash_input = f"{chunk_id}_{model_id}"
        hash_val = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        return f"emb_{chunk_id}_{hash_val}"
    
    def embed_text(self, text: str, chunk_id: str) -> Optional[EmbeddingResult]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            chunk_id: Associated chunk ID
            
        Returns:
            EmbeddingResult or None if failed
        """
        results = self.embed_texts([text], [chunk_id])
        return results[0] if results else None
    
    def embed_texts(
        self,
        texts: List[str],
        chunk_ids: List[str],
        batch_size: int = DEFAULT_BATCH_SIZE,
        retry_count: int = 3,
        retry_delay: float = 1.0
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts with batching.
        
        Args:
            texts: List of texts to embed
            chunk_ids: List of corresponding chunk IDs
            batch_size: Batch size for API calls
            retry_count: Number of retries on failure
            retry_delay: Delay between retries in seconds
            
        Returns:
            List of EmbeddingResult objects
        """
        if not self._available:
            logger.error("Vertex AI not available, cannot generate embeddings")
            return []
        
        if len(texts) != len(chunk_ids):
            raise ValueError("texts and chunk_ids must have same length")
        
        results = []
        total_batches = (len(texts) + batch_size - 1) // batch_size
        
        for batch_idx in range(0, len(texts), batch_size):
            batch_texts = texts[batch_idx:batch_idx + batch_size]
            batch_ids = chunk_ids[batch_idx:batch_idx + batch_size]
            batch_num = batch_idx // batch_size + 1
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_texts)} texts)")
            
            # Prepare inputs
            inputs = [
                self.TextEmbeddingInput(text=text, task_type=self.task_type)
                for text in batch_texts
            ]
            
            # Call API with retries
            for attempt in range(retry_count):
                try:
                    embeddings = self.model.get_embeddings(inputs)
                    
                    # Process results
                    for i, embedding in enumerate(embeddings):
                        chunk_id = batch_ids[i]
                        embedding_id = self.generate_embedding_id(chunk_id, self.model_id)
                        
                        result = EmbeddingResult(
                            embedding_id=embedding_id,
                            chunk_id=chunk_id,
                            embedding=embedding.values,
                            model_id=self.model_id,
                            model_version=self.model_version
                        )
                        results.append(result)
                    
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    logger.warning(f"Batch {batch_num} attempt {attempt + 1} failed: {e}")
                    if attempt < retry_count - 1:
                        time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    else:
                        logger.error(f"Batch {batch_num} failed after {retry_count} attempts")
        
        logger.info(f"Generated {len(results)} embeddings")
        return results
    
    def embed_for_query(self, query_text: str) -> Optional[List[float]]:
        """
        Generate embedding for a search query.
        
        Uses RETRIEVAL_QUERY task type for optimal query embeddings.
        
        Args:
            query_text: Query text to embed
            
        Returns:
            Embedding vector or None if failed
        """
        if not self._available:
            logger.error("Vertex AI not available")
            return None
        
        try:
            # Use RETRIEVAL_QUERY for query embeddings
            input_obj = self.TextEmbeddingInput(
                text=query_text,
                task_type="RETRIEVAL_QUERY"
            )
            
            embeddings = self.model.get_embeddings([input_obj])
            return embeddings[0].values if embeddings else None
            
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            return None


class MockEmbedder:
    """
    Mock embedder for testing without Vertex AI.
    
    Generates deterministic pseudo-random embeddings based on text hash.
    """
    
    def __init__(self, dimension: int = EMBEDDING_DIMENSION):
        """Initialize mock embedder."""
        self.dimension = dimension
        self.model_id = "mock-embedding-model"
        self.model_version = "mock-001"
        logger.warning("Using MockEmbedder - embeddings are NOT real!")
    
    @property
    def available(self) -> bool:
        return True
    
    def _generate_mock_embedding(self, text: str) -> List[float]:
        """Generate deterministic mock embedding from text hash."""
        import random
        
        # Use text hash as seed for reproducibility
        seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)
        
        # Generate normalized random vector
        embedding = [rng.gauss(0, 1) for _ in range(self.dimension)]
        norm = sum(x**2 for x in embedding) ** 0.5
        return [x / norm for x in embedding]
    
    def generate_embedding_id(self, chunk_id: str, model_id: str) -> str:
        hash_input = f"{chunk_id}_{model_id}"
        hash_val = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        return f"emb_{chunk_id}_{hash_val}"
    
    def embed_text(self, text: str, chunk_id: str) -> EmbeddingResult:
        embedding = self._generate_mock_embedding(text)
        embedding_id = self.generate_embedding_id(chunk_id, self.model_id)
        
        return EmbeddingResult(
            embedding_id=embedding_id,
            chunk_id=chunk_id,
            embedding=embedding,
            model_id=self.model_id,
            model_version=self.model_version
        )
    
    def embed_texts(
        self,
        texts: List[str],
        chunk_ids: List[str],
        **kwargs
    ) -> List[EmbeddingResult]:
        return [
            self.embed_text(text, chunk_id)
            for text, chunk_id in zip(texts, chunk_ids)
        ]
    
    def embed_for_query(self, query_text: str) -> List[float]:
        return self._generate_mock_embedding(query_text)


def get_embedder(
    project_id: Optional[str] = None,
    use_mock: bool = False,
    **kwargs
) -> Any:
    """
    Factory function to get appropriate embedder.
    
    Args:
        project_id: GCP project ID
        use_mock: Force use of mock embedder
        **kwargs: Additional arguments for VertexEmbedder
        
    Returns:
        VertexEmbedder or MockEmbedder instance
    """
    if use_mock:
        return MockEmbedder()
    
    try:
        embedder = VertexEmbedder(project_id=project_id, **kwargs)
        if embedder.available:
            return embedder
    except Exception as e:
        logger.warning(f"Failed to initialize VertexEmbedder: {e}")
    
    logger.warning("Falling back to MockEmbedder")
    return MockEmbedder()


if __name__ == "__main__":
    # CLI for testing embedder
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description="Test embedding generation")
    parser.add_argument("--text", default="This is a test document about cybersecurity risk management.", 
                        help="Text to embed")
    parser.add_argument("--project", help="GCP project ID")
    parser.add_argument("--mock", action="store_true", help="Use mock embedder")
    
    args = parser.parse_args()
    
    embedder = get_embedder(project_id=args.project, use_mock=args.mock)
    
    print(f"\n🔢 Embedder: {embedder.model_id}")
    print(f"   Available: {embedder.available}")
    
    result = embedder.embed_text(args.text, "test_chunk_001")
    
    if result:
        print(f"\n✅ Embedding generated:")
        print(f"   ID: {result.embedding_id}")
        print(f"   Dimension: {len(result.embedding)}")
        print(f"   First 5 values: {result.embedding[:5]}")
        print(f"   Model: {result.model_id} v{result.model_version}")
    else:
        print("\n❌ Failed to generate embedding")
