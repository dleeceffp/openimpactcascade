"""OpenAI provider for oic_llm."""

import os
from typing import List, Dict, Optional

from openai import OpenAI
from openai.types.chat import ChatCompletion

from ..base import LLMProvider, LLMResponse, ProviderError


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""
    name = "openai"

    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ProviderError(
                "OPENAI_API_KEY not set",
                provider="openai",
                kind="auth",
            )
        self.client = OpenAI(api_key=api_key)

    def generate(
        self,
        *,
        system: str,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int = 4096,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        """Generate completion using OpenAI's API."""
        try:
            # Convert messages to OpenAI format (prepend system message)
            openai_messages = [{"role": "system", "content": system}]
            for msg in messages:
                if msg["role"] in ("user", "assistant"):
                    openai_messages.append({"role": msg["role"], "content": msg["content"]})

            response: ChatCompletion = self.client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=openai_messages,
            )

            return LLMResponse(
                text=response.choices[0].message.content or "",
                provider=self.name,
                model=model,
                raw=response,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            )

        except Exception as e:
            # Normalize common errors
            if "authentication" in str(e).lower() or "unauthorized" in str(e).lower():
                raise ProviderError(
                    f"OpenAI authentication failed: {e}",
                    provider="openai",
                    kind="auth",
                    cause=e,
                ) from e
            elif "rate" in str(e).lower():
                raise ProviderError(
                    f"OpenAI rate limit exceeded: {e}",
                    provider="openai",
                    kind="rate_limit",
                    cause=e,
                ) from e
            elif "model" in str(e).lower() and "not found" in str(e).lower():
                raise ProviderError(
                    f"OpenAI model not found: {e}",
                    provider="openai",
                    kind="not_found",
                    cause=e,
                ) from e
            else:
                raise ProviderError(
                    f"OpenAI API error: {e}",
                    provider="openai",
                    kind="unknown",
                    cause=e,
                ) from e