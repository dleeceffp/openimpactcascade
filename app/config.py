import logging
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Environment bootstrap
# ---------------------------------------------------------------------------
# Resolution order (highest wins):
#   1. Process environment (GCP Cloud Run secrets / docker --env / K8s envFrom)
#   2. Local .env file     (dev server — present only outside containers)
#   3. Built-in defaults   (below)
#
# python-dotenv is already in requirements.txt.  We use override=False so that
# variables already set by the container runtime (Secret Manager, --env flags)
# are never overwritten by a stale .env line.  The loader is silent when .env
# is absent — which is the normal container behaviour.
# ---------------------------------------------------------------------------
_logger = logging.getLogger("oic.config")

def _bootstrap_env() -> None:
    """Load .env into the process environment, if a .env file is found.

    Search order:
      1. OIC_ENV_FILE env var — explicit override (useful in test suites)
      2. .env in the app working directory (typical dev-server layout)
      3. .env one level above the app dir (monorepo root, e.g. OIC_SBX/.env)

    Never raises.  Uses override=False so container secrets always win.
    """
    try:
        from dotenv import load_dotenv, find_dotenv  # type: ignore
    except ImportError:
        # python-dotenv not installed (shouldn't happen — it's in requirements.txt)
        _logger.debug("python-dotenv not available; skipping .env load")
        return

    explicit = os.environ.get("OIC_ENV_FILE")
    if explicit:
        candidates = [Path(explicit)]
    else:
        candidates = [
            Path(".env"),                          # app working dir (dev server / docker CWD)
            Path(__file__).parent / ".env",        # same dir as config.py
            Path(__file__).parent.parent / ".env", # monorepo root (OIC_SBX/.env)
        ]

    for candidate in candidates:
        if candidate.exists():
            load_dotenv(dotenv_path=candidate, override=False)
            _logger.debug("Loaded environment from %s", candidate)
            return

    # No .env found — normal in container deployments where secrets come from
    # Secret Manager or --env flags.  Log at DEBUG so it never alarms.
    _logger.debug(
        "No .env file found (checked %s); relying on process environment",
        ", ".join(str(c) for c in candidates),
    )


_bootstrap_env()

# Anthropic Claude model selection (env-overridable; do not hardcode elsewhere).
OIC_MODEL       = os.getenv("OIC_MODEL", "claude-sonnet-4-6")     # default workhorse
OIC_MODEL_FAST  = os.getenv("OIC_MODEL_FAST", "claude-haiku-4-5") # cheap subtasks
OIC_MODEL_DEEP  = os.getenv("OIC_MODEL_DEEP", "claude-opus-4-8")  # premium deep analysis

# Prompt caching toggle (on by default; lets us disable for debugging).
ENABLE_PROMPT_CACHE = os.getenv("OIC_PROMPT_CACHE", "1") == "1"

def build_system(system_prompt: str, cache: bool = True) -> list[dict]:
    """Return the `system` argument as a content-block list, with prompt caching
    enabled by default. Caching a static system prompt bills cached input at ~10%."""
    block = {"type": "text", "text": system_prompt}
    if cache and ENABLE_PROMPT_CACHE:
        block["cache_control"] = {"type": "ephemeral"}
    return [block]


# Monte Carlo simulation mode: compound (Poisson×severity sum) vs product model.
# Default off for demo stability; validate percentile shift before enabling.
OIC_MC_COMPOUND = os.getenv("OIC_MC_COMPOUND", "1") == "1"

# --- Cascade-archetype card grounding (additive, flag-gated) ---
# Default ON. Set the env var to "0" to revert to the legacy web-only behavior.
OIC_CARDS_ENABLED    = os.getenv("OIC_CARDS_ENABLED", "1") == "1"     # load + ground on cards
OIC_ARCHETYPE_SELECT = os.getenv("OIC_ARCHETYPE_SELECT", "1") == "1"  # show Path A archetype step
OIC_ARCHETYPE_LIMIT  = int(os.getenv("OIC_ARCHETYPE_LIMIT", "3"))     # max archetypes surfaced
# Directory holding the compressed cascade-archetype cards (oic-ca-*.md).
# Relative to the app working directory (/app in the container).
OIC_CARDS_DIR        = os.getenv("OIC_CARDS_DIR", "generated/cascade_archetypes")

# --- Pillar reference grounding (additive, flag-gated) ---
# Default ON. Set the env var to "0" to disable pillar data loading.
OIC_PILLARS_ENABLED  = os.getenv("OIC_PILLARS_ENABLED", "1") == "1"
# Directory holding the pillar YAML files (dbir-*.yaml, netdiligence-*.yaml, etc.)
# Relative to /app in the container (copied by Dockerfile: COPY app/corpus/ /app/corpus/)
OIC_PILLARS_DIR      = os.getenv("OIC_PILLARS_DIR", "corpus/ref_pillars")
