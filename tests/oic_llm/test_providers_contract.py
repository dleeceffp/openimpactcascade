"""Contract tests for all three providers.

Each test skips automatically when the relevant API key is absent.
These are marked `integration` so they can be excluded in fast CI:
  pytest -m "not integration"

conftest.py adds src/ to sys.path — no path manipulation needed here.
"""

import os
import pytest

from oic_llm.base import ProviderError
from oic_llm.registry import get_provider, list_providers, resolve_model

pytestmark = pytest.mark.integration

SYSTEM_PROMPT = "You are a helpful assistant."
TEST_MESSAGES = [{"role": "user", "content": "Say 'Hello world' in exactly those words."}]


def _has_credentials(provider_name: str) -> bool:
    if provider_name == "anthropic":
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    if provider_name == "openai":
        return bool(os.environ.get("OPENAI_API_KEY"))
    if provider_name == "gemini":
        return bool(
            os.environ.get("GEMINI_API_KEY") or
            os.environ.get("GOOGLE_API_KEY") or
            (os.environ.get("GOOGLE_CLOUD_PROJECT") and os.environ.get("GOOGLE_GENAI_USE_VERTEXAI"))
        )
    return False


@pytest.mark.parametrize("provider_name", list_providers())
def test_provider_instantiation(provider_name):
    """Each provider can be instantiated when credentials are present."""
    if not _has_credentials(provider_name):
        pytest.skip(f"No credentials for {provider_name}")
    provider = get_provider(provider_name)
    assert provider.name == provider_name


@pytest.mark.parametrize("provider_name", list_providers())
def test_provider_generate(provider_name):
    """Each provider returns a well-formed LLMResponse for a simple prompt."""
    if not _has_credentials(provider_name):
        pytest.skip(f"No credentials for {provider_name}")
    provider = get_provider(provider_name)
    model = resolve_model(provider_name, "light")
    response = provider.generate(
        system=SYSTEM_PROMPT,
        messages=TEST_MESSAGES,
        model=model,
        max_tokens=100,
    )
    assert response.text.strip()
    assert response.provider == provider_name
    assert response.model == model
    assert isinstance(response.usage, dict)
    assert "Hello world" in response.text


@pytest.mark.parametrize("provider_name", list_providers())
def test_provider_auth_error(provider_name):
    """Missing credentials raise a ProviderError(kind='auth')."""
    original_vars: dict = {}
    if provider_name == "anthropic":
        original_vars["ANTHROPIC_API_KEY"] = os.environ.pop("ANTHROPIC_API_KEY", None)
    elif provider_name == "openai":
        original_vars["OPENAI_API_KEY"] = os.environ.pop("OPENAI_API_KEY", None)
    elif provider_name == "gemini":
        for k in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_CLOUD_PROJECT"):
            original_vars[k] = os.environ.pop(k, None)
    try:
        with pytest.raises(ProviderError) as exc_info:
            get_provider(provider_name)
        assert exc_info.value.provider == provider_name
        assert exc_info.value.kind == "auth"
    finally:
        for key, value in original_vars.items():
            if value is not None:
                os.environ[key] = value


def test_error_normalization():
    """An invalid model name produces a normalised ProviderError."""
    if not _has_credentials("anthropic"):
        pytest.skip("No Anthropic credentials")
    provider = get_provider("anthropic")
    try:
        provider.generate(
            system=SYSTEM_PROMPT,
            messages=TEST_MESSAGES,
            model="invalid-model-name-12345",
            max_tokens=100,
        )
    except ProviderError as e:
        assert e.provider == "anthropic"
        assert e.kind in ("not_found", "unknown")
