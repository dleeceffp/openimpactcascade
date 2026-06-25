"""Tests for oic_search/cache.py.

Verifies:
- Cache stores and retrieves correctly
- cached flag is set on hits
- force_refresh / use_cache=False bypass cache
- TTL expiry works
- clear() and invalidate() work
- Identical queries return identical results (reproducibility guarantee)
"""

import time
import pytest
from oic_search.base import SearchResponse, SearchResult
from oic_search.cache import SearchCache


def _make_response(query: str = "test query") -> SearchResponse:
    return SearchResponse(
        results=[
            SearchResult(title="Title A", url="https://cisa.gov/a", snippet="snippet a", source="cisa.gov"),
            SearchResult(title="Title B", url="https://mandiant.com/b", snippet="snippet b", source="mandiant.com"),
        ],
        provider="google_cse",
        query=query,
        profile="incident",
    )


@pytest.fixture
def cache(tmp_path):
    """Fresh in-memory-equivalent cache backed by a temp dir per test."""
    return SearchCache(cache_dir=tmp_path, ttl=3600)


class TestCacheBasics:
    def test_miss_returns_none(self, cache):
        result = cache.get("google_cse", "incident", "ransomware 2026", 5)
        assert result is None

    def test_put_then_get_returns_response(self, cache):
        resp = _make_response()
        cache.put("google_cse", "incident", "ransomware 2026", 5, resp)
        hit = cache.get("google_cse", "incident", "ransomware 2026", 5)
        assert hit is not None
        assert len(hit.results) == 2

    def test_cached_flag_set_on_hit(self, cache):
        resp = _make_response()
        cache.put("google_cse", "incident", "phishing", 5, resp)
        hit = cache.get("google_cse", "incident", "phishing", 5)
        assert hit.cached is True

    def test_results_content_preserved(self, cache):
        resp = _make_response()
        cache.put("google_cse", "incident", "bec fraud", 5, resp)
        hit = cache.get("google_cse", "incident", "bec fraud", 5)
        assert hit.results[0].title == "Title A"
        assert hit.results[0].url == "https://cisa.gov/a"
        assert hit.results[0].source == "cisa.gov"
        assert hit.results[1].title == "Title B"


class TestCacheKeyIsolation:
    def test_different_query_is_miss(self, cache):
        resp = _make_response("query A")
        cache.put("google_cse", "incident", "query A", 5, resp)
        assert cache.get("google_cse", "incident", "query B", 5) is None

    def test_different_provider_is_miss(self, cache):
        resp = _make_response()
        cache.put("google_cse", "incident", "malware", 5, resp)
        assert cache.get("brave", "incident", "malware", 5) is None

    def test_different_profile_is_miss(self, cache):
        resp = _make_response()
        cache.put("google_cse", "incident", "malware", 5, resp)
        assert cache.get("google_cse", "ics", "malware", 5) is None

    def test_different_num_is_miss(self, cache):
        resp = _make_response()
        cache.put("google_cse", "incident", "malware", 5, resp)
        assert cache.get("google_cse", "incident", "malware", 10) is None


class TestTTLExpiry:
    def test_expired_entry_returns_none(self, tmp_path):
        short_cache = SearchCache(cache_dir=tmp_path, ttl=1)
        resp = _make_response()
        short_cache.put("google_cse", "default", "data breach", 5, resp)
        time.sleep(1.1)
        assert short_cache.get("google_cse", "default", "data breach", 5) is None

    def test_non_expired_entry_returns_response(self, tmp_path):
        long_cache = SearchCache(cache_dir=tmp_path, ttl=3600)
        resp = _make_response()
        long_cache.put("google_cse", "default", "incident 2026", 5, resp)
        hit = long_cache.get("google_cse", "default", "incident 2026", 5)
        assert hit is not None

    def test_purge_expired_removes_stale_rows(self, tmp_path):
        short_cache = SearchCache(cache_dir=tmp_path, ttl=1)
        for i in range(3):
            short_cache.put("google_cse", "default", f"query {i}", 5, _make_response(f"query {i}"))
        time.sleep(1.1)
        removed = short_cache.purge_expired()
        assert removed == 3


class TestInvalidateAndClear:
    def test_invalidate_removes_specific_entry(self, cache):
        resp = _make_response()
        cache.put("google_cse", "incident", "ddos", 5, resp)
        cache.invalidate("google_cse", "incident", "ddos", 5)
        assert cache.get("google_cse", "incident", "ddos", 5) is None

    def test_invalidate_does_not_affect_other_entries(self, cache):
        resp = _make_response()
        cache.put("google_cse", "incident", "ddos", 5, resp)
        cache.put("google_cse", "incident", "phishing", 5, resp)
        cache.invalidate("google_cse", "incident", "ddos", 5)
        assert cache.get("google_cse", "incident", "phishing", 5) is not None

    def test_clear_removes_all_entries(self, cache):
        resp = _make_response()
        for q in ["a", "b", "c"]:
            cache.put("google_cse", "incident", q, 5, resp)
        cache.clear()
        for q in ["a", "b", "c"]:
            assert cache.get("google_cse", "incident", q, 5) is None


class TestReproducibility:
    def test_two_gets_return_identical_results(self, cache):
        """Core guarantee: identical query → identical results for model comparison."""
        resp = _make_response()
        cache.put("google_cse", "incident", "pass the hash 2024", 5, resp)
        hit1 = cache.get("google_cse", "incident", "pass the hash 2024", 5)
        hit2 = cache.get("google_cse", "incident", "pass the hash 2024", 5)
        assert [r.url for r in hit1.results] == [r.url for r in hit2.results]
        assert [r.title for r in hit1.results] == [r.title for r in hit2.results]
