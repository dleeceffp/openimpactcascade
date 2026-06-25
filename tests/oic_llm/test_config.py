"""Tests for oic_llm configuration loading.

conftest.py adds src/ to sys.path so no sys.path manipulation is needed here.
"""

import os
import tempfile
from pathlib import Path

import pytest

from oic_llm.config import load_config


def test_default_config():
    """Default config uses anthropic / heavy."""
    for key in ("OIC_LLM_PROVIDER", "OIC_LLM_WEIGHT"):
        os.environ.pop(key, None)
    config = load_config()
    assert config.provider == "anthropic"
    assert config.weight == "heavy"


def test_env_override():
    """Environment variables override defaults."""
    os.environ["OIC_LLM_PROVIDER"] = "openai"
    os.environ["OIC_LLM_WEIGHT"] = "light"
    try:
        config = load_config()
        assert config.provider == "openai"
        assert config.weight == "light"
    finally:
        for key in ("OIC_LLM_PROVIDER", "OIC_LLM_WEIGHT"):
            os.environ.pop(key, None)


def test_config_file():
    """TOML config file is loaded when path is provided."""
    config_content = 'provider = "gemini"\nweight = "light"\n'
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(config_content)
        tmp_path = Path(f.name)
    try:
        config = load_config(tmp_path)
        assert config.provider == "gemini"
        assert config.weight == "light"
    finally:
        tmp_path.unlink(missing_ok=True)


def test_invalid_provider():
    """Invalid provider raises ValueError."""
    os.environ["OIC_LLM_PROVIDER"] = "invalid"
    try:
        with pytest.raises(ValueError, match="Invalid provider"):
            load_config()
    finally:
        os.environ.pop("OIC_LLM_PROVIDER", None)


def test_invalid_weight():
    """Invalid weight raises ValueError."""
    os.environ["OIC_LLM_WEIGHT"] = "invalid"
    try:
        with pytest.raises(ValueError, match="Invalid weight"):
            load_config()
    finally:
        os.environ.pop("OIC_LLM_WEIGHT", None)
