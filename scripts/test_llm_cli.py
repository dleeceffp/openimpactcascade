#!/usr/bin/env python3
"""
Interactive test harness for oic_llm + oic_search packages.

Validates API keys and model assignments for Anthropic, OpenAI, and Gemini.
Runs model-only by default.  Pass --search to enable web-search grounding,
which addresses the LLM knowledge cut-off using the same pattern as the main
application (ai_question_generator.py: search → format context block → inject
into system prompt).

Usage:
    python scripts/test_llm_cli.py               # model only (default)
    python scripts/test_llm_cli.py --search       # enable web-search grounding
"""

import argparse
import sys
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Add src/ to Python path so oic_llm and oic_search are importable
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))

try:
    from oic_llm import complete, resolve_model, ProviderError
    from oic_llm.registry import list_providers, list_models
except ImportError as e:
    print(f"Error importing oic_llm: {e}")
    print("Install dependencies: pip install anthropic openai google-genai")
    sys.exit(1)

try:
    from oic_search import search, SearchError, SearchResponse
    from oic_search.config import load_config as load_search_config
    from oic_search.registry import list_providers as list_search_providers
    from oic_search.profiles import list_profiles
    _SEARCH_AVAILABLE = True
except ImportError as e:
    print(f"Note: oic_search not importable ({e}) — web search disabled")
    _SEARCH_AVAILABLE = False


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_SYSTEM_PROMPT = (
    "You are a cybersecurity risk and threat intelligence expert. "
    "You have deep knowledge of MITRE ATT&CK, FAIR methodology, DBIR, "
    "CISA advisories, and industry-specific attack patterns. "
    "When grounding context from recent web searches is provided, you MUST "
    "prioritize that information over your training data to overcome your "
    "knowledge cut-off. Cite the specific sources and dates from the provided "
    "context when making claims about recent incidents or statistics."
)

_SEARCH_CONTEXT_HEADER = "=" * 70
_SEARCH_CONTEXT_LABEL = "WEB SEARCH GROUNDING CONTEXT (recent — overrides training data)"


# ---------------------------------------------------------------------------
# Credential checks
# ---------------------------------------------------------------------------

def check_llm_credentials() -> dict:
    """Check which LLM providers have credentials configured."""
    print("\n=== LLM Credentials ===")
    status = {}

    if os.environ.get("ANTHROPIC_API_KEY"):
        key = os.environ["ANTHROPIC_API_KEY"]
        status["anthropic"] = f"OK  (ends ...{key[-10:]})"
    else:
        status["anthropic"] = "MISSING  ANTHROPIC_API_KEY not set"

    if os.environ.get("OPENAI_API_KEY"):
        key = os.environ["OPENAI_API_KEY"]
        status["openai"] = f"OK  (ends ...{key[-10:]})"
    else:
        status["openai"] = "MISSING  OPENAI_API_KEY not set"

    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    gemini_adc = os.environ.get("GOOGLE_CLOUD_PROJECT") and os.environ.get("GOOGLE_GENAI_USE_VERTEXAI")
    if gemini_key:
        status["gemini"] = f"OK  (starts {gemini_key[:10]}...)"
    elif gemini_adc:
        status["gemini"] = f"OK  Vertex AI (project: {os.environ['GOOGLE_CLOUD_PROJECT']})"
    else:
        status["gemini"] = "MISSING  Set GEMINI_API_KEY or GOOGLE_CLOUD_PROJECT+GOOGLE_GENAI_USE_VERTEXAI=1"

    for provider, msg in status.items():
        print(f"  {provider.title():10}: {msg}")

    return status


def check_search_credentials() -> bool:
    """Check whether web search is operational. Returns True if usable."""
    print("\n=== Search Credentials ===")
    if not _SEARCH_AVAILABLE:
        print("  oic_search package not importable — web search disabled")
        return False

    has_google = bool(os.environ.get("GOOGLE_SEARCH_API_KEY"))
    has_brave  = bool(os.environ.get("BRAVE_SEARCH_API_KEY"))
    has_tavily = bool(os.environ.get("TAVILY_API_KEY"))

    if has_google:
        key = os.environ["GOOGLE_SEARCH_API_KEY"]
        print(f"  google_cse : OK  (ends ...{key[-10:]})")
    else:
        print("  google_cse : MISSING  GOOGLE_SEARCH_API_KEY not set")

    if has_brave:
        print("  brave      : OK")
    else:
        print("  brave      : MISSING  BRAVE_SEARCH_API_KEY not set")

    if has_tavily:
        print("  tavily     : OK")
    else:
        print("  tavily     : MISSING  TAVILY_API_KEY not set")

    usable = has_google or has_brave or has_tavily
    if not usable:
        print("  (No search provider available — chat will run without grounding)")
    return usable


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def show_model_matrix():
    print("\n=== Model Matrix ===")
    for (provider, weight), model in list_models().items():
        print(f"  {provider:10} {weight:5}: {model}")


def show_search_profiles():
    if not _SEARCH_AVAILABLE:
        return
    print("\n=== Search Profiles ===")
    for name in list_profiles():
        print(f"  {name}")


# ---------------------------------------------------------------------------
# Interactive selectors
# ---------------------------------------------------------------------------

def select_provider() -> str:
    providers = list_providers()
    print("\n=== Select LLM Provider ===")
    for i, p in enumerate(providers, 1):
        print(f"  {i}. {p.title()}")
    while True:
        try:
            choice = input(f"\nProvider (1-{len(providers)}): ").strip()
            if not choice:
                continue
            idx = int(choice) - 1
            if 0 <= idx < len(providers):
                return providers[idx]
            print("Invalid selection.")
        except ValueError:
            print("Please enter a number.")


def select_weight() -> str:
    print("\n=== Select Model Weight ===")
    print("  1. Light (faster, cheaper)")
    print("  2. Heavy (more capable)")
    while True:
        choice = input("\nWeight (1-2): ").strip()
        if choice == "1":
            return "light"
        if choice == "2":
            return "heavy"
        print("Enter 1 or 2.")


def select_search_profile(search_enabled: bool) -> Optional[str]:
    """Let user pick a search profile, or disable search for this session."""
    if not search_enabled:
        return None

    profiles = list_profiles()
    print("\n=== Select Search Profile ===")
    print("  0. Disable web search for this session")
    for i, name in enumerate(profiles, 1):
        print(f"  {i}. {name}")

    while True:
        try:
            choice = input(f"\nProfile (0-{len(profiles)}): ").strip()
            if not choice:
                continue
            idx = int(choice)
            if idx == 0:
                return None
            if 1 <= idx <= len(profiles):
                return profiles[idx - 1]
            print("Invalid selection.")
        except ValueError:
            print("Please enter a number.")


# ---------------------------------------------------------------------------
# Web search: the same pattern as ai_question_generator._perform_intelligent_web_search
# ---------------------------------------------------------------------------

def _format_search_response(resp: SearchResponse, query: str) -> str:
    """Format a SearchResponse into a prompt-injectable context block.

    Mirrors the format used by ai_question_generator._format_search_results /
    _perform_intelligent_web_search so the LLM sees the same context structure
    as in production.
    """
    if not resp.results:
        return ""

    cache_flag = " [cached]" if resp.cached else ""
    lines = [
        f"### Search: {query}{cache_flag}",
        f"Profile: {resp.profile}  Provider: {resp.provider}  "
        f"Results: {len(resp.results)}",
    ]
    for i, r in enumerate(resp.results, 1):
        lines.append(f"\n**Result {i}:**")
        lines.append(f"Title  : {r.title}")
        lines.append(f"Source : {r.source}")
        lines.append(f"Summary: {r.snippet}")
        lines.append(f"URL    : {r.url}")
        if r.published:
            lines.append(f"Date   : {r.published}")

    return "\n".join(lines)


def run_web_search(
    query: str,
    profile: str,
    num: int = 5,
    active_provider: Optional[str] = None,
) -> str:
    """Execute an oic_search query with timing, provider identification, and fallback.

    Search order:
      1. active_provider if set (mid-session override), else OIC_SEARCH_PROVIDER env var
      2. If that provider fails with a hard error (auth/not_configured/timeout/unknown),
         try each remaining registered provider in order until one succeeds.
      3. rate_limit and quota errors are NOT retried on another provider — they
         indicate the provider is up but temporarily restricted.

    Each attempt prints:
      [search] provider=<name>  profile=<profile>  query...  N result(s)  (X.XXs)

    Returns an empty string when all providers fail, so the chat loop degrades
    gracefully to ungrounded mode.
    """
    if not _SEARCH_AVAILABLE:
        return ""

    # Build the ordered provider list: active/configured first, then fallbacks.
    # Kinds that warrant trying the next provider (provider is broken/unavailable).
    _FALLBACK_KINDS = {"auth", "not_configured", "timeout", "unknown"}

    if active_provider:
        cfg_provider = active_provider
    else:
        try:
            cfg_provider = load_search_config().provider
        except Exception:
            cfg_provider = "tavily"

    all_providers = list_search_providers()
    ordered = [cfg_provider] + [p for p in all_providers if p != cfg_provider and p != "null"]

    for provider_name in ordered:
        is_fallback = provider_name != ordered[0]
        fallback_label = f"  [fallback→{provider_name}]" if is_fallback else ""
        print(
            f"  [search]{fallback_label} provider={provider_name}  "
            f"profile={profile}  {query[:60]!r} ...",
            end="", flush=True,
        )
        t0 = time.perf_counter()
        try:
            resp = search(query, profile=profile, num=num, provider=provider_name)
            elapsed = time.perf_counter() - t0
            cache_label = " [cached]" if resp.cached else ""
            print(f"  {len(resp.results)} result(s){cache_label}  ({elapsed:.2f}s)")
            return _format_search_response(resp, query)

        except SearchError as e:
            elapsed = time.perf_counter() - t0
            if e.kind in _FALLBACK_KINDS and provider_name != ordered[-1]:
                print(f"  FAILED ({e.kind}) ({elapsed:.2f}s) — trying next provider")
            else:
                print(f"  FAILED ({e.kind}) ({elapsed:.2f}s): {e}")
                break  # quota/rate_limit: don't fan-out to other providers

        except Exception as e:
            elapsed = time.perf_counter() - t0
            print(f"  error ({elapsed:.2f}s): {e}")
            break

    return ""


def build_grounded_system_prompt(
    search_profile: Optional[str],
    user_query: str,
    num_results: int = 5,
    active_provider: Optional[str] = None,
) -> str:
    """Build a system prompt that includes fresh web-search context for this turn.

    Matches the approach in ai_question_generator.generate_questionnaire:
      1. Run targeted search query
      2. Format results into a labelled context block
      3. Prepend to system prompt so the LLM treats it as authoritative
         ground truth that overrides its training-data cut-off

    Returns the plain BASE_SYSTEM_PROMPT when search is off or produces nothing.
    """
    if not search_profile:
        return BASE_SYSTEM_PROMPT

    context_block = run_web_search(
        user_query, search_profile, num=num_results, active_provider=active_provider
    )
    if not context_block:
        return BASE_SYSTEM_PROMPT

    current_date = datetime.now().strftime("%Y-%m-%d")
    search_section = "\n".join([
        _SEARCH_CONTEXT_HEADER,
        _SEARCH_CONTEXT_LABEL,
        f"Retrieved: {current_date}",
        _SEARCH_CONTEXT_HEADER,
        context_block,
        _SEARCH_CONTEXT_HEADER,
    ])

    return "\n\n".join([BASE_SYSTEM_PROMPT, search_section])


# ---------------------------------------------------------------------------
# Provider smoke-test
# ---------------------------------------------------------------------------

def test_provider(provider: str, weight: str) -> bool:
    print(f"\n=== Testing {provider.title()} ({weight}) ===")
    try:
        model = resolve_model(provider, weight)
        print(f"Model: {model}")
        print("Sending test request...")
        response = complete(
            system=BASE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": "Say 'API test successful' and nothing else."}],
            provider=provider,
            weight=weight,
            max_tokens=100,
        )
        print(f"Response : {response.text.strip()}")
        print(f"Provider : {response.provider}  Model: {response.model}")
        if response.usage:
            print(f"Usage    : {response.usage}")
        return True
    except ProviderError as e:
        print(f"Provider Error ({e.kind}): {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


# ---------------------------------------------------------------------------
# Chat loop
# ---------------------------------------------------------------------------

def chat_loop(provider: str, weight: str, search_profile: Optional[str]) -> bool:
    """Interactive chat with per-turn web-search grounding.

    Search grounding pattern (matches the main application):
      - Each user message triggers a fresh oic_search query against
        the selected profile before the LLM call.
      - Results are formatted into a context block and prepended to the
        system prompt for that turn only (not accumulated in history).
      - The assistant's reply and the original user message are added to
        history normally so multi-turn context is preserved.

    Returns True to signal "switch provider", False to exit.
    """
    # Resolve the configured search provider for display and mid-session tracking.
    try:
        cfg_provider = load_search_config().provider if _SEARCH_AVAILABLE else None
    except Exception:
        cfg_provider = None

    def _search_status(prov: Optional[str], prof: Optional[str]) -> str:
        if not prof:
            return "disabled"
        return f"{prov or '?'}:{prof}"

    print(f"\n=== Chat with {provider.title()} ({weight})  "
          f"search={_search_status(cfg_provider, search_profile)} ===")
    print("Commands: quit/exit | switch (change provider) | nosearch (toggle search off)")
    print("          search on <profile>      e.g. 'search on incident'")
    print("          use provider <name>      e.g. 'use provider brave'")
    print("-" * 60)
    print(f"Using model: {resolve_model(provider, weight)}")

    messages: List[dict] = []
    active_profile = search_profile       # mutable for this session
    active_search_provider = cfg_provider  # mutable: None means use env config

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit"):
                print("Goodbye!")
                return False
            if user_input.lower() == "switch":
                return True
            if user_input.lower() == "nosearch":
                active_profile = None
                print("Web search disabled for remaining turns.")
                continue
            if user_input.lower().startswith("search on "):
                requested = user_input[len("search on "):].strip()
                if requested in list_profiles():
                    active_profile = requested
                    print(f"Search switched to "
                          f"{_search_status(active_search_provider, active_profile)}.")
                else:
                    print(f"Unknown profile '{requested}'. "
                          f"Available: {', '.join(list_profiles())}")
                continue
            if user_input.lower().startswith("use provider "):
                requested = user_input[len("use provider "):].strip()
                available = [p for p in list_search_providers() if p != "null"]
                if requested in available:
                    active_search_provider = requested
                    print(f"Search provider switched to "
                          f"{_search_status(active_search_provider, active_profile)}.")
                else:
                    print(f"Unknown provider '{requested}'. "
                          f"Available: {', '.join(available)}")
                continue

            # --- Build grounded system prompt for this turn ---
            system = build_grounded_system_prompt(
                search_profile=active_profile,
                user_query=user_input,
                num_results=5,
                active_provider=active_search_provider,
            )

            messages.append({"role": "user", "content": user_input})
            print("Assistant: ", end="", flush=True)

            response = complete(
                system=system,
                messages=messages,
                provider=provider,
                weight=weight,
                max_tokens=2000,
                temperature=0.7,
            )
            reply = response.text.strip()
            print(reply)
            messages.append({"role": "assistant", "content": reply})

        except KeyboardInterrupt:
            print("\nGoodbye!")
            return False
        except ProviderError as e:
            print(f"\nProvider Error ({e.kind}): {e}")
        except Exception as e:
            print(f"\nError: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="oic_llm test harness — model-only by default.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/test_llm_cli.py            # model only\n"
            "  python scripts/test_llm_cli.py --search   # with web-search grounding\n"
        ),
    )
    parser.add_argument(
        "--search",
        action="store_true",
        default=False,
        help="Enable web-search grounding (oic_search). Off by default.",
    )
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("oic_llm Test Harness" + ("  [+search]" if args.search else ""))
    print("=" * 60)

    check_llm_credentials()

    # Search credential check and profile selector only run when --search is passed.
    if args.search:
        search_enabled = check_search_credentials()
        show_search_profiles()
    else:
        search_enabled = False

    show_model_matrix()

    while True:
        provider = select_provider()
        weight   = select_weight()
        search_profile = select_search_profile(search_enabled)

        if not test_provider(provider, weight):
            print("\nProvider test failed. Try another.")
            continue

        if not chat_loop(provider, weight, search_profile):
            break


if __name__ == "__main__":
    main()
