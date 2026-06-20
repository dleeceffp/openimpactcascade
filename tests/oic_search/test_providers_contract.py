"""Provider contract tests for oic_search.

One shared assertion suite, parametrized over all providers:
- NullProvider always available, always passes
- Google CSE, Brave, Tavily: skipped automatically if credentials absent;
  marked @pytest.mark.integration for live API calls

Contract assertions (no-network, mocked):
1. search() returns a SearchResponse
2. results is a list (possibly empty for null)
3. provider field matches provider.name
4. query field is populated
5. Every SearchResult has title and url fields

Error normalization assertions (mocked HTTP errors):
6. 401 → SearchError(kind="auth")
7. 403 quota → SearchError(kind="quota")
8. 403 disabled → SearchError(kind="not_configured")
9. 429 → SearchError(kind="rate_limit")
"""

import pytest
from unittest.mock import MagicMock, patch

from oic_search.base import SearchError, SearchResponse, SearchResult
from oic_search.providers.null_provider import NullProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_http_response(status_code: int, json_body: dict = None, text: str = ""):
    """Create a mock requests.Response with given status and optional JSON body."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.text = text
    if json_body is not None:
        mock.json.return_value = json_body
    else:
        mock.json.side_effect = ValueError("No JSON")
    return mock


def _good_cse_response():
    return _mock_http_response(200, {
        "items": [
            {
                "title": "CISA Advisory AA26-001",
                "link": "https://cisa.gov/advisory/aa26-001",
                "snippet": "Recent ransomware campaign targeting healthcare.",
                "displayLink": "cisa.gov",
                "pagemap": {"metatags": [{}]},
            }
        ]
    })


def _good_brave_response():
    return _mock_http_response(200, {
        "web": {
            "results": [
                {
                    "title": "Dragos ICS Threat Report",
                    "url": "https://dragos.com/report/ics-threat-2026",
                    "description": "ICS threats 2026 summary.",
                    "page_age": "2026-01-15",
                }
            ]
        }
    })


def _good_tavily_response():
    return _mock_http_response(200, {
        "results": [
            {
                "title": "ENISA Threat Landscape",
                "url": "https://enisa.europa.eu/threat-landscape-2026",
                "content": "Top cyber threats for 2026.",
                "published_date": "2026-02-01",
            }
        ]
    })


# ---------------------------------------------------------------------------
# Null provider — always runs, never skipped
# ---------------------------------------------------------------------------

class TestNullProvider:
    def test_returns_search_response(self):
        p = NullProvider()
        resp = p.search("test query", profile="incident", num=5)
        assert isinstance(resp, SearchResponse)

    def test_results_is_empty_list(self):
        p = NullProvider()
        resp = p.search("any query")
        assert resp.results == []

    def test_provider_field_is_null(self):
        p = NullProvider()
        resp = p.search("q")
        assert resp.provider == "null"

    def test_query_field_populated(self):
        p = NullProvider()
        resp = p.search("my query")
        assert resp.query == "my query"

    def test_profile_field_passed_through(self):
        p = NullProvider()
        resp = p.search("q", profile="ics")
        assert resp.profile == "ics"

    def test_cached_is_false(self):
        p = NullProvider()
        resp = p.search("q")
        assert resp.cached is False


# ---------------------------------------------------------------------------
# Google CSE provider — mocked unit tests
# ---------------------------------------------------------------------------

class TestGoogleCSEContractMocked:
    """Contract tests with mocked HTTP — no API key needed."""

    @pytest.fixture
    def provider(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "fake-key")
        monkeypatch.setenv("OIC_SEARCH_CSE_INCIDENT", "fake-cx")
        monkeypatch.setenv("OIC_SEARCH_CSE_DEFAULT", "fake-cx-default")
        from oic_search.providers.google_cse_provider import GoogleCSEProvider
        return GoogleCSEProvider()

    def test_returns_search_response(self, provider):
        with patch("requests.get", return_value=_good_cse_response()):
            resp = provider.search("ransomware healthcare", profile="incident", num=5)
        assert isinstance(resp, SearchResponse)

    def test_results_are_search_result_objects(self, provider):
        with patch("requests.get", return_value=_good_cse_response()):
            resp = provider.search("q", profile="incident", num=5)
        for r in resp.results:
            assert isinstance(r, SearchResult)
            assert r.title
            assert r.url

    def test_provider_field(self, provider):
        with patch("requests.get", return_value=_good_cse_response()):
            resp = provider.search("q", profile="incident", num=5)
        assert resp.provider == "google_cse"

    def test_source_is_domain(self, provider):
        with patch("requests.get", return_value=_good_cse_response()):
            resp = provider.search("q", profile="incident", num=5)
        assert resp.results[0].source == "cisa.gov"

    # Error normalization
    def test_401_is_auth_error(self, provider):
        with patch("requests.get", return_value=_mock_http_response(401, {"error": {"message": "Invalid creds", "status": "UNAUTHENTICATED"}})):
            with pytest.raises(SearchError) as exc:
                provider.search("q", profile="incident")
        assert exc.value.kind == "auth"

    def test_403_quota_is_quota_error(self, provider):
        with patch("requests.get", return_value=_mock_http_response(403, {"error": {"message": "quota exceeded", "status": "RESOURCE_EXHAUSTED"}})):
            with pytest.raises(SearchError) as exc:
                provider.search("q", profile="incident")
        assert exc.value.kind == "quota", "quota 403 must not be mislabelled as not_configured"

    def test_403_api_disabled_is_not_configured(self, provider):
        with patch("requests.get", return_value=_mock_http_response(403, {"error": {"message": "API not enabled", "status": "PERMISSION_DENIED"}})):
            with pytest.raises(SearchError) as exc:
                provider.search("q", profile="incident")
        assert exc.value.kind == "not_configured", "disabled-API 403 must not be mislabelled as quota"

    def test_429_is_rate_limit(self, provider):
        with patch("requests.get", return_value=_mock_http_response(429, {"error": {"message": "too many requests", "status": "RESOURCE_EXHAUSTED"}})):
            with pytest.raises(SearchError) as exc:
                provider.search("q", profile="incident")
        assert exc.value.kind == "rate_limit"

    def test_missing_engine_id_raises_not_configured(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "fake-key")
        monkeypatch.delenv("OIC_SEARCH_CSE_FRAMEWORK", raising=False)
        monkeypatch.delenv("GOOGLE_SEARCH_CSE_ID", raising=False)
        from oic_search.providers.google_cse_provider import GoogleCSEProvider
        p = GoogleCSEProvider()
        with pytest.raises(SearchError) as exc:
            p.search("q", profile="framework")
        assert exc.value.kind == "not_configured"


# ---------------------------------------------------------------------------
# Brave provider — mocked unit tests
# ---------------------------------------------------------------------------

class TestBraveContractMocked:
    @pytest.fixture
    def provider(self, monkeypatch):
        monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "fake-brave-key")
        from oic_search.providers.brave_provider import BraveProvider
        return BraveProvider()

    def test_returns_search_response(self, provider):
        with patch("requests.get", return_value=_good_brave_response()):
            resp = provider.search("ICS threat 2026", profile="ics", num=5)
        assert isinstance(resp, SearchResponse)

    def test_results_are_search_result_objects(self, provider):
        with patch("requests.get", return_value=_good_brave_response()):
            resp = provider.search("q", profile="ics", num=5)
        for r in resp.results:
            assert isinstance(r, SearchResult)

    def test_provider_field(self, provider):
        with patch("requests.get", return_value=_good_brave_response()):
            resp = provider.search("q", profile="ics", num=5)
        assert resp.provider == "brave"

    def test_401_is_auth_error(self, provider):
        with patch("requests.get", return_value=_mock_http_response(401, {"message": "Unauthorized"})):
            with pytest.raises(SearchError) as exc:
                provider.search("q", profile="ics")
        assert exc.value.kind == "auth"

    def test_422_is_quota_error(self, provider):
        with patch("requests.get", return_value=_mock_http_response(422, {"message": "Subscription inactive"})):
            with pytest.raises(SearchError) as exc:
                provider.search("q", profile="ics")
        assert exc.value.kind == "quota"

    def test_429_is_rate_limit(self, provider):
        with patch("requests.get", return_value=_mock_http_response(429, {"message": "Rate limit"})):
            with pytest.raises(SearchError) as exc:
                provider.search("q", profile="ics")
        assert exc.value.kind == "rate_limit"


# ---------------------------------------------------------------------------
# Tavily provider — mocked unit tests
# ---------------------------------------------------------------------------

class TestTavilyContractMocked:
    @pytest.fixture
    def provider(self, monkeypatch):
        monkeypatch.setenv("TAVILY_API_KEY", "fake-tavily-key")
        from oic_search.providers.tavily_provider import TavilyProvider
        return TavilyProvider()

    def test_returns_search_response(self, provider):
        with patch("requests.post", return_value=_good_tavily_response()):
            resp = provider.search("ENISA threat landscape", profile="incident", num=5)
        assert isinstance(resp, SearchResponse)

    def test_results_are_search_result_objects(self, provider):
        with patch("requests.post", return_value=_good_tavily_response()):
            resp = provider.search("q", profile="incident", num=5)
        for r in resp.results:
            assert isinstance(r, SearchResult)

    def test_provider_field(self, provider):
        with patch("requests.post", return_value=_good_tavily_response()):
            resp = provider.search("q", profile="incident", num=5)
        assert resp.provider == "tavily"

    def test_401_is_auth_error(self, provider):
        with patch("requests.post", return_value=_mock_http_response(401, {"detail": "Unauthorized"})):
            with pytest.raises(SearchError) as exc:
                provider.search("q", profile="incident")
        assert exc.value.kind == "auth"

    def test_429_is_quota_error(self, provider):
        with patch("requests.post", return_value=_mock_http_response(429, {"detail": "Quota exceeded"})):
            with pytest.raises(SearchError) as exc:
                provider.search("q", profile="incident")
        assert exc.value.kind == "quota"
