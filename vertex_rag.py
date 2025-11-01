"""
GCP Vertex AI RAG Engine Integration for Risk Assessment Platform.

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
    from google.cloud import aiplatform
    from vertexai.preview import rag
    from vertexai.preview.generative_models import GenerativeModel, Tool
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
        location: str = "northamerica-northeast1",
        rag_corpus_name: Optional[str] = None,
        enable_fallback: bool = True
    ):
        """
        Initialize Vertex AI RAG Engine.
        
        Args:
            project_id: GCP project ID (defaults to GOOGLE_CLOUD_PROJECT env var)
            location: GCP region (default: northamerica-northeast1 - Montreal, Canada)
            rag_corpus_name: Name of the RAG corpus to use
            enable_fallback: If True, gracefully degrade when RAG unavailable
        """
        self.project_id = project_id or os.environ.get('GOOGLE_CLOUD_PROJECT')
        self.location = location
        self.rag_corpus_name = rag_corpus_name or os.environ.get('VERTEX_RAG_CORPUS')
        self.enable_fallback = enable_fallback
        self.enabled = False
        
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
        
        try:
            # Initialize Vertex AI
            aiplatform.init(project=self.project_id, location=self.location)
            self.enabled = True
            logger.info(f"Vertex AI RAG initialized: project={self.project_id}, location={self.location}")
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}")
            if not self.enable_fallback:
                raise
    
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
        if not self.enabled:
            logger.debug("RAG not enabled, returning empty context")
            return []
        
        # Build query for risk identification
        query_parts = [
            f"cybersecurity threats and vulnerabilities for {industry} industry",
            f"in {region}",
            "recent incidents and attack patterns",
            "MITRE ATT&CK techniques",
            "threat actor profiles"
        ]
        
        if organization_size:
            query_parts.append(f"organization size: {organization_size}")
        
        query = " ".join(query_parts)
        
        logger.info(f"RAG query for risk identification: {query}")
        
        try:
            contexts = self._query_rag_corpus(
                query=query,
                max_results=max_results,
                filter_metadata={
                    "industry": industry,
                    "region": region,
                    "document_type": ["threat_intelligence", "mitre_attack", "incident_report"]
                }
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
        if not self.enabled:
            logger.debug("RAG not enabled, returning empty context")
            return []
        
        # Build query for coaching
        query_parts = [user_question]
        
        if fair_component:
            if fair_component == "LEF":
                query_parts.append("loss event frequency estimation")
            elif fair_component == "LM":
                query_parts.append("loss magnitude estimation financial impact")
        
        query_parts.extend([
            f"{industry} industry",
            f"{region} region",
            "best practices and guidance"
        ])
        
        query = " ".join(query_parts)
        
        logger.info(f"RAG query for coaching: {query}")
        
        try:
            contexts = self._query_rag_corpus(
                query=query,
                max_results=max_results,
                filter_metadata={
                    "industry": industry,
                    "region": region,
                    "document_type": ["guidance", "best_practices", "case_studies", "benchmarks"]
                }
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
        max_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[RAGContext]:
        """
        Internal method to query the RAG corpus.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            filter_metadata: Optional metadata filters
            
        Returns:
            List of RAGContext objects
        """
        if not self.rag_corpus_name:
            logger.warning("RAG corpus name not configured")
            return []
        
        try:
            # Query the RAG corpus using Vertex AI RAG API
            # Note: This is a placeholder for the actual Vertex AI RAG API call
            # The exact API may vary based on Vertex AI RAG implementation
            
            # Example structure (adjust based on actual Vertex AI RAG API):
            # response = rag.retrieval_query(
            #     rag_resources=[
            #         rag.RagResource(
            #             rag_corpus=self.rag_corpus_name,
            #         )
            #     ],
            #     text=query,
            #     similarity_top_k=max_results,
            #     vector_distance_threshold=0.5,
            # )
            
            # For now, return empty list as placeholder
            # This will be replaced with actual Vertex AI RAG API calls
            logger.warning("RAG corpus query not yet implemented - placeholder")
            
            # Placeholder return structure
            contexts = []
            
            # TODO: Parse response and create RAGContext objects
            # for result in response.contexts:
            #     contexts.append(RAGContext(
            #         content=result.text,
            #         source=result.source_uri,
            #         relevance_score=result.score,
            #         metadata=result.metadata
            #     ))
            
            return contexts
            
        except Exception as e:
            logger.error(f"Error querying RAG corpus: {e}")
            raise
    
    def format_context_for_prompt(self, contexts: List[RAGContext]) -> str:
        """
        Format retrieved RAG contexts for inclusion in prompts.
        
        Args:
            contexts: List of RAGContext objects
            
        Returns:
            Formatted string for prompt injection
        """
        if not contexts:
            return ""
        
        formatted_parts = ["**Grounding Context from Knowledge Base:**\n"]
        
        for i, ctx in enumerate(contexts, 1):
            formatted_parts.append(f"\n**Source {i}** (Relevance: {ctx.relevance_score:.2f}):")
            formatted_parts.append(f"- Source: {ctx.source}")
            formatted_parts.append(f"- Content: {ctx.content}")
            
            if ctx.metadata:
                formatted_parts.append(f"- Metadata: {ctx.metadata}")
        
        formatted_parts.append("\n**Use this grounding context to inform your response.**\n")
        
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
            "rag_corpus": self.rag_corpus_name,
            "fallback_enabled": self.enable_fallback
        }


# Global RAG engine instance
_rag_engine = None


def get_rag_engine(
    project_id: Optional[str] = None,
    location: str = "northamerica-northeast1",
    rag_corpus_name: Optional[str] = None,
    enable_fallback: bool = True
) -> VertexRAGEngine:
    """
    Get or create the global RAG engine instance.
    
    Args:
        project_id: GCP project ID
        location: GCP region
        rag_corpus_name: RAG corpus name
        enable_fallback: Enable graceful degradation
        
    Returns:
        VertexRAGEngine instance
    """
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = VertexRAGEngine(
            project_id=project_id,
            location=location,
            rag_corpus_name=rag_corpus_name,
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
        contexts = engine.retrieve_risk_identification_context(
            industry="Healthcare",
            region="Canada",
            organization_size="500 employees"
        )
        print(f"Retrieved {len(contexts)} contexts")
        
        # Test coaching context retrieval
        print("\nTesting coaching context retrieval...")
        contexts = engine.retrieve_coaching_context(
            user_question="How to estimate ransomware frequency?",
            industry="Healthcare",
            region="Canada",
            fair_component="LEF"
        )
        print(f"Retrieved {len(contexts)} contexts")
    else:
        print("\n⚠️  RAG engine is disabled (fallback mode)")
        print("To enable:")
        print("  1. Install: pip install google-cloud-aiplatform")
        print("  2. Set: export GOOGLE_CLOUD_PROJECT=your-project-id")
        print("  3. Set: export VERTEX_RAG_CORPUS=your-corpus-name")
        print("  4. Authenticate: gcloud auth application-default login")
    
    print("\n=== Test Complete ===")
