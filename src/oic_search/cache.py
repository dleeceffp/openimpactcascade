"""SQLite-backed search result cache for oic_search.

Purpose
-------
1. Quota protection — repeated calls with the same query do not re-bill.
2. Reproducible comparisons — the test harness's "injected" mode feeds
   identical search evidence to all three models.  A cache keyed on
   (provider, profile, query, num) guarantees this; a live re-pull would
   give each model slightly different results and invalidate the comparison.

Cache location
--------------
Default: <OIC_SEARCH_CACHE_DIR or ~/.cache/oic/search> / oic_search_cache.db
Override: OIC_SEARCH_CACHE_DIR env var or pass cache_dir explicitly.

TTL
---
Default: 86400 seconds (24 h).  Override: OIC_SEARCH_CACHE_TTL env var (seconds).
"""

import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import List, Optional

from .base import SearchResponse, SearchResult


_DEFAULT_TTL = 86400  # 24 hours


def _default_cache_dir() -> Path:
    env = os.environ.get("OIC_SEARCH_CACHE_DIR")
    if env:
        return Path(env)
    return Path.home() / ".cache" / "oic" / "search"


def _cache_key(provider: str, profile: Optional[str], query: str, num: int) -> str:
    raw = json.dumps(
        {"provider": provider, "profile": profile or "", "query": query, "num": num},
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def _response_to_json(resp: SearchResponse) -> str:
    return json.dumps({
        "provider": resp.provider,
        "query": resp.query,
        "profile": resp.profile,
        "results": [
            {
                "title": r.title,
                "url": r.url,
                "snippet": r.snippet,
                "source": r.source,
                "published": r.published,
            }
            for r in resp.results
        ],
    })


def _response_from_json(data: str) -> SearchResponse:
    obj = json.loads(data)
    results = [
        SearchResult(
            title=r["title"],
            url=r["url"],
            snippet=r.get("snippet", ""),
            source=r.get("source", ""),
            published=r.get("published"),
        )
        for r in obj.get("results", [])
    ]
    return SearchResponse(
        results=results,
        provider=obj["provider"],
        query=obj.get("query", ""),
        profile=obj.get("profile"),
        cached=True,
    )


class SearchCache:
    """Simple SQLite cache with TTL and force_refresh support."""

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        ttl: Optional[int] = None,
    ):
        self._dir = cache_dir or _default_cache_dir()
        self._ttl = ttl if ttl is not None else int(
            os.environ.get("OIC_SEARCH_CACHE_TTL", _DEFAULT_TTL)
        )
        self._dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self._dir / "oic_search_cache.db"
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key       TEXT PRIMARY KEY,
                    value     TEXT NOT NULL,
                    stored_at REAL NOT NULL
                )
            """)

    def get(
        self,
        provider: str,
        profile: Optional[str],
        query: str,
        num: int,
    ) -> Optional[SearchResponse]:
        """Return a cached SearchResponse, or None on miss / expiry."""
        key = _cache_key(provider, profile, query, num)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value, stored_at FROM cache WHERE key = ?", (key,)
            ).fetchone()
        if row is None:
            return None
        age = time.time() - row["stored_at"]
        if age > self._ttl:
            return None
        return _response_from_json(row["value"])

    def put(
        self,
        provider: str,
        profile: Optional[str],
        query: str,
        num: int,
        response: SearchResponse,
    ) -> None:
        """Store a SearchResponse in the cache."""
        key = _cache_key(provider, profile, query, num)
        value = _response_to_json(response)
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache (key, value, stored_at) VALUES (?, ?, ?)",
                (key, value, time.time()),
            )

    def invalidate(
        self,
        provider: str,
        profile: Optional[str],
        query: str,
        num: int,
    ) -> None:
        """Remove a specific cache entry."""
        key = _cache_key(provider, profile, query, num)
        with self._connect() as conn:
            conn.execute("DELETE FROM cache WHERE key = ?", (key,))

    def clear(self) -> None:
        """Wipe the entire cache (useful in tests)."""
        with self._connect() as conn:
            conn.execute("DELETE FROM cache")

    def purge_expired(self) -> int:
        """Delete all expired entries. Returns number of rows removed."""
        cutoff = time.time() - self._ttl
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM cache WHERE stored_at < ?", (cutoff,))
            return cur.rowcount


# Module-level singleton — lazily created on first use.
_cache: Optional[SearchCache] = None


def get_cache() -> SearchCache:
    global _cache
    if _cache is None:
        _cache = SearchCache()
    return _cache
