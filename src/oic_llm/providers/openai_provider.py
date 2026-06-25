"""OpenAI provider for oic_llm."""

import os
from typing import List, Dict, Optional

from openai import OpenAI
from openai.types.chat import ChatCompletion
import openai

from ..base import LLMProvider, LLMResponse, ProviderError


# GPT-5 series and o-series reasoning models do not support custom temperature.
# Passing any value other than the default (1) raises a 400 invalid_request_error.
# Add new model prefixes here as OpenAI releases them.
_NO_TEMPERATURE_PREFIXES = ("gpt-5", "o1", "o3", "o4")


def _supports_temperature(model: str) -> bool:
    """Return False for models that only accept the default temperature."""
    return not any(model.startswith(p) for p in _NO_TEMPERATURE_PREFIXES)


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
        """Generate a completion using the OpenAI chat completions API."""
        try:
            openai_messages = [{"role": "system", "content": system}]
            for msg in messages:
                if msg["role"] in ("user", "assistant"):
                    openai_messages.append({"role": msg["role"], "content": msg["content"]})

            # GPT-5+ uses max_completion_tokens; older models use max_tokens.
            kwargs: dict = {
                "model": model,
                "messages": openai_messages,
                "max_completion_tokens" if model.startswith("gpt-5") else "max_tokens": max_tokens,
            }

            # GPT-5 and reasoning models (o-series) reject any temperature != default.
            # Silently omit the parameter for those models.
            if temperature is not None and _supports_temperature(model):
                kwargs["temperature"] = temperature

            response: ChatCompletion = self.client.chat.completions.create(**kwargs)

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

        except openai.AuthenticationError as e:
            raise ProviderError(
                f"OpenAI authentication failed: {e}",
                provider="openai",
                kind="auth",
                cause=e,
            ) from e
        except openai.RateLimitError as e:
            raise ProviderError(
                f"OpenAI rate limit exceeded: {e}",
                provider="openai",
                kind="rate_limit",
                cause=e,
            ) from e
        except openai.NotFoundError as e:
            raise ProviderError(
                f"OpenAI model not found: {e}",
                provider="openai",
                kind="not_found",
                cause=e,
            ) from e
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(
                f"OpenAI API error: {e}",
                provider="openai",
                kind="unknown",
                cause=e,
            ) from e
