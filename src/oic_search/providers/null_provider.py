"""Null search provider — always returns empty results.

Used for:
- "search disabled" mode (set OIC_SEARCH_PROVIDER=null)
- Offline / no-network unit tests
- As a baseline in provider contract tests

Requires no credentials and never raises SearchError.
"""

from typing import Any, Optional

from ..base import SearchProvider, SearchResponse, SearchResult


class NullProvider(SearchProvider):
    """Returns an empty SearchResponse for every query. Never errors."""
    name = "null"

    def search(
        self,
        query: str,
        *,
        profile: Optional[str] = None,
        num: int = 10,
        **opts: Any,
    ) -> SearchResponse:
        return SearchResponse(
            results=[],
            provider=self.name,
            query=query,
            profile=profile,
            cached=False,
        )
