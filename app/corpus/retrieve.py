import os
import json
from dataclasses import dataclass
from typing import List, Dict, Optional, Any

@dataclass
class ContextSlice:
    docs: List[Any]
    total_tokens: int
    citations_manifest: Dict[str, str]

class CorpusRetriever:
    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or os.environ.get('CORPUS_BUCKET_NAME')
        self.index_path = 'corpus/_index.json'
        
    @property
    def enabled(self) -> bool:
        # Check if local index exists or if a bucket is configured
        return os.path.exists(self.index_path) or bool(self.bucket_name)

    def retrieve_risk_identification_context(
        self,
        industry: str,
        region: str,
        organization_size: Optional[str] = None,
        max_results: int = 5,
        tier: str = "free"
    ) -> List:
        """
        Retrieves context slice based on facets.
        Currently returns an empty list if the corpus index is missing/empty,
        forcing the generator to fall back to intelligent web search.
        """
        # If no index exists, return empty to trigger web search fallback
        if not os.path.exists(self.index_path):
            print("ℹ️  Corpus index not found. Defaulting to web search.")
            return []
            
        try:
            with open(self.index_path, 'r') as f:
                index = json.load(f)
                if not index:
                    print("ℹ️  Corpus index is empty. Defaulting to web search.")
                    return []
        except (FileNotFoundError, json.JSONDecodeError):
            print("ℹ️  Corpus index invalid or missing. Defaulting to web search.")
            return []
            
        # TODO: Implement actual metadata filtering logic based on ADR-0012
        return []

    def retrieve_coaching_context(
        self,
        user_question: str,
        industry: str,
        region: str,
        fair_component: Optional[str] = None,
        max_results: int = 5
    ) -> List:
        return []

    def format_context_for_prompt(self, contexts: List) -> str:
        if not contexts:
            return ""
        # TODO: Format markdown context blocks
        return ""

def get_rag_engine(enable_fallback: bool = True) -> CorpusRetriever:
    """Factory function maintaining the same signature for backwards compatibility."""
    return CorpusRetriever()
