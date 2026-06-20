"""Tests for oic_search/config.py.

Mirrors tests/oic_llm/test_config.py: env overrides default; unknown
provider/profile raises; per-call args override env.
"""

import os
import pytest

from oic_search.base import SearchConfig
from oic_search.config import load_config


class TestDefaults:
    def test_default_provider_is_google_cse(self, monkeypatch):
        monkeypatch.delenv("OIC_SEARCH_PROVIDER", raising=False)
        monkeypatch.delenv("OIC_SEARCH_PROFILE", raising=False)
        monkeypatch.delenv("OIC_SEARCH_CONFIG", raising=False)
        config = load_config()
        assert config.provider == "google_cse"

    def test_default_profile_is_default(self, monkeypatch):
        monkeypatch.delenv("OIC_SEARCH_PROVIDER", raising=False)
        monkeypatch.delenv("OIC_SEARCH_PROFILE", raising=False)
        monkeypatch.delenv("OIC_SEARCH_CONFIG", raising=False)
        config = load_config()
        assert config.profile == "default"


class TestEnvOverrides:
    def test_provider_env_overrides_default(self, monkeypatch):
        monkeypatch.setenv("OIC_SEARCH_PROVIDER", "null")
        monkeypatch.delenv("OIC_SEARCH_PROFILE", raising=False)
        config = load_config()
        assert config.provider == "null"

    def test_profile_env_overrides_default(self, monkeypatch):
        monkeypatch.delenv("OIC_SEARCH_PROVIDER", raising=False)
        monkeypatch.setenv("OIC_SEARCH_PROFILE", "incident")
        config = load_config()
        assert config.profile == "incident"

    def test_all_valid_providers_accepted(self, monkeypatch):
        for p in ("google_cse", "brave", "tavily", "null"):
            monkeypatch.setenv("OIC_SEARCH_PROVIDER", p)
            config = load_config()
            assert config.provider == p

    def test_all_named_profiles_accepted(self, monkeypatch):
        for profile in ("default", "framework", "threatintel", "incident", "ics"):
            monkeypatch.setenv("OIC_SEARCH_PROFILE", profile)
            config = load_config()
            assert config.profile == profile


class TestValidation:
    def test_invalid_provider_raises(self, monkeypatch):
        monkeypatch.setenv("OIC_SEARCH_PROVIDER", "yahoo")
        with pytest.raises(ValueError, match="Invalid search provider"):
            load_config()

    def test_invalid_profile_raises(self, monkeypatch):
        monkeypatch.delenv("OIC_SEARCH_PROVIDER", raising=False)
        monkeypatch.setenv("OIC_SEARCH_PROFILE", "top_secret_profile")
        with pytest.raises(ValueError, match="Invalid search profile"):
            load_config()

    def test_error_message_lists_valid_options(self, monkeypatch):
        monkeypatch.setenv("OIC_SEARCH_PROVIDER", "bad_provider")
        with pytest.raises(ValueError, match="google_cse"):
            load_config()


class TestSearchConfigDataclass:
    def test_defaults(self):
        c = SearchConfig()
        assert c.provider == "google_cse"
        assert c.profile == "default"

    def test_assignment(self):
        c = SearchConfig(provider="brave", profile="incident")
        assert c.provider == "brave"
        assert c.profile == "incident"
