"""Tavily Search API provider — purpose-built for LLM grounding.

Tavily returns clean, pre-extracted content rather than raw snippets, making
it particularly effective for injecting search evidence into LLM prompts.

Credentials
-----------
  TAVILY_API_KEY  — from https://tavily.com

API reference: https://docs.tavily.com/documentation/api-reference/endpoint/search

Site scoping
------------
Tavily supports an include_domains parameter that restricts results to a list
of domains — a clean match for OIC profiles.  No site: query operators needed.

Key parameters (pass via **opts to search()):
  search_depth  "basic" (default, 1 credit) | "advanced" (2 credits, higher relevance)
  time_range    "day" | "week" | "month" | "year"  — recency filter, useful for
                knowledge cut-off queries (e.g. "recent CISA advisories")
  max_results   1–20 (default 5; oic_search clamps to 20)
"""

import os
from typing import Any, List, Optional
from urllib.parse import urlparse

import requests

from ..base import SearchError, SearchProvider, SearchResponse, SearchResult
from ..profiles import get_profile_domains


_TAVILY_SEARCH_URL = "https://api.tavily.com/search"


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.removeprefix("www.")
    except Exception:
        return url


class TavilyProvider(SearchProvider):
    """Tavily Search API provider."""
    name = "tavily"

    def __init__(self) -> None:
        self._api_key = os.environ.get("TAVILY_API_KEY")
        if not self._api_key:
            raise SearchError(
                "TAVILY_API_KEY not set",
                provider=self.name,
                kind="auth",
            )

    def search(
        self,
        query: str,
        *,
        profile: Optional[str] = None,
        num: int = 10,
        **opts: Any,
    ) -> SearchResponse:
        """Execute a Tavily search and return normalized results."""
        effective_profile = profile or "default"

        try:
            # get_profile_domains() strips path components — Tavily's include_domains
            # accepts only bare domains, not path-scoped entries like github.com/vz-risk/veris.
            sites: List[str] = get_profile_domains(effective_profile)
        except ValueError as e:
            raise SearchError(str(e), provider=self.name, kind="not_configured") from e

        payload: dict = {
            "api_key": self._api_key,
            "query": query,
            "max_results": min(max(num, 1), 20),  # Tavily supports up to 20
            "search_depth": "basic",
            "include_domains": sites,
        }
        payload.update(opts)

        try:
            resp = requests.post(_TAVILY_SEARCH_URL, json=payload, timeout=20)
        except requests.exceptions.Timeout as e:
            raise SearchError(
                f"Tavily request timed out for query: {query[:60]}",
                provider=self.name,
                kind="timeout",
                cause=e,
            ) from e
        except requests.exceptions.RequestException as e:
            raise SearchError(
                f"Tavily network error: {e}",
                provider=self.name,
                kind="unknown",
                cause=e,
            ) from e

        self._raise_for_status(resp)

        data = resp.json()
        results = []
        for item in data.get("results", []):
            url = item.get("url", "")
            results.append(SearchResult(
                title=item.get("title", ""),
                url=url,
                snippet=item.get("content", ""),
                source=_domain(url),
                published=item.get("published_date"),
            ))

        return SearchResponse(
            results=results,
            provider=self.name,
            query=query,
            profile=effective_profile,
            raw=data,
        )

    def _raise_for_status(self, resp: requests.Response) -> None:
        if resp.status_code == 200:
            return
        try:
            err_msg = resp.json().get("detail", resp.text)
        except Exception:
            err_msg = resp.text

        if resp.status_code == 401:
            raise SearchError(
                f"Tavily authentication failed: {err_msg}",
                provider=self.name,
                kind="auth",
            )
        if resp.status_code == 429:
            raise SearchError(
                f"Tavily quota or rate limit exceeded: {err_msg}",
                provider=self.name,
                kind="quota",
            )
        raise SearchError(
            f"Tavily HTTP {resp.status_code}: {err_msg}",
            provider=self.name,
            kind="unknown",
        )
