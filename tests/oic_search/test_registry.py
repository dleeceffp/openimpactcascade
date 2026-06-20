"""Tests for oic_search/registry.py.

Verifies:
- All expected providers are registered
- Unknown provider raises ValueError
- get_provider() returns correct type
- search_multi_profile() deduplicates by URL
- search_multi_profile() merges results across profiles
"""

import pytest
from unittest.mock import patch, MagicMock

from oic_search.base import SearchError, SearchResponse, SearchResult
from oic_search.registry import get_provider, list_providers, search_multi_profile
from oic_search.providers.null_provider import NullProvider


_EXPECTED_PROVIDERS = {"google_cse", "brave", "tavily", "null"}


class TestListProviders:
    def test_all_expected_providers_registered(self):
        assert _EXPECTED_PROVIDERS.issubset(set(list_providers()))

    def test_returns_list(self):
        assert isinstance(list_providers(), list)


class TestGetProvider:
    def test_null_provider_always_available(self):
        p = get_provider("null")
        assert isinstance(p, NullProvider)

    def test_unknown_provider_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown search provider"):
            get_provider("yahoo_search")

    def test_error_message_lists_available(self):
        with pytest.raises(ValueError, match="null"):
            get_provider("does_not_exist")

    def test_google_cse_raises_search_error_without_key(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_SEARCH_API_KEY", raising=False)
        with pytest.raises(SearchError) as exc_info:
            get_provider("google_cse")
        assert exc_info.value.kind == "auth"
        assert exc_info.value.provider == "google_cse"

    def test_brave_raises_search_error_without_key(self, monkeypatch):
        monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
        with pytest.raises(SearchError) as exc_info:
            get_provider("brave")
        assert exc_info.value.kind == "auth"
        assert exc_info.value.provider == "brave"

    def test_tavily_raises_search_error_without_key(self, monkeypatch):
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        with pytest.raises(SearchError) as exc_info:
            get_provider("tavily")
        assert exc_info.value.kind == "auth"
        assert exc_info.value.provider == "tavily"


def _make_resp(provider: str, profile: str, urls: list) -> SearchResponse:
    results = [
        SearchResult(title=f"Title {u}", url=u, snippet="", source=u.split("/")[2])
        for u in urls
    ]
    return SearchResponse(results=results, provider=provider, query="test", profile=profile)


class TestSearchMultiProfile:
    def test_merges_results_from_two_profiles(self):
        null_p = NullProvider()

        def mock_search(query, *, profile=None, num=10, **opts):
            if profile == "ics":
                return _make_resp("null", "ics", ["https://dragos.com/a", "https://nerc.com/b"])
            if profile == "incident":
                return _make_resp("null", "incident", ["https://cisa.gov/c", "https://verizon.com/d"])
            return _make_resp("null", profile, [])

        null_p.search = mock_search
        resp = search_multi_profile(null_p, "ransomware OT", ["ics", "incident"], num=10)
        urls = [r.url for r in resp.results]
        assert "https://dragos.com/a" in urls
        assert "https://cisa.gov/c" in urls
        # No truncation: both profiles contribute fully — all 4 unique results returned
        assert len(urls) == 4

    def test_no_truncation_both_profiles_contribute(self):
        """num results per profile should all appear — second profile must not be zeroed out."""
        null_p = NullProvider()

        def mock_search(query, *, profile=None, num=2, **opts):
            if profile == "ics":
                return _make_resp("null", "ics", ["https://dragos.com/1", "https://dragos.com/2"])
            if profile == "incident":
                return _make_resp("null", "incident", ["https://cisa.gov/1", "https://cisa.gov/2"])
            return _make_resp("null", profile, [])

        null_p.search = mock_search
        # With old truncation [:num=2], second profile would contribute 0 results
        resp = search_multi_profile(null_p, "query", ["ics", "incident"], num=2)
        urls = [r.url for r in resp.results]
        assert "https://cisa.gov/1" in urls, "second profile must contribute results (no [:num] truncation)"
        assert len(urls) == 4  # 2 from each profile, no duplicates

    def test_deduplicates_by_url(self):
        null_p = NullProvider()
        shared_url = "https://cisa.gov/shared"

        def mock_search(query, *, profile=None, num=10, **opts):
            return _make_resp("null", profile, [shared_url, f"https://example.com/{profile}"])

        null_p.search = mock_search
        resp = search_multi_profile(null_p, "query", ["ics", "incident"], num=10)
        urls = [r.url for r in resp.results]
        assert urls.count(shared_url) == 1

    def test_profile_label_is_joined(self):
        null_p = NullProvider()
        resp = search_multi_profile(null_p, "query", ["ics", "incident"], num=5)
        assert resp.profile == "ics+incident"

    def test_empty_profiles_raises(self):
        null_p = NullProvider()
        with pytest.raises((ValueError, Exception)):
            search_multi_profile(null_p, "query", [], num=5)

    def test_unknown_profile_raises_search_error(self):
        null_p = NullProvider()
        with pytest.raises((ValueError, SearchError)):
            search_multi_profile(null_p, "query", ["nonexistent"], num=5)

    def test_invalid_profile_validated_upfront_before_any_search(self):
        """A bad profile in position 1 must fail before the provider is called at all."""
        null_p = NullProvider()
        call_count = [0]

        def counting_search(query, *, profile=None, num=10, **opts):
            call_count[0] += 1
            return _make_resp("null", profile, ["https://dragos.com/a"])

        null_p.search = counting_search
        with pytest.raises((ValueError, SearchError)):
            search_multi_profile(null_p, "query", ["ics", "bad_profile_name"], num=5)
        assert call_count[0] == 0, "provider.search must not be called if any profile name is invalid"
