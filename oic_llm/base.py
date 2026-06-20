"""Base interfaces and data structures for oic_llm."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    text: str
    provider: str          # "anthropic" | "openai" | "gemini"
    model: str             # concrete model id actually used
    raw: Any = None        # underlying SDK response, for debugging
    usage: Dict[str, Any] = field(default_factory=dict)


class ProviderError(Exception):
    """Normalized error across providers.

    Wraps vendor SDK errors with a consistent interface.
    """
    def __init__(self, message: str, *, provider: str, kind: str = "unknown", cause: Optional[Exception] = None):
        super().__init__(message)
        self.provider = provider
        self.kind = kind  # "auth", "rate_limit", "not_found", "unknown"
        self.cause = cause


@dataclass
class LLMConfig:
    """Configuration loaded from environment and optional config file."""
    provider: str = "anthropic"
    weight: str = "heavy"


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    name: str

    @abstractmethod
    def generate(
        self,
        *,
        system: str,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int = 4096,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        """Generate a completion."""
        ...