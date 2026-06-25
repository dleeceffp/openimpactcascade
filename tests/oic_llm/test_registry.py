"""Tests for provider registry and model matrix.

conftest.py adds src/ to sys.path so no sys.path manipulation is needed here.
"""

import pytest

from oic_llm.registry import get_provider, resolve_model, list_providers, list_models


def test_list_providers():
    providers = list_providers()
    assert "anthropic" in providers
    assert "openai" in providers
    assert "gemini" in providers


def test_list_models():
    models = list_models()
    assert ("anthropic", "light") in models
    assert ("openai", "heavy") in models
    assert ("gemini", "light") in models


def test_resolve_model_returns_string():
    """resolve_model returns a non-empty string for all valid combinations."""
    for provider in list_providers():
        for weight in ("light", "heavy"):
            model = resolve_model(provider, weight)
            assert isinstance(model, str) and model


def test_resolve_invalid_provider():
    with pytest.raises(ValueError, match="No model configured"):
        resolve_model("invalid", "light")


def test_get_invalid_provider():
    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider("invalid")
