"""Tests for provider registry and model matrix."""

import pytest

from ..registry import get_provider, resolve_model, list_providers, list_models


def test_list_providers():
    """Test listing available providers."""
    providers = list_providers()
    assert "anthropic" in providers
    assert "openai" in providers
    assert "gemini" in providers


def test_list_models():
    """Test listing model matrix."""
    models = list_models()
    assert ("anthropic", "light") in models
    assert ("openai", "heavy") in models
    assert ("gemini", "light") in models


def test_resolve_model():
    """Test model resolution."""
    model = resolve_model("anthropic", "light")
    assert model == "claude-3-5-sonnet-20241022"
    
    model = resolve_model("openai", "heavy")
    assert model == "gpt-4o"


def test_resolve_invalid():
    """Test resolving invalid provider/weight."""
    with pytest.raises(ValueError, match="No model configured"):
        resolve_model("invalid", "light")


def test_get_provider():
    """Test getting provider instances."""
    provider = get_provider("anthropic")
    assert provider.name == "anthropic"
    
    provider = get_provider("openai")
    assert provider.name == "openai"
    
    provider = get_provider("gemini")
    assert provider.name == "gemini"


def test_get_invalid_provider():
    """Test getting invalid provider."""
    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider("invalid")