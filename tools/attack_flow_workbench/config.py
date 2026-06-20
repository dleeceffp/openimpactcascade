"""Configuration settings for the Attack Flow Workbench."""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = BASE_DIR.parent.parent.absolute()

# Corpus settings — pillar YAML data lives under app/corpus/ref_pillars/ while
# the data directory consolidation to data/ is deferred (see CLEANUP_NOTES.md).
# src/oic_corpus/ is the importable package; the data path is configured here.
OIC_PILLARS_DIR = os.getenv("OIC_PILLARS_DIR", str(PROJECT_ROOT / "app" / "corpus" / "ref_pillars"))
OIC_PILLARS_ENABLED = os.getenv("OIC_PILLARS_ENABLED", "1") == "1"

# MITRE schemas — refdocs/ rename to data/ is deferred (see CLEANUP_NOTES.md).
MITRE_MATRICES_DIR = PROJECT_ROOT / "refdocs" / "matrices"
ENTERPRISE_ATTACK_FILE = MITRE_MATRICES_DIR / "enterprise-attack-19.1.json"
ICS_ATTACK_FILE = MITRE_MATRICES_DIR / "ics-attack-19.1.json"

# Attack Flow schema
ATTACK_FLOW_SCHEMA_FILE = PROJECT_ROOT / "refdocs" / "flowschema" / "attack-flow-schema-2.0.0.json"

# Output — all features write to the shared root generated/ tree.
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "generated" / "attack_flows"

# LLM model selection — env-overridable; model strings are sourced from
# src/oic_llm/registry.py. Defaults kept here for standalone CLI use.
OIC_MODEL = os.getenv("OIC_MODEL", "claude-sonnet-4-6")
OIC_MODEL_FAST = os.getenv("OIC_MODEL_FAST", "claude-haiku-4-5")
ENABLE_PROMPT_CACHE = os.getenv("OIC_PROMPT_CACHE", "1") == "1"


def build_system(system_prompt: str, cache: bool = True) -> list[dict]:
    """Return the `system` argument as a content-block list, with prompt caching
    enabled by default. Caching a static system prompt bills cached input at ~10%."""
    block = {"type": "text", "text": system_prompt}
    if cache and ENABLE_PROMPT_CACHE:
        block["cache_control"] = {"type": "ephemeral"}
    return [block]
