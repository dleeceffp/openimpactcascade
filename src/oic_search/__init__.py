"""oic_search: shared pluggable search/grounding module for OIC applications.

Exports:
    search()                - simple single-call search interface (with caching)
    search_with_fallback()  - try primary provider, fall back on transient failures
    search_multi()          - fan-out across multiple OIC profiles, deduped
    get_provider()          - explicit provider instance (for advanced use)
    SearchConfig            - configuration dataclass
    SearchResult            - single normalized result
    SearchResponse          - response dataclass (results + provenance)
    SearchError             - normalized error type
"""

import logging
from typing import Any, List, Optional, Sequence

_fb_logger = logging.getLogger("oic_search.fallback")

from .base import SearchConfig, SearchError, SearchResponse, SearchResult
from .cache import get_cache
from .config import load_config
from .profiles import get_profile
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


def search_with_fallback(
    query: str,
    *,
    provider: Optional[str] = None,
    fallback_providers: Optional[Sequence[str]] = None,
    profile: Optional[str] = None,
    num: int = 10,
    force_refresh: bool = False,
    use_cache: bool = True,
    **opts: Any,
) -> SearchResponse:
    """Search with automatic provider fallback on transient failures.

    Tries the primary provider first.  If it fails with a transient error
    (quota, rate_limit, timeout, or unknown), the next provider in the
    fallback chain is tried in order.  The first successful response is
    returned.

    Permanent failures (auth, not_configured) are NOT retried — they indicate
    a misconfiguration that would fail on every provider in the chain anyway,
    and surfacing them immediately is more useful than silent degradation.

    The fallback chain is resolved as follows (highest priority first):
      1. ``fallback_providers`` argument (explicit override, e.g. from __init__)
      2. ``OIC_SEARCH_FALLBACK`` env var (comma-separated list, e.g. "brave,tavily")
      3. Empty — no fallback, behaves identically to ``search()``

    Caching applies per provider: a cache hit on the primary short-circuits
    the whole chain (no fallback needed).  Cache misses on the primary are
    stored under the fallback provider's key when a fallback succeeds.

    Args:
        query:              The search query string.
        provider:           Primary provider override (google_cse|brave|tavily|null).
        fallback_providers: Ordered list of fallback provider names.  When None,
                            resolved from OIC_SEARCH_FALLBACK env var.
        profile:            OIC source profile (default|framework|threatintel|incident|ics).
        num:                Max results to return (1-10).
        force_refresh:      Bypass cache.
        use_cache:          Set False to skip cache entirely.
        **opts:             Provider-specific pass-through options.

    Returns:
        SearchResponse from the first provider that succeeds.

    Raises:
        SearchError: If ALL providers in the chain fail (raises the last error).
    """
    # Transient error kinds that permit trying the next provider.
    _TRANSIENT = {"quota", "rate_limit", "timeout", "unknown"}

    config = load_config()
    effective_provider = provider or config.provider
    effective_profile = profile or config.profile

    # Resolve fallback chain
    if fallback_providers is not None:
        fb_chain = list(fallback_providers)
    else:
        fb_chain = list(config.fallback_providers)

    # Full ordered chain: primary first, then fallbacks (deduped, primary excluded)
    chain = [effective_provider] + [p for p in fb_chain if p != effective_provider]

    last_exc: Optional[SearchError] = None

    for attempt, prov_name in enumerate(chain):
        # Cache check (only when not force_refresh)
        cache = get_cache() if use_cache else None
        if cache and not force_refresh:
            cached = cache.get(prov_name, effective_profile, query, num)
            if cached is not None:
                if attempt > 0:
                    _fb_logger.debug(
                        "Cache hit on fallback provider '%s' for query: %s",
                        prov_name, query[:60],
                    )
                return cached

        try:
            p = get_provider(prov_name)
            response = p.search(query, profile=effective_profile, num=num, **opts)
            if cache:
                cache.put(prov_name, effective_profile, query, num, response)
            if attempt > 0:
                _fb_logger.info(
                    "Search succeeded on fallback provider '%s' after primary '%s' failed.",
                    prov_name, chain[0],
                )
            return response

        except SearchError as exc:
            last_exc = exc
            if exc.kind not in _TRANSIENT:
                # Permanent failure — do not try fallback, raise immediately.
                raise
            if attempt < len(chain) - 1:
                _fb_logger.warning(
                    "Provider '%s' failed with %s (%s); trying fallback '%s'.",
                    prov_name, exc.kind, exc, chain[attempt + 1],
                )
            else:
                _fb_logger.warning(
                    "All providers in chain %s failed. Last error: %s",
                    chain, exc,
                )

    # All providers exhausted
    if last_exc is not None:
        raise last_exc
    # Unreachable, but satisfies type checker
    raise SearchError("Empty provider chain", provider="none", kind="not_configured")


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
    # Validate all profile names upfront — before instantiating the provider or
    # touching the cache — so a typo fails immediately with a clear ValueError,
    # not mid-fan-out after already billing the first profile's network call.
    for _p in profiles:
        get_profile(_p)  # raises ValueError for unknown names

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
    "search_with_fallback",
    "search_multi",
    "get_provider",
    "list_providers",
    "SearchConfig",
    "SearchResult",
    "SearchResponse",
    "SearchError",
]
