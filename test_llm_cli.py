#!/usr/bin/env python3
"""
Interactive test harness for oic_llm package.

Validates API keys and model assignments for Anthropic, OpenAI, and Gemini.
Provides an interactive chat interface to test each provider.
"""

import sys
import os
from pathlib import Path

# Add the repo root to Python path so we can import oic_llm
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

try:
    from oic_llm import complete, get_provider, resolve_model, ProviderError
    from oic_llm.registry import list_providers, list_models
except ImportError as e:
    print(f"Error importing oic_llm: {e}")
    print("Make sure you're running this from the repo root.")
    sys.exit(1)


SYSTEM_PROMPT = "You are a testing tool proving API authentication and environmental variable assignment for a software designer."


def check_credentials():
    """Check which providers have credentials configured."""
    print("\n=== Checking Credentials ===")
    
    status = {}
    
    # Anthropic
    if os.environ.get("ANTHROPIC_API_KEY"):
        key = os.environ["ANTHROPIC_API_KEY"]
        status["anthropic"] = f"✓ Set (starts with sk-ant-...{key[-10:]})"
    else:
        status["anthropic"] = "✗ ANTHROPIC_API_KEY not set"
    
    # OpenAI
    if os.environ.get("OPENAI_API_KEY"):
        key = os.environ["OPENAI_API_KEY"]
        status["openai"] = f"✓ Set (starts with sk-...{key[-10:]})"
    else:
        status["openai"] = "✗ OPENAI_API_KEY not set"
    
    # Gemini (multiple auth modes)
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    gemini_adc = os.environ.get("GOOGLE_CLOUD_PROJECT") and os.environ.get("GOOGLE_GENAI_USE_VERTEXAI")
    
    if gemini_key:
        key = gemini_key
        status["gemini"] = f"✓ API key set (starts with {key[:10]}...{key[-10:]})"
    elif gemini_adc:
        status["gemini"] = f"✓ Vertex AI/ADC set (project: {os.environ['GOOGLE_CLOUD_PROJECT']})"
    else:
        status["gemini"] = "✗ No Gemini auth (set GEMINI_API_KEY or GOOGLE_CLOUD_PROJECT + GOOGLE_GENAI_USE_VERTEXAI=1)"
    
    for provider, msg in status.items():
        print(f"  {provider.title():10}: {msg}")
    
    return status


def show_model_matrix():
    """Show the model matrix."""
    print("\n=== Model Matrix ===")
    models = list_models()
    for (provider, weight), model in models.items():
        print(f"  {provider:10} {weight:5}: {model}")


def select_provider():
    """Interactive provider selection."""
    providers = list_providers()
    print("\n=== Select Provider ===")
    
    for i, provider in enumerate(providers, 1):
        print(f"  {i}. {provider.title()}")
    
    while True:
        try:
            choice = input(f"\nEnter provider number (1-{len(providers)}): ").strip()
            if not choice:
                continue
            idx = int(choice) - 1
            if 0 <= idx < len(providers):
                return providers[idx]
            else:
                print("Invalid selection. Try again.")
        except ValueError:
            print("Please enter a number.")


def select_weight():
    """Interactive weight selection."""
    print("\n=== Select Model Weight ===")
    print("  1. Light (faster, cheaper)")
    print("  2. Heavy (more capable)")
    
    while True:
        try:
            choice = input("\nEnter weight number (1-2): ").strip()
            if not choice:
                continue
            if choice == "1":
                return "light"
            elif choice == "2":
                return "heavy"
            else:
                print("Invalid selection. Try again.")
        except ValueError:
            print("Please enter a number.")


def test_provider(provider: str, weight: str):
    """Test a specific provider with a simple completion."""
    print(f"\n=== Testing {provider.title()} ({weight}) ===")
    
    try:
        model = resolve_model(provider, weight)
        print(f"Model: {model}")
        
        print("Sending test request...")
        response = complete(
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": "Say 'API test successful' and nothing else."}],
            provider=provider,
            weight=weight,
            max_tokens=100,
        )
        
        print(f"✓ Success!")
        print(f"Response: {response.text.strip()}")
        print(f"Provider: {response.provider}")
        print(f"Model: {response.model}")
        if response.usage:
            print(f"Usage: {response.usage}")
        
        return True
        
    except ProviderError as e:
        print(f"✗ Provider Error ({e.kind}): {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def chat_loop(provider: str, weight: str):
    """Interactive chat loop."""
    print(f"\n=== Chat with {provider.title()} ({weight}) ===")
    print("Type 'quit' or 'exit' to end the chat.")
    print("Type 'switch' to change provider/weight.")
    print("-" * 50)
    
    model = resolve_model(provider, weight)
    print(f"Using model: {model}")
    
    messages = []
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ("quit", "exit"):
                print("Goodbye!")
                break
            elif user_input.lower() == "switch":
                return True  # Signal to switch providers
            elif not user_input:
                continue
            
            messages.append({"role": "user", "content": user_input})
            
            print("Assistant: ", end="", flush=True)
            response = complete(
                system=SYSTEM_PROMPT,
                messages=messages,
                provider=provider,
                weight=weight,
                max_tokens=2000,
                temperature=0.7,
            )
            
            print(response.text.strip())
            messages.append({"role": "assistant", "content": response.text})
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except ProviderError as e:
            print(f"\nProvider Error ({e.kind}): {e}")
        except Exception as e:
            print(f"\nError: {e}")
    
    return False  # Signal to exit


def main():
    """Main interactive loop."""
    print("oic_llm Test Harness")
    print("=" * 50)
    
    # Check credentials
    status = check_credentials()
    
    # Show model matrix
    show_model_matrix()
    
    # Main loop
    while True:
        # Select provider and weight
        provider = select_provider()
        weight = select_weight()
        
        # Test the provider
        if not test_provider(provider, weight):
            print("\nProvider test failed. Try another provider.")
            continue
        
        # Chat loop
        should_switch = chat_loop(provider, weight)
        if not should_switch:
            break


if __name__ == "__main__":
    main()