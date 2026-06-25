"""Tests for configuration loading."""

import os
import tempfile
from pathlib import Path

import pytest

from ..config import load_config


def test_default_config():
    """Test default configuration."""
    # Clear env vars
    for key in ["OIC_LLM_PROVIDER", "OIC_LLM_WEIGHT"]:
        if key in os.environ:
            del os.environ[key]
    
    config = load_config()
    assert config.provider == "anthropic"
    assert config.weight == "heavy"


def test_env_override():
    """Test environment variable override."""
    os.environ["OIC_LLM_PROVIDER"] = "openai"
    os.environ["OIC_LLM_WEIGHT"] = "light"
    
    try:
        config = load_config()
        assert config.provider == "openai"
        assert config.weight == "light"
    finally:
        for key in ["OIC_LLM_PROVIDER", "OIC_LLM_WEIGHT"]:
            if key in os.environ:
                del os.environ[key]


def test_config_file():
    """Test loading from config file."""
    config_content = """
provider = "gemini"
weight = "light"
"""
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(config_content)
        f.flush()
        
        try:
            config = load_config(Path(f.name))
            assert config.provider == "gemini"
            assert config.weight == "light"
        finally:
            os.unlink(f.name)


def test_invalid_provider():
    """Test invalid provider raises error."""
    os.environ["OIC_LLM_PROVIDER"] = "invalid"
    
    try:
        with pytest.raises(ValueError, match="Invalid provider"):
            load_config()
    finally:
        if "OIC_LLM_PROVIDER" in os.environ:
            del os.environ["OIC_LLM_PROVIDER"]


def test_invalid_weight():
    """Test invalid weight raises error."""
    os.environ["OIC_LLM_WEIGHT"] = "invalid"
    
    try:
        with pytest.raises(ValueError, match="Invalid weight"):
            load_config()
    finally:
        if "OIC_LLM_WEIGHT" in os.environ:
            del os.environ["OIC_LLM_WEIGHT"]