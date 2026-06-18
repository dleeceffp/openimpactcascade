"""Web search integration for recent threat intelligence."""

import os
import logging
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger("oic.attack_flow.web_search")


class WebSearchClient:
    """Google Custom Search API client for threat intelligence."""

    def __init__(self):
        self.api_key = os.environ.get("GOOGLE_SEARCH_API_KEY")
        self.cse_id = os.environ.get("GOOGLE_SEARCH_CSE_ID")
        self.enabled = bool(self.api_key and self.cse_id)

        if not self.enabled:
            logger.warning("Web search disabled - missing GOOGLE_SEARCH_API_KEY or GOOGLE_SEARCH_CSE_ID")

    def search_threats(self, industry: str, region: str, max_results: int = 5) -> List[Dict]:
        """Search for recent threats affecting the industry/region."""
        if not self.enabled:
            return []

        # Calculate date 90 days ago for recent threats
        cutoff_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

        queries = [
            f"cybersecurity threats {industry} {region} after:{cutoff_date}",
            f"ransomware attacks {industry} {region} 2024 2025",
            f"data breach {industry} {region} incident",
        ]

        results = []
        for query in queries[:2]:  # Limit to first 2 queries
            try:
                url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    "key": self.api_key,
                    "cx": self.cse_id,
                    "q": query,
                    "num": min(max_results, 5),
                    "sort": "date",  # Prioritize recent results
                }

                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                for item in data.get("items", []):
                    results.append({
                        "title": item.get("title", ""),
                        "link": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "source": self._extract_domain(item.get("link", "")),
                        "date": item.get("pagemap", {}).get("metatags", [{}])[0].get("article:published_time", "Unknown"),
                    })

            except Exception as e:
                logger.error(f"Web search error for query '{query}': {e}")

        return results[:max_results]

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.replace("www.", "")
        except:
            return url

    def format_results_for_prompt(self, results: List[Dict]) -> str:
        """Format search results for LLM prompt."""
        if not results:
            return ""

        lines = ["=" * 70]
        lines.append("RECENT THREAT INTELLIGENCE (Web Search)")
        lines.append("=" * 70)

        for i, result in enumerate(results, 1):
            lines.append(f"\n{i}. {result['title']}")
            lines.append(f"   Source: {result['source']}")
            if result.get('date') and result['date'] != "Unknown":
                lines.append(f"   Date: {result['date']}")
            lines.append(f"   Summary: {result['snippet'][:200]}...")

        lines.append("=" * 70)
        return "\n".join(lines)


# Singleton instance
_search_client: Optional[WebSearchClient] = None


def get_web_search() -> WebSearchClient:
    """Get the singleton web search client."""
    global _search_client
    if _search_client is None:
        _search_client = WebSearchClient()
    return _search_client
