"""Google Programmable Search Engine (Custom Search) provider.

Two endpoint modes — auto-selected per profile:

  Site-Restricted  (customsearch/v1/siterestrict)
      Used when a profile has <= 10 domains and no bare TLD patterns.
      Google documents this endpoint as having NO daily query limit.
      NOTE: Google is steering users toward Vertex AI Search; verify the
      Site-Restricted no-limit perk is still active if you see unexpected
      quota errors.  Fallback: switch the profile to standard mode by adding
      a comment in SITE_RESTRICTED_ELIGIBLE in profiles.py.

  Standard  (customsearch/v1)
      Used for the "default" profile (22 domains) and any future large profiles.
      Quota: 100 queries/day free; 10,000/day paid (per GCP project).

Credentials
-----------
  GOOGLE_SEARCH_API_KEY  — the API key; must have Custom Search API enabled in
                           the GCP project.  A 403 from a disabled API surfaces
                           as SearchError(kind="not_configured"), NOT quota.
  OIC_SEARCH_CSE_<PROFILE_UPPER>  — one engine ID per profile, e.g.:
      OIC_SEARCH_CSE_DEFAULT
      OIC_SEARCH_CSE_INCIDENT
      OIC_SEARCH_CSE_ICS
      OIC_SEARCH_CSE_FRAMEWORK
      OIC_SEARCH_CSE_THREATINTEL

If the per-profile engine ID is missing but GOOGLE_SEARCH_CSE_ID is set, that
value is used as a fallback (backward-compatible with the legacy single-engine
setup in tools/attack_flow_workbench/web_search.py).
"""

import os
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests

from ..base import SearchError, SearchProvider, SearchResponse, SearchResult
from ..profiles import SITE_RESTRICTED_ELIGIBLE, get_profile


_STANDARD_URL = "https://www.googleapis.com/customsearch/v1"
_SITE_RESTRICTED_URL = "https://www.googleapis.com/customsearch/v1/siterestrict"


def _engine_id_for_profile(profile: str) -> Optional[str]:
    """Read OIC_SEARCH_CSE_<PROFILE> from env, with fallback to GOOGLE_SEARCH_CSE_ID."""
    specific = os.environ.get(f"OIC_SEARCH_CSE_{profile.upper()}")
    if specific:
        return specific
    # Backward-compat fallback: the old single-engine variable
    return os.environ.get("GOOGLE_SEARCH_CSE_ID")


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.removeprefix("www.")
    except Exception:
        return url


class GoogleCSEProvider(SearchProvider):
    """Google Programmable Search Engine provider."""
    name = "google_cse"

    def __init__(self) -> None:
        self._api_key = os.environ.get("GOOGLE_SEARCH_API_KEY")
        if not self._api_key:
            raise SearchError(
                "GOOGLE_SEARCH_API_KEY not set",
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
        """Execute a search and return normalized results."""
        effective_profile = profile or "default"

        try:
            get_profile(effective_profile)  # validates; raises ValueError if unknown
        except ValueError as e:
            raise SearchError(str(e), provider=self.name, kind="not_configured") from e

        engine_id = _engine_id_for_profile(effective_profile)
        if not engine_id:
            raise SearchError(
                f"No CSE engine ID configured for profile '{effective_profile}'. "
                f"Set OIC_SEARCH_CSE_{effective_profile.upper()} (or GOOGLE_SEARCH_CSE_ID as fallback).",
                provider=self.name,
                kind="not_configured",
            )

        site_restricted = SITE_RESTRICTED_ELIGIBLE.get(effective_profile, False)
        endpoint = _SITE_RESTRICTED_URL if site_restricted else _STANDARD_URL

        # For the Site-Restricted endpoint the engine itself enforces the site list —
        # no site: operators needed in the query.
        # For the Standard endpoint (i.e. "default" with 22 sites) the engine is
        # pre-configured with the site list; do not append site: operators here because:
        #   (a) 22-site clauses would push the query over URL length limits, and
        #   (b) any <=10-domain profile is already site-restricted, so this branch
        #       is only ever reached by the "default" 22-site profile anyway.
        effective_query = query

        params: Dict[str, Any] = {
            "key": self._api_key,
            "cx": engine_id,
            "q": effective_query,
            "num": min(max(num, 1), 10),  # API hard max is 10
        }

        # Pass any caller overrides (e.g. dateRestrict, sort)
        params.update(opts)

        try:
            resp = requests.get(endpoint, params=params, timeout=15)
        except requests.exceptions.Timeout as e:
            raise SearchError(
                f"Google CSE request timed out for query: {query[:60]}",
                provider=self.name,
                kind="timeout",
                cause=e,
            ) from e
        except requests.exceptions.RequestException as e:
            raise SearchError(
                f"Google CSE network error: {e}",
                provider=self.name,
                kind="unknown",
                cause=e,
            ) from e

        self._raise_for_status(resp, effective_profile)

        data = resp.json()
        results = []
        for item in data.get("items", []):
            url = item.get("link", "")
            # Published date: try pagemap metatags first, then snippet date
            published = None
            metatags = item.get("pagemap", {}).get("metatags", [{}])
            if metatags:
                published = (
                    metatags[0].get("article:published_time")
                    or metatags[0].get("og:article:published_time")
                    or metatags[0].get("date")
                )
            results.append(SearchResult(
                title=item.get("title", ""),
                url=url,
                snippet=item.get("snippet", ""),
                source=_domain(url),
                published=published,
            ))

        return SearchResponse(
            results=results,
            provider=self.name,
            query=query,
            profile=effective_profile,
            raw=data,
        )

    def _raise_for_status(self, resp: requests.Response, profile: str) -> None:
        """Map HTTP errors to typed SearchError — do not string-match into wrong bucket."""
        if resp.status_code == 200:
            return

        # Try to parse the Google error body for a more specific message
        try:
            err_body = resp.json()
            err_msg = err_body.get("error", {}).get("message", resp.text)
            err_status = err_body.get("error", {}).get("status", "")
        except Exception:
            err_msg = resp.text
            err_status = ""

        if resp.status_code == 401:
            raise SearchError(
                f"Google CSE authentication failed: {err_msg}",
                provider=self.name,
                kind="auth",
            )
        if resp.status_code == 403:
            # 403 can be quota exceeded OR API not enabled — distinguish them.
            if "quota" in err_msg.lower() or "rateLimitExceeded" in err_status:
                raise SearchError(
                    f"Google CSE quota exceeded: {err_msg}",
                    provider=self.name,
                    kind="quota",
                )
            # API not enabled on this GCP project, or CSE ID misconfigured
            raise SearchError(
                f"Google CSE not configured (API disabled or engine '{profile}' invalid): {err_msg}",
                provider=self.name,
                kind="not_configured",
            )
        if resp.status_code == 429:
            raise SearchError(
                f"Google CSE rate limited: {err_msg}",
                provider=self.name,
                kind="rate_limit",
            )
        if resp.status_code == 404:
            raise SearchError(
                f"Google CSE endpoint or engine not found: {err_msg}",
                provider=self.name,
                kind="not_found",
            )
        raise SearchError(
            f"Google CSE HTTP {resp.status_code}: {err_msg}",
            provider=self.name,
            kind="unknown",
        )
