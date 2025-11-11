"""
GCP Vertex AI RAG Engine Integration for Risk Assessment Platform.

UPDATED VERSION - Added Service Account Authentication Support for Remote Servers

This module provides grounding context for:
1. Preliminary risk identification (questionnaire generation)
2. Risk analysis coaching (chat assistance)

Uses Vertex AI RAG API to retrieve relevant context from a curated knowledge base
containing threat intelligence, MITRE ATT&CK data, industry reports, and compliance docs.

Authentication Methods (in order of precedence):
1. Service Account Key File (GOOGLE_APPLICATION_CREDENTIALS env var) - RECOMMENDED FOR SERVERS
2. Application Default Credentials (ADC) - gcloud auth application-default login
"""

import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

# GCP Vertex AI imports
try:
    import vertexai
    try:
        # Try new import path (v1.50+)
        from vertexai import rag
    except ImportError:
        # Fall back to preview path (v1.38-1.49)
        from vertexai.preview import rag
    from google.auth import default as google_auth_default
    from google.oauth2 import service_account
    VERTEX_AI_AVAILABLE = True
except ImportError as e:
    VERTEX_AI_AVAILABLE = False
    logging.warning(f"Vertex AI libraries not installed. RAG features will be disabled. Error: {e}")

logger = logging.getLogger(__name__)
# Set to INFO level for debugging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')


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
    
    Authentication:
    - Automatically uses service account if GOOGLE_APPLICATION_CREDENTIALS is set
    - Falls back to Application Default Credentials if not set
    """
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        location: str = "us-east1",
        corpus_display_name: Optional[str] = None,
        similarity_threshold: float = 0.2,  # Lowered from 0.5 based on typical scores
        enable_fallback: bool = True,
        service_account_key_path: Optional[str] = None
    ):
        """
        Initialize Vertex AI RAG Engine.
        
        Args:
            project_id: GCP project ID (defaults to GOOGLE_CLOUD_PROJECT env var)
            location: GCP region (default: us-east1)
            corpus_display_name: Display name of the RAG corpus
            similarity_threshold: Minimum similarity score (0-1, default: 0.2)
                                 Note: Typical RAG scores range 0.2-0.4 for good matches.
                                 Can be overridden via RAG_SIMILARITY_THRESHOLD env var.
            enable_fallback: If True, gracefully degrade when RAG unavailable
            service_account_key_path: Path to service account JSON key file
                                     (defaults to GOOGLE_APPLICATION_CREDENTIALS env var)
        """
        self.project_id = project_id or os.environ.get('GOOGLE_CLOUD_PROJECT')
        self.location = location or os.environ.get('GCP_REGION', 'us-east1')
        self.corpus_display_name = corpus_display_name or os.environ.get('VERTEX_RAG_CORPUS')
        # Default threshold lowered to 0.2 based on typical RAG corpus scores
        # Can be overridden via RAG_SIMILARITY_THRESHOLD environment variable
        self.similarity_threshold = float(os.environ.get('RAG_SIMILARITY_THRESHOLD', 0.2))
        self.enable_fallback = enable_fallback
        self.enabled = False
        self.rag_corpus = None
        self.credentials = None
        
        # Get service account key path from parameter or environment
        self.service_account_key_path = service_account_key_path or os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        
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
            # Initialize credentials
            self._initialize_credentials()
            
            # Initialize Vertex AI with credentials
            if self.credentials:
                logger.info(f"Initializing Vertex AI with service account credentials")
                vertexai.init(
                    project=self.project_id,
                    location=self.location,
                    credentials=self.credentials
                )
            else:
                logger.info(f"Initializing Vertex AI with Application Default Credentials")
                vertexai.init(project=self.project_id, location=self.location)
            
            # Find corpus by display name
            self.rag_corpus = self._find_corpus_by_name(self.corpus_display_name)
            
            if self.rag_corpus:
                self.enabled = True
                auth_method = "service account" if self.credentials else "ADC"
                logger.info(f"✅ Vertex AI RAG initialized: project={self.project_id}, location={self.location}, corpus={self.corpus_display_name}, auth={auth_method}")
            else:
                logger.warning(f"RAG corpus '{self.corpus_display_name}' not found")
                if not self.enable_fallback:
                    raise ValueError(f"RAG corpus '{self.corpus_display_name}' not found")
                
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}")
            if not self.enable_fallback:
                raise
    
    def _initialize_credentials(self):
        """
        Initialize Google Cloud credentials.
        
        Priority:
        1. Service account key file (GOOGLE_APPLICATION_CREDENTIALS)
        2. Application Default Credentials (ADC)
        """
        # Try service account key file first
        if self.service_account_key_path:
            if os.path.exists(self.service_account_key_path):
                try:
                    self.credentials = service_account.Credentials.from_service_account_file(
                        self.service_account_key_path,
                        scopes=['https://www.googleapis.com/auth/cloud-platform']
                    )
                    logger.info(f"✅ Loaded service account credentials from: {self.service_account_key_path}")
                    return
                except Exception as e:
                    logger.error(f"Failed to load service account key: {e}")
                    if not self.enable_fallback:
                        raise
            else:
                logger.warning(f"Service account key file not found: {self.service_account_key_path}")
        
        # Fall back to ADC
        logger.info("Using Application Default Credentials (ADC)")
        # credentials will be None, and vertexai.init() will use ADC automatically
        self.credentials = None
    
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
        based on the user's question and the FAIR component they're working on.
        
        Args:
            user_question: User's question or topic
            industry: Target industry for context
            region: Geographic region for context
            fair_component: FAIR component (LEF/LM) for targeted guidance
            max_results: Maximum number of context chunks to retrieve
            
        Returns:
            List of RAGContext objects with relevant coaching information
        """
        if not self.enabled or not self.rag_corpus:
            logger.debug("RAG not enabled, returning empty context")
            return []
        
        # Build query for coaching
        query_parts = [user_question]
        
        if fair_component:
            if fair_component == 'LEF':
                query_parts.append("loss event frequency probability estimation attack likelihood")
            elif fair_component == 'LM':
                query_parts.append("loss magnitude impact cost estimation financial impact")
        
        query_parts.append(f"{industry} {region}")
        
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
        Query the RAG corpus and return contexts.
        
        Args:
            query: Search query text
            max_results: Maximum results to return
            
        Returns:
            List of RAGContext objects
        """
        if not self.rag_corpus:
            return []
        
        try:
            # Retrieve from RAG corpus
            # Note: similarity_top_k parameter was removed from the API
            # We handle result limiting via post-processing (see below)
            response = rag.retrieval_query(
                rag_resources=[
                    rag.RagResource(
                        rag_corpus=self.rag_corpus.name,
                    )
                ],
                text=query
            )
            
            # Parse response and create RAGContext objects
            contexts = []
            
            # Debug: Log response structure
            logger.info(f"Response type: {type(response)}")
            logger.info(f"Has contexts attr: {hasattr(response, 'contexts')}")
            
            if hasattr(response, 'contexts') and response.contexts:
                logger.info(f"response.contexts type: {type(response.contexts)}")
                logger.info(f"Has contexts.contexts: {hasattr(response.contexts, 'contexts')}")
                
                if hasattr(response.contexts, 'contexts'):
                    contexts_list = response.contexts.contexts
                    logger.info(f"Number of raw contexts: {len(contexts_list)}")
                    
                    for i, context in enumerate(contexts_list):
                        logger.debug(f"Context {i+1} attributes: {[x for x in dir(context) if not x.startswith('_')]}")
                        
                        # Extract relevance score - try multiple attribute names
                        distance = None
                        similarity_score = 0.0
                        
                        # Try different possible attribute names for score
                        for score_attr in ['distance', 'score', 'relevance_score', 'similarity']:
                            if hasattr(context, score_attr):
                                distance = getattr(context, score_attr)
                                logger.debug(f"Found score attribute '{score_attr}': {distance}")
                                break
                        
                        if distance is not None:
                            # If it's called 'distance', convert to similarity (inverse)
                            if score_attr == 'distance':
                                similarity_score = max(0.0, 1.0 - float(distance))
                            else:
                                # Otherwise assume it's already a similarity score
                                similarity_score = float(distance)
                        else:
                            logger.warning(f"Context {i+1}: No score attribute found, using default 0.5")
                            similarity_score = 0.5
                        
                        logger.debug(f"Context {i+1}: similarity_score={similarity_score:.3f}, threshold={self.similarity_threshold}")
                        
                        # Apply similarity threshold filter
                        if similarity_score < self.similarity_threshold:
                            logger.info(f"Skipping context {i+1}: score {similarity_score:.3f} below threshold {self.similarity_threshold}")
                            continue
                        
                        # Extract source information - try multiple attribute names
                        source_uri = None
                        for source_attr in ['source_uri', 'source', 'uri', 'document_id', 'file_name']:
                            if hasattr(context, source_attr):
                                source_uri = getattr(context, source_attr)
                                break
                        
                        if not source_uri:
                            source_uri = f"Document {i+1}"
                        
                        # Extract text content - try multiple attribute names
                        text_content = None
                        for text_attr in ['text', 'content', 'chunk', 'passage']:
                            if hasattr(context, text_attr):
                                text_content = getattr(context, text_attr)
                                if text_content:  # Make sure it's not empty
                                    break
                        
                        if not text_content:
                            logger.warning(f"Context {i+1}: No text content found")
                            text_content = ''
                        
                        # Create RAGContext
                        rag_context = RAGContext(
                            content=text_content,
                            source=source_uri,
                            relevance_score=similarity_score,
                            metadata={}
                        )
                        
                        contexts.append(rag_context)
                        logger.info(f"Retrieved context {i+1}: score={similarity_score:.3f}, source={source_uri}, length={len(text_content)}")
                else:
                    logger.warning("response.contexts exists but has no 'contexts' attribute")
            else:
                logger.warning("Response has no 'contexts' attribute or it's empty")

            
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
        auth_method = "service_account" if self.credentials else "adc"
        
        return {
            "enabled": self.enabled,
            "vertex_ai_available": VERTEX_AI_AVAILABLE,
            "project_id": self.project_id,
            "location": self.location,
            "corpus_display_name": self.corpus_display_name,
            "corpus_found": self.rag_corpus is not None,
            "corpus_resource_name": self.rag_corpus.name if self.rag_corpus else None,
            "similarity_threshold": self.similarity_threshold,
            "fallback_enabled": self.enable_fallback,
            "auth_method": auth_method,
            "service_account_key_configured": self.service_account_key_path is not None
        }


# Global RAG engine instance
_rag_engine = None


def get_rag_engine(
    project_id: Optional[str] = None,
    location: str = "us-east1",
    corpus_display_name: Optional[str] = None,
    enable_fallback: bool = True,
    service_account_key_path: Optional[str] = None
) -> VertexRAGEngine:
    """
    Get or create the global RAG engine instance.
    
    Args:
        project_id: GCP project ID
        location: GCP region (default: us-east1)
        corpus_display_name: RAG corpus display name
        enable_fallback: Enable graceful degradation
        service_account_key_path: Path to service account JSON key
        
    Returns:
        VertexRAGEngine instance
    """
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = VertexRAGEngine(
            project_id=project_id,
            location=location,
            corpus_display_name=corpus_display_name,
            enable_fallback=enable_fallback,
            service_account_key_path=service_account_key_path
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
        print("  4. Set: export GCP_REGION=us-east1")
        print("  5. Authenticate using ONE of these methods:")
        print("     METHOD 1 (Recommended for servers):")
        print("       - Create service account in GCP Console")
        print("       - Download JSON key file")
        print("       - Set: export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json")
        print("     METHOD 2 (For local development):")
        print("       - Run: gcloud auth application-default login")
    
    print("\n=== Test Complete ===")
