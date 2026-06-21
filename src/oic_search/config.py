"""Configuration loading for oic_search.

Mirrors oic_llm/config.py exactly: env > file > default.
"""

import os
from pathlib import Path
from typing import Optional

from .base import SearchConfig
from .profiles import PROFILES


_VALID_PROVIDERS = ("google_cse", "brave", "tavily", "null")


def load_config(config_path: Optional[Path] = None) -> SearchConfig:
    """Load configuration from environment and optional TOML config file.

    Resolution order (each level overrides the previous):
      1. Built-in defaults  (google_cse / default)
      2. Config file        (oic_search.toml, OIC_SEARCH_CONFIG path, or ~/.config/oic/search.toml)
      3. Environment vars   (OIC_SEARCH_PROVIDER, OIC_SEARCH_PROFILE)

    Args:
        config_path: Explicit path to a TOML config file.  When None, the
                     standard locations are probed in order.

    Returns:
        SearchConfig instance.

    Raises:
        ValueError: If provider or profile is not recognised.
    """
    config = SearchConfig()

    # --- File ---
    if config_path is None:
        env_path = os.environ.get("OIC_SEARCH_CONFIG")
        if env_path:
            config_path = Path(env_path)
        else:
            for loc in [
                Path("oic_search.toml"),
                Path.home() / ".config" / "oic" / "search.toml",
            ]:
                if loc.exists():
                    config_path = loc
                    break

    if config_path and config_path.exists():
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]

        with open(config_path, "rb") as f:
            data = tomllib.load(f)
            if "provider" in data:
                config.provider = data["provider"]
            if "profile" in data:
                config.profile = data["profile"]

    # --- Environment overrides ---
    if os.environ.get("OIC_SEARCH_PROVIDER"):
        config.provider = os.environ["OIC_SEARCH_PROVIDER"]
    if os.environ.get("OIC_SEARCH_PROFILE"):
        config.profile = os.environ["OIC_SEARCH_PROFILE"]

    # OIC_SEARCH_FALLBACK — comma-separated ordered fallback chain.
    # Example: OIC_SEARCH_FALLBACK=brave,tavily
    # The primary provider (OIC_SEARCH_PROVIDER) is NOT repeated here.
    # Auth/not_configured failures on the primary do NOT trigger fallback.
    raw_fallback = os.environ.get("OIC_SEARCH_FALLBACK", "")
    if raw_fallback:
        config.fallback_providers = [
            p.strip() for p in raw_fallback.split(",") if p.strip()
        ]

    # --- Validate ---
    if config.provider not in _VALID_PROVIDERS:
        raise ValueError(
            f"Invalid search provider: '{config.provider}'. "
            f"Must be one of: {', '.join(_VALID_PROVIDERS)}"
        )
    if config.profile not in PROFILES:
        raise ValueError(
            f"Invalid search profile: '{config.profile}'. "
            f"Must be one of: {', '.join(sorted(PROFILES.keys()))}"
        )
    for fb in config.fallback_providers:
        if fb not in _VALID_PROVIDERS:
            raise ValueError(
                f"Invalid fallback provider: '{fb}' in OIC_SEARCH_FALLBACK. "
                f"Must be one of: {', '.join(_VALID_PROVIDERS)}"
            )

    return config
