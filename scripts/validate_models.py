#!/usr/bin/env python3
"""
Validate model strings in oic_llm/registry.py against the live provider APIs.

Run whenever models are updated to confirm the IDs are still valid.
Uses client.models.list() for each provider -- the authoritative check.

Usage:
    python scripts/validate_models.py
"""

import os
import sys
from pathlib import Path

# Add src/ to Python path so oic_llm is importable
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))


def validate_anthropic():
    """Validate Anthropic models against the API."""
    try:
        from anthropic import Anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("  Anthropic: SKIP (ANTHROPIC_API_KEY not set)")
            return
        client = Anthropic(api_key=api_key)
        model_ids = {m.id for m in client.models.list()}
        from oic_llm.registry import MODEL_MATRIX
        print("\n  Anthropic Models")
        for weight in ("light", "heavy"):
            m = MODEL_MATRIX[("anthropic", weight)]
            mark = "OK  " if m in model_ids else "FAIL"
            print(f"    [{mark}] {weight:5}: {m}")
    except ImportError:
        print("  Anthropic: SKIP (SDK not installed)")
    except Exception as e:
        print(f"  Anthropic: ERROR - {e}")


def validate_openai():
    """Validate OpenAI models against the API."""
    try:
        from openai import OpenAI
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("  OpenAI: SKIP (OPENAI_API_KEY not set)")
            return
        client = OpenAI(api_key=api_key)
        model_ids = {m.id for m in client.models.list().data}
        from oic_llm.registry import MODEL_MATRIX
        print("\n  OpenAI Models")
        for weight in ("light", "heavy"):
            m = MODEL_MATRIX[("openai", weight)]
            mark = "OK  " if m in model_ids else "FAIL"
            print(f"    [{mark}] {weight:5}: {m}")
    except ImportError:
        print("  OpenAI: SKIP (SDK not installed)")
    except Exception as e:
        print(f"  OpenAI: ERROR - {e}")


def validate_gemini():
    """Validate Gemini models against the API."""
    try:
        from google import genai
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if api_key:
            client = genai.Client(api_key=api_key)
        elif os.environ.get("GOOGLE_CLOUD_PROJECT"):
            client = genai.Client(
                vertexai=True,
                project=os.environ["GOOGLE_CLOUD_PROJECT"],
                location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
            )
        else:
            print("  Gemini: SKIP (no credentials; set GEMINI_API_KEY or GOOGLE_CLOUD_PROJECT)")
            return
        model_ids = {m.name for m in client.models.list()}
        from oic_llm.registry import MODEL_MATRIX
        print("\n  Gemini Models")
        for weight in ("light", "heavy"):
            m = MODEL_MATRIX[("gemini", weight)]
            found = f"models/{m}" in model_ids or m in model_ids
            mark = "OK  " if found else "FAIL"
            print(f"    [{mark}] {weight:5}: {m}")
    except ImportError:
        print("  Gemini: SKIP (google-genai not installed)")
    except Exception as e:
        print(f"  Gemini: ERROR - {e}")


def main():
    """Validate all models in the registry."""
    # Reconfigure stdout for UTF-8 on Windows
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("Validating MODEL_MATRIX against live provider APIs")
    print("=" * 50)
    print("Set API keys as env vars before running (see .env.example)")

    validate_anthropic()
    validate_openai()
    validate_gemini()

    print("\nUpdate MODEL_MATRIX in src/oic_llm/registry.py for any FAIL entries.")
    print("Commit a 'Last verified:' date comment with the change.")


if __name__ == "__main__":
    main()
