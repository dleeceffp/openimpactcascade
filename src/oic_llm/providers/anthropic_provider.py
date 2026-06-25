"""Anthropic provider for oic_llm."""

import os
from typing import List, Dict, Optional

from anthropic import Anthropic
from anthropic.types import Message
import anthropic

from ..base import LLMProvider, LLMResponse, ProviderError


# Adaptive-thinking models (Opus 4.7+, Fable 5, Mythos 5) do not support custom
# temperature — the API returns invalid_request_error: "temperature is deprecated
# for this model."  Sonnet 4.6 and Haiku 4.5 still accept it.
# Add new model names here as Anthropic releases adaptive-thinking models.
_NO_TEMPERATURE_MODELS = (
    "claude-opus-4-7",
    "claude-opus-4-8",
    "claude-fable-5",
    "claude-mythos-5",
    "claude-mythos-preview",
)


def _supports_temperature(model: str) -> bool:
    """Return False for models that do not accept a custom temperature."""
    return not any(model.startswith(m) for m in _NO_TEMPERATURE_MODELS)


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""
    name = "anthropic"

    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ProviderError(
                "ANTHROPIC_API_KEY not set",
                provider="anthropic",
                kind="auth",
            )
        self.client = Anthropic(api_key=api_key)

    def generate(
        self,
        *,
        system: str,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int = 4096,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        """Generate a completion using the Anthropic Messages API."""
        try:
            anthropic_messages = []
            for msg in messages:
                if msg["role"] == "user":
                    anthropic_messages.append({"role": "user", "content": msg["content"]})
                elif msg["role"] == "assistant":
                    anthropic_messages.append({"role": "assistant", "content": msg["content"]})

            kwargs: dict = {
                "model": model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": anthropic_messages,
            }

            # Adaptive-thinking models reject temperature; omit silently for those.
            if temperature is not None and _supports_temperature(model):
                kwargs["temperature"] = temperature

            response: Message = self.client.messages.create(**kwargs)

            # Safely extract text — skips thinking blocks, tool-use blocks, etc.
            text = next(
                (b.text for b in response.content if getattr(b, "type", None) == "text"),
                "",
            )

            return LLMResponse(
                text=text,
                provider=self.name,
                model=model,
                raw=response,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
            )

        except anthropic.AuthenticationError as e:
            raise ProviderError(
                f"Anthropic authentication failed: {e}",
                provider="anthropic",
                kind="auth",
                cause=e,
            ) from e
        except anthropic.RateLimitError as e:
            raise ProviderError(
                f"Anthropic rate limit exceeded: {e}",
                provider="anthropic",
                kind="rate_limit",
                cause=e,
            ) from e
        except anthropic.NotFoundError as e:
            raise ProviderError(
                f"Anthropic model not found: {e}",
                provider="anthropic",
                kind="not_found",
                cause=e,
            ) from e
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(
                f"Anthropic API error: {e}",
                provider="anthropic",
                kind="unknown",
                cause=e,
            ) from e
