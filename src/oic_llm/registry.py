"""Provider registry and model matrix for oic_llm."""

from typing import Dict, Tuple

from .base import LLMProvider, ProviderError
from .providers.anthropic_provider import AnthropicProvider
from .providers.openai_provider import OpenAIProvider
from .providers.gemini_provider import GeminiProvider


# The ONE place model strings live. Update here when vendors rev models.
# Last verified: 2026-06-20
#
# Temperature support:
#   anthropic light  (sonnet-4-6)      -- YES, temperature accepted
#   anthropic heavy  (opus-4-8)        -- NO,  adaptive thinking; temperature silently dropped
#   openai    light  (gpt-5.4-mini)    -- NO,  GPT-5 series; temperature silently dropped
#   openai    heavy  (gpt-5.5)         -- NO,  GPT-5 series; temperature silently dropped
#   gemini    light  (3.5-flash)       -- YES, temperature accepted
#   gemini    heavy  (3.1-pro-preview) -- YES, temperature accepted (preview model)
MODEL_MATRIX: Dict[Tuple[str, str], str] = {
    ("anthropic", "light"): "claude-sonnet-4-6",
    ("anthropic", "heavy"): "claude-opus-4-8",         # adaptive thinking; no temperature
    ("openai",    "light"): "gpt-5.4",             # GPT-5 series; no temperature
    ("openai",    "heavy"): "gpt-5.5",                  # GPT-5 series; no temperature
    ("gemini",    "light"): "gemini-3.5-flash",
    ("gemini",    "heavy"): "gemini-3.1-pro-preview",   # docs: ai.google.dev/gemini-api/docs/models/gemini-3.1-pro-preview
}


# Provider registry
_PROVIDERS: Dict[str, type[LLMProvider]] = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
}


def get_provider(name: str) -> LLMProvider:
    """Get a provider instance by name."""
    if name not in _PROVIDERS:
        raise ValueError(f"Unknown provider: {name}. Available: {list(_PROVIDERS.keys())}")
    return _PROVIDERS[name]()


def resolve_model(provider: str, weight: str) -> str:
    """Resolve provider+weight to a concrete model ID."""
    key = (provider, weight)
    if key not in MODEL_MATRIX:
        raise ValueError(f"No model configured for provider={provider}, weight={weight}")
    return MODEL_MATRIX[key]


def list_providers() -> list[str]:
    """List available provider names."""
    return list(_PROVIDERS.keys())


def list_models() -> Dict[Tuple[str, str], str]:
    """Get the full model matrix."""
    return MODEL_MATRIX.copy()