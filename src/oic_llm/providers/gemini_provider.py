"""Gemini provider for oic_llm with dual auth mode."""

import os
from typing import List, Dict, Optional

try:
    from google import genai
    from google.genai import types
    from google.genai.types import GenerateContentResponse
    import google.genai.errors
except ImportError as e:
    raise ImportError(
        "google-genai SDK not installed. Install with: pip install google-genai"
    ) from e

from ..base import LLMProvider, LLMResponse, ProviderError


def _make_gemini_client():
    """
    Create a Google GenAI client with dual auth mode.

    Auth precedence (first match wins):
    1. GEMINI_API_KEY or GOOGLE_API_KEY (AI Studio key)
    2. Vertex AI via Application Default Credentials (ADC)
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if api_key:
        return genai.Client(api_key=api_key)

    if (os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") in ("1", "true", "True") or
            os.environ.get("GOOGLE_CLOUD_PROJECT")):
        return genai.Client(
            vertexai=True,
            project=os.environ["GOOGLE_CLOUD_PROJECT"],
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )

    raise ProviderError(
        "No Gemini credentials: set GEMINI_API_KEY for AI Studio, "
        "or GOOGLE_CLOUD_PROJECT + GOOGLE_GENAI_USE_VERTEXAI=1 for Vertex AI/ADC",
        provider="gemini",
        kind="auth",
    )


class GeminiProvider(LLMProvider):
    """Google Gemini provider with dual auth support."""
    name = "gemini"

    def __init__(self):
        try:
            self.client = _make_gemini_client()
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(
                f"Failed to initialize Gemini client: {e}",
                provider="gemini",
                kind="auth",
                cause=e,
            ) from e

    def generate(
        self,
        *,
        system: str,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int = 4096,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        """Generate a completion using the Gemini API."""
        try:
            # Build contents using the typed API.
            # The SDK requires types.Content objects; plain dicts are not accepted
            # by all model versions and cause silent NoneType failures on parts iteration.
            contents = []
            for msg in messages:
                role = msg["role"]
                text = msg["content"]
                if role == "user":
                    contents.append(
                        types.Content(role="user", parts=[types.Part.from_text(text=text)])
                    )
                elif role == "assistant":
                    # Gemini uses "model" for assistant turns
                    contents.append(
                        types.Content(role="model", parts=[types.Part.from_text(text=text)])
                    )
                # Ignore unknown roles rather than crashing

            # Build config in a single constructor call.
            # GenerateContentConfig is a Pydantic model — do NOT mutate after construction.
            config_kwargs: dict = {
                "system_instruction": system,
                "max_output_tokens": max_tokens,
            }
            if temperature is not None:
                config_kwargs["temperature"] = temperature

            config = types.GenerateContentConfig(**config_kwargs)

            response: GenerateContentResponse = self.client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )

            # Use response.text — the SDK's safe accessor that handles blocked/empty
            # responses, thinking blocks, and multi-part candidates without crashing.
            text = response.text or ""

            # Usage metadata
            usage = {}
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                um = response.usage_metadata
                usage = {
                    "prompt_tokens": getattr(um, "prompt_token_count", None),
                    "candidates_tokens": getattr(um, "candidates_token_count", None),
                    "total_tokens": getattr(um, "total_token_count", None),
                }

            return LLMResponse(
                text=text,
                provider=self.name,
                model=model,
                raw=response,
                usage=usage,
            )

        except google.genai.errors.APIError as e:
            msg = str(e).lower()
            if "authentication" in msg or "unauthorized" in msg or "api_key" in msg:
                raise ProviderError(
                    f"Gemini authentication failed: {e}",
                    provider="gemini",
                    kind="auth",
                    cause=e,
                ) from e
            if "rate" in msg or "quota" in msg or "resource_exhausted" in msg:
                raise ProviderError(
                    f"Gemini rate limit/quota exceeded: {e}",
                    provider="gemini",
                    kind="rate_limit",
                    cause=e,
                ) from e
            if "not found" in msg or "not_found" in msg:
                raise ProviderError(
                    f"Gemini model not found: {e}",
                    provider="gemini",
                    kind="not_found",
                    cause=e,
                ) from e
            raise ProviderError(
                f"Gemini API error: {e}",
                provider="gemini",
                kind="unknown",
                cause=e,
            ) from e
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(
                f"Gemini unexpected error: {e}",
                provider="gemini",
                kind="unknown",
                cause=e,
            ) from e
