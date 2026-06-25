"""Configuration loading for oic_llm."""

import os
from pathlib import Path
from typing import Optional

from .base import LLMConfig


def _env_bool(key: str, default: bool = False) -> bool:
    """Parse boolean from environment variable."""
    val = os.environ.get(key, "").lower()
    return val in ("1", "true", "yes", "on")


def load_config(config_path: Optional[Path] = None) -> LLMConfig:
    """Load configuration from environment and optional config file.

    Environment variables override config file values.
    
    Args:
        config_path: Path to config file (TOML). If None, looks for:
                   - OIC_LLM_CONFIG env var
                   - oic_llm.toml in current dir
                   - ~/.config/oic/llm.toml
    
    Returns:
        LLMConfig instance
    """
    # Start with defaults
    config = LLMConfig()

    # Load from file if present
    if config_path is None:
        # Check env var first
        env_path = os.environ.get("OIC_LLM_CONFIG")
        if env_path:
            config_path = Path(env_path)
        else:
            # Check common locations
            for loc in [Path("oic_llm.toml"), Path.home() / ".config" / "oic" / "llm.toml"]:
                if loc.exists():
                    config_path = loc
                    break

    if config_path and config_path.exists():
        try:
            import tomllib
        except ImportError:
            # Python < 3.11
            import tomli as tomllib

        with open(config_path, "rb") as f:
            data = tomllib.load(f)
            if "provider" in data:
                config.provider = data["provider"]
            if "weight" in data:
                config.weight = data["weight"]

    # Environment overrides
    if os.environ.get("OIC_LLM_PROVIDER"):
        config.provider = os.environ["OIC_LLM_PROVIDER"]
    if os.environ.get("OIC_LLM_WEIGHT"):
        config.weight = os.environ["OIC_LLM_WEIGHT"]

    # Validate
    if config.provider not in ("anthropic", "openai", "gemini"):
        raise ValueError(f"Invalid provider: {config.provider}. Must be one of: anthropic, openai, gemini")
    if config.weight not in ("light", "heavy"):
        raise ValueError(f"Invalid weight: {config.weight}. Must be one of: light, heavy")

    return config