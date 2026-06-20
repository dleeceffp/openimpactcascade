"""Base interfaces and data structures for oic_search."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SearchResult:
    """A single normalized search result, provider-agnostic."""
    title: str
    url: str
    snippet: str = ""
    source: str = ""               # domain, e.g. "cisa.gov" — for provenance/weighting
    published: Optional[str] = None  # ISO-8601 date string when the backend provides it


@dataclass
class SearchResponse:
    """Normalized response from any search provider."""
    results: List[SearchResult]
    provider: str                  # "google_cse" | "brave" | "tavily" | "null"
    query: str = ""
    profile: Optional[str] = None  # which OIC source profile was used, if any
    cached: bool = False           # True when this response was served from cache
    raw: Any = None                # underlying HTTP response / SDK object, for debugging


class SearchError(Exception):
    """Normalized error across search backends.

    Wraps backend-specific exceptions with a consistent interface.
    kind values:
        "auth"           — API key missing, invalid, or not authorised
        "quota"          — daily query limit or billing quota exceeded
        "not_configured" — engine/resource not set up (e.g. API not enabled in GCP,
                           CSE ID missing, or a 403 that is NOT quota)
        "rate_limit"     — per-second / per-minute throttle (retry after)
        "not_found"      — engine ID or endpoint not found (404)
        "unknown"        — anything else
    """
    def __init__(
        self,
        message: str,
        *,
        provider: str,
        kind: str = "unknown",
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.kind = kind
        self.cause = cause


@dataclass
class SearchConfig:
    """Configuration loaded from environment and optional config file."""
    provider: str = "google_cse"
    profile: str = "default"


class SearchProvider(ABC):
    """Abstract base class for search providers."""
    name: str

    @abstractmethod
    def search(
        self,
        query: str,
        *,
        profile: Optional[str] = None,
        num: int = 10,
        **opts: Any,
    ) -> SearchResponse:
        """Execute a search query and return normalized results.

        Args:
            query:   The search query string.
            profile: OIC source profile name (e.g. "incident", "framework").
                     If None the provider uses the configured default.
            num:     Maximum number of results to return (1–10).
            **opts:  Provider-specific pass-through options.

        Returns:
            SearchResponse with normalized SearchResult list.

        Raises:
            SearchError: On any backend failure, with normalized kind.
        """
        ...
