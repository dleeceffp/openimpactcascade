"""oic_search: shared pluggable search/grounding module for OIC applications.

Exports:
    search()            - simple single-call search interface (with caching)
    search_multi()      - fan-out across multiple OIC profiles, deduped
    get_provider()      - explicit provider instance (for advanced use)
    SearchConfig        - configuration dataclass
    SearchResult        - single normalized result
    SearchResponse      - response dataclass (results + provenance)
    SearchError         - normalized error type
"""

from typing import Any, List, Optional

from .base import SearchConfig, SearchError, SearchResponse, SearchResult
from .cache import get_cache
from .config import load_config
from .registry import get_provider, list_providers, search_multi_profile


def search(
    query: str,
    *,
    provider: Optional[str] = None,
    profile: Optional[str] = None,
    num: int = 10,
    force_refresh: bool = False,
    use_cache: bool = True,
    **opts: Any,
) -> SearchResponse:
    """Search for query using the configured provider and optional OIC profile.

    Results are cached by default (keyed on provider + profile + query + num).
    A cache hit sets SearchResponse.cached = True.

    Args:
        query:         The search query string.
        provider:      Override the configured provider (google_cse|brave|tavily|null).
        profile:       OIC source profile (default|framework|threatintel|incident|ics).
        num:           Max results to return (1–10).
        force_refresh: Bypass cache and execute a live query (result is then cached).
        use_cache:     Set False to skip cache entirely (live query, not stored).
        **opts:        Provider-specific pass-through options.

    Returns:
        SearchResponse with normalized results and provenance fields.

    Raises:
        SearchError: On any backend failure.
    """
    config = load_config()
    effective_provider = provider or config.provider
    effective_profile = profile or config.profile

    # Cache check
    cache = get_cache() if use_cache else None
    if cache and not force_refresh:
        cached = cache.get(effective_provider, effective_profile, query, num)
        if cached is not None:
            return cached

    # Live query
    p = get_provider(effective_provider)
    response = p.search(query, profile=effective_profile, num=num, **opts)

    # Store result
    if cache:
        cache.put(effective_provider, effective_profile, query, num, response)

    return response


def search_multi(
    query: str,
    profiles: List[str],
    *,
    provider: Optional[str] = None,
    num: int = 10,
    force_refresh: bool = False,
    use_cache: bool = True,
    **opts: Any,
) -> SearchResponse:
    """Search across multiple OIC profiles and return merged, deduplicated results.

    Recommended for ICS/OT queries: profiles=["ics", "incident"].

    Args:
        query:    The search query string.
        profiles: List of OIC profile names to search.
        provider: Override the configured provider.
        num:      Max results to return per profile (total may be up to num * len(profiles)).
        force_refresh: Bypass cache for all profiles.
        use_cache: Set False to skip cache entirely.
        **opts:   Provider-specific pass-through options.

    Returns:
        SearchResponse with merged results and profile="ics+incident" style label.
    """
    config = load_config()
    effective_provider = provider or config.provider
    combined_profile = "+".join(profiles)

    cache = get_cache() if use_cache else None
    if cache and not force_refresh:
        cached = cache.get(effective_provider, combined_profile, query, num)
        if cached is not None:
            return cached

    p = get_provider(effective_provider)
    response = search_multi_profile(p, query, profiles, num=num, **opts)

    if cache:
        cache.put(effective_provider, combined_profile, query, num, response)

    return response


__all__ = [
    "search",
    "search_multi",
    "get_provider",
    "list_providers",
    "SearchConfig",
    "SearchResult",
    "SearchResponse",
    "SearchError",
]
