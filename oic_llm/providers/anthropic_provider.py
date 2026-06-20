"""Anthropic provider for oic_llm."""

import os
from typing import List, Dict, Optional

from anthropic import Anthropic
from anthropic.types import Message

from ..base import LLMProvider, LLMResponse, ProviderError


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
        """Generate completion using Anthropic's API."""
        try:
            # Convert messages to Anthropic format
            anthropic_messages = []
            for msg in messages:
                if msg["role"] == "user":
                    anthropic_messages.append({"role": "user", "content": msg["content"]})
                elif msg["role"] == "assistant":
                    anthropic_messages.append({"role": "assistant", "content": msg["content"]})

            response: Message = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=anthropic_messages,
            )

            return LLMResponse(
                text=response.content[0].text,
                provider=self.name,
                model=model,
                raw=response,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
            )

        except Exception as e:
            # Normalize common errors
            if "authentication" in str(e).lower() or "unauthorized" in str(e).lower():
                raise ProviderError(
                    f"Anthropic authentication failed: {e}",
                    provider="anthropic",
                    kind="auth",
                    cause=e,
                ) from e
            elif "rate" in str(e).lower():
                raise ProviderError(
                    f"Anthropic rate limit exceeded: {e}",
                    provider="anthropic",
                    kind="rate_limit",
                    cause=e,
                ) from e
            elif "model" in str(e).lower() and "not found" in str(e).lower():
                raise ProviderError(
                    f"Anthropic model not found: {e}",
                    provider="anthropic",
                    kind="not_found",
                    cause=e,
                ) from e
            else:
                raise ProviderError(
                    f"Anthropic API error: {e}",
                    provider="anthropic",
                    kind="unknown",
                    cause=e,
                ) from e