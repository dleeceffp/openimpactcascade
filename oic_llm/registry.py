"""Provider registry and model matrix for oic_llm."""

from typing import Dict, Tuple

from .base import LLMProvider, ProviderError
from .providers.anthropic_provider import AnthropicProvider
from .providers.openai_provider import OpenAIProvider
from .providers.gemini_provider import GeminiProvider


# The ONE place model strings live. Update here when vendors rev models.
MODEL_MATRIX: Dict[Tuple[str, str], str] = {
    ("anthropic", "light"): "claude-3-5-sonnet-20241022",
    ("anthropic", "heavy"): "claude-3-5-sonnet-20241022",  # Same for now; could be Opus later
    ("openai", "light"): "gpt-4o-mini",
    ("openai", "heavy"): "gpt-4o",
    ("gemini", "light"): "gemini-1.5-flash",
    ("gemini", "heavy"): "gemini-1.5-pro",
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