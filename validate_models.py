#!/usr/bin/env python3
"""
Validate model strings against live provider APIs.
Run this to verify the MODEL_MATRIX entries are current.
"""

import os
import sys
from pathlib import Path

# Add the repo root to Python path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

def validate_anthropic():
    """Validate Anthropic models."""
    try:
        from anthropic import Anthropic
        
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("⚠️  Anthropic: No ANTHROPIC_API_KEY, skipping validation")
            return
        
        client = Anthropic(api_key=api_key)
        models = client.models.list()
        
        model_ids = {m.id for m in models}
        
        from oic_llm.registry import MODEL_MATRIX
        
        anthropic_models = [
            MODEL_MATRIX[("anthropic", "light")],
            MODEL_MATRIX[("anthropic", "heavy")]
        ]
        
        print("\n=== Anthropic Models ===")
        for model in anthropic_models:
            if model in model_ids:
                print(f"✓ {model}")
            else:
                print(f"✗ {model} (NOT FOUND)")
                
    except ImportError:
        print("⚠️  Anthropic SDK not installed")
    except Exception as e:
        print(f"✗ Anthropic validation failed: {e}")


def validate_openai():
    """Validate OpenAI models."""
    try:
        from openai import OpenAI
        
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("⚠️  OpenAI: No OPENAI_API_KEY, skipping validation")
            return
        
        client = OpenAI(api_key=api_key)
        models = client.models.list()
        
        model_ids = {m.id for m in models.data}
        
        from oic_llm.registry import MODEL_MATRIX
        
        openai_models = [
            MODEL_MATRIX[("openai", "light")],
            MODEL_MATRIX[("openai", "heavy")]
        ]
        
        print("\n=== OpenAI Models ===")
        for model in openai_models:
            if model in model_ids:
                print(f"✓ {model}")
            else:
                print(f"✗ {model} (NOT FOUND)")
                
    except ImportError:
        print("⚠️  OpenAI SDK not installed")
    except Exception as e:
        print(f"✗ OpenAI validation failed: {e}")


def validate_gemini():
    """Validate Gemini models."""
    try:
        from google import genai
        
        # Try API key auth first
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if api_key:
            client = genai.Client(api_key=api_key)
        else:
            # Try Vertex/ADC
            if os.environ.get("GOOGLE_CLOUD_PROJECT"):
                client = genai.Client(
                    vertexai=True,
                    project=os.environ["GOOGLE_CLOUD_PROJECT"],
                    location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
                )
            else:
                print("⚠️  Gemini: No credentials, skipping validation")
                return
        
        models = client.models.list()
        model_ids = {m.name for m in models}
        
        from oic_llm.registry import MODEL_MATRIX
        
        gemini_models = [
            MODEL_MATRIX[("gemini", "light")],
            MODEL_MATRIX[("gemini", "heavy")]
        ]
        
        print("\n=== Gemini Models ===")
        for model in gemini_models:
            # Gemini models are returned as "models/<model-id>"
            if f"models/{model}" in model_ids or model in model_ids:
                print(f"✓ {model}")
            else:
                print(f"✗ {model} (NOT FOUND)")
                
    except ImportError:
        print("⚠️  Gemini SDK not installed")
    except Exception as e:
        print(f"✗ Gemini validation failed: {e}")


def main():
    """Validate all models in the registry."""
    print("Validating model strings against live APIs...")
    print("Make sure your API keys are set in environment variables.")
    
    validate_anthropic()
    validate_openai()
    validate_gemini()
    
    print("\nDone. Update MODEL_MATRIX in oic_llm/registry.py if any models are marked NOT FOUND.")


if __name__ == "__main__":
    main()