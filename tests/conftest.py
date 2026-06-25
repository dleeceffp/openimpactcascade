"""
Root pytest configuration and shared fixtures.

This file is discovered automatically by pytest because it sits in the
`tests/` root, which is the `testpaths` entry in pyproject.toml.

Path setup
----------
Adds `src/` to sys.path so that `import oic_llm` and `import oic_corpus`
work without a prior `pip install -e .`.  Also adds the repo root so that
`tools/` and `app/` modules can be imported in integration tests.
"""

import os
import sys
from pathlib import Path
import pytest

# --- Path bootstrap ----------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent
SRC_DIR = REPO_ROOT / "src"
APP_DIR = REPO_ROOT / "app"
TOOLS_DIR = REPO_ROOT / "tools"

for _p in (str(SRC_DIR), str(APP_DIR), str(TOOLS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
# -----------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Shared credential-availability helpers (used by integration markers)
# ---------------------------------------------------------------------------

def has_anthropic() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))

def has_openai() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))

def has_gemini() -> bool:
    return bool(
        os.environ.get("GEMINI_API_KEY") or
        os.environ.get("GOOGLE_API_KEY") or
        (os.environ.get("GOOGLE_CLOUD_PROJECT") and os.environ.get("GOOGLE_GENAI_USE_VERTEXAI"))
    )


# ---------------------------------------------------------------------------
# Pytest skip helpers — use as decorators in test files
# ---------------------------------------------------------------------------

requires_anthropic = pytest.mark.skipif(
    not has_anthropic(), reason="ANTHROPIC_API_KEY not set"
)
requires_openai = pytest.mark.skipif(
    not has_openai(), reason="OPENAI_API_KEY not set"
)
requires_gemini = pytest.mark.skipif(
    not has_gemini(), reason="No Gemini credentials set"
)


# ---------------------------------------------------------------------------
# Common fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Absolute path to the repo root."""
    return REPO_ROOT


@pytest.fixture(scope="session")
def generated_dir(repo_root) -> Path:
    """Absolute path to the shared generated/ output directory."""
    return repo_root / "generated"


@pytest.fixture(scope="session")
def corpus_data_dir(repo_root) -> Path:
    """Absolute path to the corpus reference pillar data."""
    return repo_root / "app" / "corpus" / "ref_pillars"
