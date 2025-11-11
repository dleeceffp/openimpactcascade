"""
GCP Vertex AI RAG Engine Integration for Risk Assessment Platform.

UPDATED VERSION - Based on working API patterns from create_rag_corpus.py

This module provides grounding context for:
1. Preliminary risk identification (questionnaire generation)
2. Risk analysis coaching (chat assistance)

Uses Vertex AI RAG API to retrieve relevant context from a curated knowledge base
containing threat intelligence, MITRE ATT&CK data, industry reports, and compliance docs.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

# GCP Vertex AI imports
try:
    from vertexai import rag
    import vertexai
    VERTEX_AI_AVAILABLE = True
except ImportError:
    VERTEX_AI_AVAILABLE = False
    logging.warning("Vertex AI libraries not installed. RAG features will be disabled.")

logger = logging.getLogger(__name__)


@dataclass
class RAGContext:
    """Represents retrieved context from RAG engine."""
    content: str
    source: str
    relevance_score: float
    metadata: Dict[str, Any]


class VertexRAGEngine:
    """
    Vertex AI RAG Engine for grounding risk assessment context.
    
    Provides two main capabilities:
    1. Retrieve grounding context for questionnaire generation
    2. Retrieve coaching context for chat assistance
    """
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        #location: str = "northamerica-northeast1",
        location: str = "us-east1",
        corpus_display_name: Optional[str] = None,
        similarity_threshold: float = 0.5,
        enable_fallback: bool = True
    ):
        """
        Initialize Vertex AI RAG Engine.
        
        Args:
            project_id: GCP project ID (defaults to GOOGLE_CLOUD_PROJECT env var)
            location: GCP region (default: northamerica-northeast1 for Montreal)
            corpus_display_name: Display name of the RAG corpus (e.g., "oic-rarag-kb")
            similarity_threshold: Minimum similarity score (0-1, default: 0.5)
            enable_fallback: If True, gracefully degrade when RAG unavailable
        """
        self.project_id = project_id or os.environ.get('GOOGLE_CLOUD_PROJECT')
        #self.location = location or os.environ.get('GCP_REGION', 'northamerica-northeast1')
        self.location = location or os.environ.get('GCP_REGION', 'us-east1')
        self.corpus_display_name = corpus_display_name or os.environ.get('VERTEX_RAG_CORPUS')
        self.similarity_threshold = float(os.environ.get('RAG_SIMILARITY_THRESHOLD', similarity_threshold))
        self.enable_fallback = enable_fallback
        self.enabled = False
        self.rag_corpus = None
        
        if not VERTEX_AI_AVAILABLE:
            logger.warning("Vertex AI not available. RAG features disabled.")
            if not self.enable_fallback:
                raise RuntimeError("Vertex AI libraries required but not installed")
            return
        
        if not self.project_id:
            logger.warning("GOOGLE_CLOUD_PROJECT not set. RAG features disabled.")
            if not self.enable_fallback:
                raise ValueError("GOOGLE_CLOUD_PROJECT environment variable required")
            return
        
        if not self.corpus_display_name:
            logger.warning("VERTEX_RAG_CORPUS not set. RAG features disabled.")
            if not self.enable_fallback:
                raise ValueError("VERTEX_RAG_CORPUS environment variable required")
            return
        
        try:
            # Initialize Vertex AI
            vertexai.init(project=self.project_id, location=self.location)
            
            # Find corpus by display name
            self.rag_corpus = self._find_corpus_by_name(self.corpus_display_name)
            
            if self.rag_corpus:
                self.enabled = True
                logger.info(f"Vertex AI RAG initialized: project={self.project_id}, location={self.location}, corpus={self.corpus_display_name}")
            else:
                logger.warning(f"RAG corpus '{self.corpus_display_name}' not found")
                if not self.enable_fallback:
                    raise ValueError(f"RAG corpus '{self.corpus_display_name}' not found")
                
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}")
            if not self.enable_fallback:
                raise
    
    def _find_corpus_by_name(self, display_name: str) -> Optional[Any]:
        """
        Find RAG corpus by display name.
        
        Args:
            display_name: Display name to search for
            
        Returns:
            RagCorpus object or None if not found
        """
        try:
            corpora_pager = rag.list_corpora()
            corpora_list = list(corpora_pager)
            
            for corpus in corpora_list:
                if corpus.display_name == display_name:
                    logger.info(f"Found corpus: {corpus.name}")
                    return corpus
            
            logger.warning(f"Corpus with display name '{display_name}' not found")
            logger.info(f"Available corpora: {[c.display_name for c in corpora_list]}")
            return None
            
        except Exception as e:
            logger.error(f"Error listing corpora: {e}")
            return None
    
    def retrieve_risk_identification_context(
        self,
        industry: str,
        region: str,
        organization_size: Optional[str] = None,
        max_results: int = 5
    ) -> List[RAGContext]:
        """
        Retrieve grounding context for preliminary risk identification.
        
        This is used during questionnaire generation to provide authoritative
        context about threats, vulnerabilities, and attack patterns specific
        to the industry and region.
        
        Args:
            industry: Target industry (e.g., "Healthcare", "Finance")
            region: Geographic region (e.g., "Canada", "United States")
            organization_size: Optional organization size context
            max_results: Maximum number of context chunks to retrieve
            
        Returns:
            List of RAGContext objects with relevant grounding information
        """
        if not self.enabled or not self.rag_corpus:
            logger.debug("RAG not enabled, returning empty context")
            return []
        
        # Build query for risk identification
        query_parts = [
            f"cybersecurity threats vulnerabilities {industry} industry",
            f"{region} region",
            f"{datetime.now().year} recent incidents attack patterns",
            "MITRE ATT&CK techniques threat actor profiles"
        ]
        
        if organization_size:
            query_parts.append(f"organization size {organization_size}")
        
        query = " ".join(query_parts)
        
        logger.info(f"RAG query for risk identification: {query}")
        
        try:
            contexts = self._query_rag_corpus(
                query=query,
                max_results=max_results
            )
            
            logger.info(f"Retrieved {len(contexts)} context chunks for risk identification")
            return contexts
            
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            if not self.enable_fallback:
                raise
            return []
    
    def retrieve_coaching_context(
        self,
        user_question: str,
        industry: str,
        region: str,
        fair_component: Optional[str] = None,
        max_results: int = 3
    ) -> List[RAGContext]:
        """
        Retrieve coaching context for chat assistance.
        
        This is used during chat interactions to provide relevant guidance
        on risk estimation, control effectiveness, and industry best practices.
        
        Args:
            user_question: The user's question or topic
            industry: Target industry
            region: Geographic region
            fair_component: FAIR component (LEF or LM) if applicable
            max_results: Maximum number of context chunks to retrieve
            
        Returns:
            List of RAGContext objects with coaching information
        """
        if not self.enabled or not self.rag_corpus:
            logger.debug("RAG not enabled, returning empty context")
            return []
        
        # Build query for coaching
        query_parts = [user_question]
        
        if fair_component:
            if fair_component == "LEF":
                query_parts.append("loss event frequency estimation incident rates")
            elif fair_component == "LM":
                query_parts.append("loss magnitude estimation financial impact costs")
        
        query_parts.extend([
            f"{industry} industry best practices",
            f"{region} region guidance benchmarks"
        ])
        
        query = " ".join(query_parts)
        
        logger.info(f"RAG query for coaching: {query}")
        
        try:
            contexts = self._query_rag_corpus(
                query=query,
                max_results=max_results
            )
            
            logger.info(f"Retrieved {len(contexts)} context chunks for coaching")
            return contexts
            
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            if not self.enable_fallback:
                raise
            return []
    
    def _query_rag_corpus(
        self,
        query: str,
        max_results: int = 5
    ) -> List[RAGContext]:
        """
        Internal method to query the RAG corpus using Vertex AI RAG API.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            
        Returns:
            List of RAGContext objects
        """
        if not self.rag_corpus:
            logger.warning("RAG corpus not available")
            return []
        
        try:
            # Execute RAG retrieval query using the corpus
            # Note: Parameter names may vary by Vertex AI version
            # Try with minimal parameters first
            try:
                # Try with basic parameters only (most compatible)
                response = rag.retrieval_query(
                    rag_resources=[
                        rag.RagResource(
                            rag_corpus=self.rag_corpus.name
                        )
                    ],
                    text=query
                )
            except TypeError as e:
                # If basic call fails, log and re-raise
                logger.error(f"RAG API call failed even with minimal parameters: {e}")
                raise
            
            # Parse response and create RAGContext objects
            contexts = []
            
            if hasattr(response, 'contexts') and response.contexts:
                for i, context in enumerate(response.contexts.contexts):
                    # Extract relevance score (distance is inverse of similarity)
                    distance = getattr(context, 'distance', 1.0)
                    similarity_score = max(0.0, 1.0 - distance)
                    
                    # Apply similarity threshold filter
                    if similarity_score < self.similarity_threshold:
                        logger.debug(f"Skipping context {i+1}: score {similarity_score:.3f} below threshold {self.similarity_threshold}")
                        continue
                    
                    # Extract source information
                    source_uri = getattr(context, 'source_uri', f"Document {i+1}")
                    
                    # Extract text content
                    text_content = getattr(context, 'text', '')
                    
                    # Create RAGContext
                    rag_context = RAGContext(
                        content=text_content,
                        source=source_uri,
                        relevance_score=similarity_score,
                        metadata={}
                    )
                    
                    contexts.append(rag_context)
                    logger.debug(f"Retrieved context {i+1}: score={similarity_score:.3f}, source={source_uri}")
            
            # Sort by relevance score (descending)
            contexts.sort(key=lambda x: x.relevance_score, reverse=True)
            
            # Limit to max_results (post-processing since API may not support parameter)
            contexts = contexts[:max_results]
            
            return contexts
            
        except Exception as e:
            logger.error(f"Error querying RAG corpus: {e}", exc_info=True)
            if not self.enable_fallback:
                raise
            return []
    
    def format_context_for_prompt(self, contexts: List[RAGContext], max_length: int = 4000) -> str:
        """
        Format retrieved RAG contexts for inclusion in prompts.
        
        Args:
            contexts: List of RAGContext objects
            max_length: Maximum character length for formatted context
            
        Returns:
            Formatted string for prompt injection
        """
        if not contexts:
            return ""
        
        formatted_parts = ["**Grounding Context from Authoritative Knowledge Base:**\n"]
        
        total_length = len(formatted_parts[0])
        included_contexts = 0
        
        for i, ctx in enumerate(contexts, 1):
            # Format single context
            context_text = f"\n**Source {i}** (Relevance: {ctx.relevance_score:.2f}):\n"
            context_text += f"- Source: {ctx.source}\n"
            
            # Truncate content if too long
            if len(ctx.content) > 500:
                context_text += f"- Content: {ctx.content[:500]}...\n"
            else:
                context_text += f"- Content: {ctx.content}\n"
            
            # Check if adding this would exceed max length
            if total_length + len(context_text) > max_length:
                logger.debug(f"Truncating context at {included_contexts} items to stay under {max_length} chars")
                break
            
            formatted_parts.append(context_text)
            total_length += len(context_text)
            included_contexts += 1
        
        formatted_parts.append(f"\n**{included_contexts} authoritative source(s) provided above. Use this grounding context to inform your response with verified, factual information.**\n")
        
        return "\n".join(formatted_parts)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get RAG engine status for monitoring.
        
        Returns:
            Dictionary with status information
        """
        return {
            "enabled": self.enabled,
            "vertex_ai_available": VERTEX_AI_AVAILABLE,
            "project_id": self.project_id,
            "location": self.location,
            "corpus_display_name": self.corpus_display_name,
            "corpus_found": self.rag_corpus is not None,
            "corpus_resource_name": self.rag_corpus.name if self.rag_corpus else None,
            "similarity_threshold": self.similarity_threshold,
            "fallback_enabled": self.enable_fallback
        }


# Global RAG engine instance
_rag_engine = None


def get_rag_engine(
    project_id: Optional[str] = None,
    location: str = "northamerica-northeast1",
    corpus_display_name: Optional[str] = None,
    enable_fallback: bool = True
) -> VertexRAGEngine:
    """
    Get or create the global RAG engine instance.
    
    Args:
        project_id: GCP project ID
        location: GCP region (default: northamerica-northeast1)
        corpus_display_name: RAG corpus display name
        enable_fallback: Enable graceful degradation
        
    Returns:
        VertexRAGEngine instance
    """
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = VertexRAGEngine(
            project_id=project_id,
            location=location,
            corpus_display_name=corpus_display_name,
            enable_fallback=enable_fallback
        )
    return _rag_engine


if __name__ == '__main__':
    # Test the RAG engine
    print("=== Vertex AI RAG Engine Test ===\n")
    
    # Initialize engine
    engine = VertexRAGEngine(enable_fallback=True)
    
    # Check status
    status = engine.get_status()
    print("RAG Engine Status:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    if engine.enabled:
        print("\n✅ RAG engine is enabled and ready")
        
        # Test risk identification context retrieval
        print("\nTesting risk identification context retrieval...")
        try:
            contexts = engine.retrieve_risk_identification_context(
                industry="Healthcare",
                region="Canada",
                organization_size="500 employees",
                max_results=5
            )
            print(f"Retrieved {len(contexts)} contexts")
            
            if contexts:
                print(f"\nTop result:")
                print(f"  Relevance: {contexts[0].relevance_score:.3f}")
                print(f"  Source: {contexts[0].source}")
                print(f"  Content: {contexts[0].content[:200]}...")
                
                # Show formatted context
                print("\nFormatted context for prompt:")
                formatted = engine.format_context_for_prompt(contexts[:3])
                print(formatted[:500] + "...")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test coaching context retrieval
        print("\nTesting coaching context retrieval...")
        try:
            contexts = engine.retrieve_coaching_context(
                user_question="How to estimate ransomware frequency?",
                industry="Healthcare",
                region="Canada",
                fair_component="LEF",
                max_results=3
            )
            print(f"Retrieved {len(contexts)} contexts")
            
            if contexts:
                print(f"\nTop result:")
                print(f"  Relevance: {contexts[0].relevance_score:.3f}")
                print(f"  Source: {contexts[0].source}")
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print("\n⚠️  RAG engine is disabled (fallback mode)")
        print("\nTo enable:")
        print("  1. Install: pip install google-cloud-aiplatform")
        print("  2. Set: export GOOGLE_CLOUD_PROJECT=your-project-id")
        print("  3. Set: export VERTEX_RAG_CORPUS=your-corpus-display-name")
        print("  4. Set: export GCP_REGION=northamerica-northeast1")
        print("  5. Authenticate: gcloud auth application-default login")
    
    print("\n=== Test Complete ===")
