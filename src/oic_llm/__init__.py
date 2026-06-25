"""oic_llm: shared multi-provider LLM module for OIC applications.

Exports:
    complete()          - simple completion interface
    get_provider()      - explicit provider instance
    LLMConfig           - configuration dataclass
    LLMResponse         - response dataclass
    ProviderError       - normalized error type
"""

from .base import LLMConfig, LLMResponse, ProviderError
from .config import load_config
from .registry import get_provider, resolve_model
from typing import Optional, List, Dict, Any


def complete(
    *,
    system: str,
    messages: List[Dict[str, str]],
    provider: Optional[str] = None,
    weight: Optional[str] = None,
    max_tokens: int = 4096,
    temperature: Optional[float] = None,
) -> LLMResponse:
    """Generate a completion using the configured provider.

    Args:
        system: System prompt
        messages: List of {"role": "user"|"assistant", "content": str}
        provider: Override provider (anthropic|openai|gemini)
        weight: Override weight (light|heavy)
        max_tokens: Max tokens in response
        temperature: Sampling temperature

    Returns:
        LLMResponse with text, provider, model, and usage info
    """
    config = load_config()
    if provider:
        config.provider = provider
    if weight:
        config.weight = weight

    provider_instance = get_provider(config.provider)
    model = resolve_model(config.provider, config.weight)
    
    return provider_instance.generate(
        system=system,
        messages=messages,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
    )


__all__ = [
    "complete",
    "get_provider",
    "resolve_model",
    "LLMConfig",
    "LLMResponse",
    "ProviderError",
]