"""Contract tests for all providers.

These tests verify that each provider implements the expected interface
and can make successful calls when credentials are present.
"""

import os
import pytest

from ..base import ProviderError
from ..registry import get_provider, list_providers


# Test data
SYSTEM_PROMPT = "You are a helpful assistant."
TEST_MESSAGES = [
    {"role": "user", "content": "Say 'Hello world' in exactly those words."}
]


def _has_credentials(provider_name: str) -> bool:
    """Check if credentials are available for a provider."""
    if provider_name == "anthropic":
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    elif provider_name == "openai":
        return bool(os.environ.get("OPENAI_API_KEY"))
    elif provider_name == "gemini":
        return bool(
            os.environ.get("GEMINI_API_KEY") or
            os.environ.get("GOOGLE_API_KEY") or
            (os.environ.get("GOOGLE_CLOUD_PROJECT") and
             os.environ.get("GOOGLE_GENAI_USE_VERTEXAI"))
        )
    return False


@pytest.mark.parametrize("provider_name", list_providers())
def test_provider_instantiation(provider_name):
    """Test that each provider can be instantiated."""
    if not _has_credentials(provider_name):
        pytest.skip(f"No credentials for {provider_name}")
    
    provider = get_provider(provider_name)
    assert provider.name == provider_name


@pytest.mark.parametrize("provider_name", list_providers())
def test_provider_generate(provider_name):
    """Test that each provider can generate a response."""
    if not _has_credentials(provider_name):
        pytest.skip(f"No credentials for {provider_name}")
    
    provider = get_provider(provider_name)
    
    # Get a model for this provider
    from ..registry import resolve_model
    model = resolve_model(provider_name, "light")
    
    response = provider.generate(
        system=SYSTEM_PROMPT,
        messages=TEST_MESSAGES,
        model=model,
        max_tokens=100,
    )
    
    # Check response structure
    assert response.text.strip()
    assert response.provider == provider_name
    assert response.model == model
    assert isinstance(response.usage, dict)
    
    # Check content
    assert "Hello world" in response.text


@pytest.mark.parametrize("provider_name", list_providers())
def test_provider_auth_error(provider_name):
    """Test that missing credentials raise auth errors."""
    # Temporarily clear credentials
    original_vars = {}
    if provider_name == "anthropic":
        original_vars["ANTHROPIC_API_KEY"] = os.environ.pop("ANTHROPIC_API_KEY", None)
    elif provider_name == "openai":
        original_vars["OPENAI_API_KEY"] = os.environ.pop("OPENAI_API_KEY", None)
    elif provider_name == "gemini":
        original_vars["GEMINI_API_KEY"] = os.environ.pop("GEMINI_API_KEY", None)
        original_vars["GOOGLE_API_KEY"] = os.environ.pop("GOOGLE_API_KEY", None)
        original_vars["GOOGLE_CLOUD_PROJECT"] = os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
    
    try:
        with pytest.raises(ProviderError) as exc_info:
            get_provider(provider_name)
        
        assert exc_info.value.provider == provider_name
        assert exc_info.value.kind == "auth"
    finally:
        # Restore credentials
        for key, value in original_vars.items():
            if value is not None:
                os.environ[key] = value


def test_error_normalization():
    """Test that provider errors are properly normalized."""
    # This test uses Anthropic as an example
    if not _has_credentials("anthropic"):
        pytest.skip("No Anthropic credentials")
    
    provider = get_provider("anthropic")
    
    # Try with an invalid model to trigger a not_found error
    from ..registry import resolve_model
    model = resolve_model("anthropic", "light")
    
    # We'll mock this by passing an obviously invalid model name
    try:
        provider.generate(
            system=SYSTEM_PROMPT,
            messages=TEST_MESSAGES,
            model="invalid-model-name-12345",
            max_tokens=100,
        )
    except ProviderError as e:
        # Should be normalized to ProviderError
        assert e.provider == "anthropic"
        # Might be "not_found" or "unknown" depending on the error
        assert e.kind in ("not_found", "unknown")