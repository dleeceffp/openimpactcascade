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
    1. GEMINI_API_KEY or GOOGLE_API_KEY (AI Studio key, AQ or AIza format)
    2. Vertex AI via Application Default Credentials (ADC)
    
    Returns:
        genai.Client instance
    """
    # 1. API key mode (AI Studio)
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if api_key:
        return genai.Client(api_key=api_key)

    # 2. Vertex AI / ADC mode
    if (os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") in ("1", "true", "True") or
        os.environ.get("GOOGLE_CLOUD_PROJECT")):
        return genai.Client(
            vertexai=True,
            project=os.environ["GOOGLE_CLOUD_PROJECT"],
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )

    raise ProviderError(
        "No Gemini credentials: set GEMINI_API_KEY for AI Studio auth, "
        "or set GOOGLE_CLOUD_PROJECT + GOOGLE_GENAI_USE_VERTEXAI=1 for Vertex AI/ADC",
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
        """Generate completion using Gemini API."""
        try:
            # Build the content with system instruction
            contents = []
            for msg in messages:
                if msg["role"] == "user":
                    contents.append({"role": "user", "parts": [{"text": msg["content"]}]})
                elif msg["role"] == "assistant":
                    contents.append({"role": "model", "parts": [{"text": msg["content"]}]})

            # Configure generation using the typed config object
            config = types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
            )
            if temperature is not None:
                config.temperature = temperature

            response: GenerateContentResponse = self.client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )

            # Extract text
            text = ""
            if response.candidates and response.candidates[0].content:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'text'):
                        text += part.text

            # Usage info (if available)
            usage = {}
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "candidates_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count,
                }

            return LLMResponse(
                text=text,
                provider=self.name,
                model=model,
                raw=response,
                usage=usage,
            )

        except google.genai.errors.APIError as e:
            # APIError covers most server-side errors including auth
            if "authentication" in str(e).lower() or "unauthorized" in str(e).lower():
                raise ProviderError(
                    f"Gemini authentication failed: {e}",
                    provider="gemini",
                    kind="auth",
                    cause=e,
                ) from e
            elif "rate" in str(e).lower() or "quota" in str(e).lower():
                raise ProviderError(
                    f"Gemini rate limit/quota exceeded: {e}",
                    provider="gemini",
                    kind="rate_limit",
                    cause=e,
                ) from e
            elif "not found" in str(e).lower():
                raise ProviderError(
                    f"Gemini model not found: {e}",
                    provider="gemini",
                    kind="not_found",
                    cause=e,
                ) from e
            else:
                raise ProviderError(
                    f"Gemini API error: {e}",
                    provider="gemini",
                    kind="unknown",
                    cause=e,
                ) from e
        except Exception as e:
            raise ProviderError(
                f"Gemini error: {e}",
                provider="gemini",
                kind="unknown",
                cause=e,
            ) from e