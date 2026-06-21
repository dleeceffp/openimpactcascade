"""Brave Search API provider — independent, no engine setup required.

Brave Search returns clean snippets with consistent structure and is
independent of Google's infrastructure and deprecation cycles.

Credentials
-----------
  BRAVE_SEARCH_API_KEY  — from https://api-dashboard.search.brave.com/

API reference: https://api-dashboard.search.brave.com/api-reference/web/search/get

Site scoping
------------
Brave does not use pre-configured engine IDs.  Profile domains are applied as
site: operators appended to the query.  Works correctly for all OIC profiles
(all named profiles <= 10 domains; default profile has 22).

Key parameters (pass via **opts to search()):
  freshness   Recency filter — useful for knowledge cut-off queries:
                "pd"  — last 24 hours
                "pw"  — last 7 days
                "pm"  — last 31 days
                "py"  — last year
                "YYYY-MM-DDtoYYYY-MM-DD"  — custom range
  count       1–20 (default 20; oic_search clamps to 20)
"""

import os
from typing import Any, List, Optional
from urllib.parse import urlparse

import requests

from ..base import SearchError, SearchProvider, SearchResponse, SearchResult
from ..profiles import get_profile_domains


_BRAVE_API_URL = "https://api.search.brave.com/res/v1/web/search"
_MAX_RESULTS = 20  # Brave Web Search API limit per request


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.removeprefix("www.")
    except Exception:
        return url


def _build_site_query(query: str, sites: List[str]) -> str:
    """Restrict query to profile domains via site: operators."""
    if not sites:
        return query
    site_clause = " OR ".join(f"site:{s}" for s in sites)
    return f"({query}) ({site_clause})"


class BraveProvider(SearchProvider):
    """Brave Web Search API provider."""
    name = "brave"

    def __init__(self) -> None:
        self._api_key = os.environ.get("BRAVE_SEARCH_API_KEY")
        if not self._api_key:
            raise SearchError(
                "BRAVE_SEARCH_API_KEY not set",
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
        """Execute a Brave web search and return normalized results."""
        effective_profile = profile or "default"

        try:
            # get_profile_domains() strips path components (e.g. github.com/vz-risk/veris
            # → github.com) because Brave's site: operator accepts only bare domains.
            sites = get_profile_domains(effective_profile)
        except ValueError as e:
            raise SearchError(str(e), provider=self.name, kind="not_configured") from e

        scoped_query = _build_site_query(query, sites)

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self._api_key,
        }
        params: dict = {
            "q": scoped_query,
            "count": min(max(num, 1), _MAX_RESULTS),
            "text_decorations": "false",
            "search_lang": "en",
        }
        params.update(opts)

        try:
            resp = requests.get(
                _BRAVE_API_URL, headers=headers, params=params, timeout=15
            )
        except requests.exceptions.Timeout as e:
            raise SearchError(
                f"Brave Search request timed out for query: {query[:60]}",
                provider=self.name,
                kind="timeout",
                cause=e,
            ) from e
        except requests.exceptions.RequestException as e:
            raise SearchError(
                f"Brave Search network error: {e}",
                provider=self.name,
                kind="unknown",
                cause=e,
            ) from e

        self._raise_for_status(resp)

        data = resp.json()
        results = []
        for item in data.get("web", {}).get("results", []):
            url = item.get("url", "")
            results.append(SearchResult(
                title=item.get("title", ""),
                url=url,
                snippet=item.get("description", ""),
                source=_domain(url),
                published=item.get("page_age"),  # ISO date string when present
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
            err_msg = resp.json().get("message", resp.text)
        except Exception:
            err_msg = resp.text

        if resp.status_code == 401:
            raise SearchError(
                f"Brave Search authentication failed: {err_msg}",
                provider=self.name,
                kind="auth",
            )
        if resp.status_code == 422:
            raise SearchError(
                f"Brave Search subscription inactive or quota exceeded: {err_msg}",
                provider=self.name,
                kind="quota",
            )
        if resp.status_code == 429:
            raise SearchError(
                f"Brave Search rate limited: {err_msg}",
                provider=self.name,
                kind="rate_limit",
            )
        raise SearchError(
            f"Brave Search HTTP {resp.status_code}: {err_msg}",
            provider=self.name,
            kind="unknown",
        )
