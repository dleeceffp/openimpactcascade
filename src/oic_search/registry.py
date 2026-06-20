"""Provider registry for oic_search.

Mirrors oic_llm/registry.py: a single place that maps names to classes.
Apps never instantiate provider classes directly.
"""

from typing import Dict, List, Optional, Type

from .base import SearchError, SearchProvider, SearchResponse
from .profiles import PROFILES, get_profile


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

def _load_providers() -> Dict[str, Type[SearchProvider]]:
    """Import provider classes lazily so missing SDKs only error when used."""
    from .providers.null_provider import NullProvider
    from .providers.google_cse_provider import GoogleCSEProvider
    from .providers.brave_provider import BraveProvider
    from .providers.tavily_provider import TavilyProvider

    return {
        "google_cse": GoogleCSEProvider,
        "brave": BraveProvider,
        "tavily": TavilyProvider,
        "null": NullProvider,
    }


_PROVIDERS: Optional[Dict[str, Type[SearchProvider]]] = None


def _get_providers() -> Dict[str, Type[SearchProvider]]:
    global _PROVIDERS
    if _PROVIDERS is None:
        _PROVIDERS = _load_providers()
    return _PROVIDERS


def get_provider(name: str) -> SearchProvider:
    """Instantiate and return a provider by name.

    Raises:
        ValueError:  Unknown provider name.
        SearchError: Provider-specific init failure (e.g. missing API key).
    """
    providers = _get_providers()
    if name not in providers:
        raise ValueError(
            f"Unknown search provider: '{name}'. "
            f"Available: {list(providers.keys())}"
        )
    return providers[name]()


def list_providers() -> List[str]:
    """Return all registered provider names."""
    return list(_get_providers().keys())


# ---------------------------------------------------------------------------
# Multi-profile fan-out helper
# ---------------------------------------------------------------------------

def search_multi_profile(
    provider: SearchProvider,
    query: str,
    profiles: List[str],
    num: int = 10,
    **opts,
) -> SearchResponse:
    """Search across multiple profiles and return a merged, deduplicated response.

    Results are ordered: first profile's results first, then unique results from
    subsequent profiles.  Deduplication is by URL (case-insensitive).

    Used for ICS/OT queries where both "ics" + "incident" profiles are needed.

    Example:
        provider = get_provider("google_cse")
        resp = search_multi_profile(provider, "ransomware OT 2026", ["ics", "incident"])
    """
    if not profiles:
        raise ValueError("profiles list must not be empty")

    merged: List = []
    seen_urls: set = set()
    last_response: Optional[SearchResponse] = None

    for profile_name in profiles:
        # Validate profile early — cleaner error than a provider-level failure
        get_profile(profile_name)

        try:
            resp = provider.search(query, profile=profile_name, num=num, **opts)
        except SearchError:
            raise

        last_response = resp
        for result in resp.results:
            key = result.url.lower().rstrip("/")
            if key not in seen_urls:
                seen_urls.add(key)
                merged.append(result)

    # Return a SearchResponse that reflects all profiles searched
    return SearchResponse(
        results=merged[:num],
        provider=provider.name,
        query=query,
        profile="+".join(profiles),
        cached=last_response.cached if last_response else False,
        raw=None,  # multi-profile has no single raw response
    )
