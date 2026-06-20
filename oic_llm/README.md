# oic_llm

Shared multi-provider LLM package for OIC applications. Provides a single
`complete()` call that works across Anthropic Claude, OpenAI GPT, and Google
Gemini, with consistent error handling and provider-agnostic response objects.

**Location:** `src/oic_llm/` (canonical source)  
**Also at:** `oic_llm/` (root copy — scheduled for removal, see `CLEANUP_NOTES.md`)

---

## Quick start

```python
from oic_llm import complete

response = complete(
    system="You are a cyber risk analyst.",
    messages=[{"role": "user", "content": "Summarise the DBIR 2025 key findings."}],
    provider="anthropic",   # optional; falls back to OIC_LLM_PROVIDER env var
    weight="heavy",         # "light" or "heavy"
)

print(response.text)      # generated text
print(response.provider)  # "anthropic"
print(response.model)     # "claude-opus-4-8"
print(response.usage)     # {"input_tokens": ..., "output_tokens": ...}
```

---

## Installation

```bash
# All three provider SDKs (only install the ones you need)
pip install anthropic openai google-genai

# Install oic_llm itself in editable mode (from the repo root)
pip install -e .
```

---

## Configuration

All configuration is via environment variables. No hardcoded credentials or
model strings anywhere in application code.

```bash
# --- Provider credentials ---
export ANTHROPIC_API_KEY=sk-ant-...

export OPENAI_API_KEY=sk-...

# Gemini: AI Studio API key (preferred for local dev)
export GEMINI_API_KEY=AQ...
# Gemini: Vertex AI / Application Default Credentials (for GCP deployment)
export GOOGLE_GENAI_USE_VERTEXAI=1
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_LOCATION=us-central1   # optional, default us-central1

# --- Default provider / weight (optional) ---
export OIC_LLM_PROVIDER=anthropic   # default: anthropic
export OIC_LLM_WEIGHT=heavy         # default: heavy
```

See `.env.example` at the repo root for a copy-paste template.

---

## Model matrix

Model strings are the **single source of truth** in `registry.py`.
Update only there — never hardcode a model string in application code.

| Provider  | Weight | Model (2026-06-20)         | Temperature |
|-----------|--------|----------------------------|-------------|
| anthropic | light  | `claude-sonnet-4-6`        | supported   |
| anthropic | heavy  | `claude-opus-4-8`          | **dropped** |
| openai    | light  | `gpt-5.4-mini`             | **dropped** |
| openai    | heavy  | `gpt-5.5`                  | **dropped** |
| gemini    | light  | `gemini-3.5-flash`         | supported   |
| gemini    | heavy  | `gemini-3.1-pro-preview`   | supported   |

### Temperature constraints

Several modern models are **reasoning / adaptive-thinking models** that do not
accept a custom temperature. Passing one returns a `400 invalid_request_error`
from the API. `oic_llm` silently drops the parameter for these models — callers
do not need to know which models support it.

Affected models as of June 2026:
- **All GPT-5 and o-series models** (`gpt-5.*`, `o1-*`, `o3-*`, `o4-*`) — OpenAI
  locked temperature support out of the entire GPT-5 generation.
- **Claude Opus 4.7 and later** (`claude-opus-4-7`, `claude-opus-4-8`,
  `claude-fable-5`, `claude-mythos-*`) — Anthropic's adaptive-thinking models
  reject the parameter.

The guard predicates (`_supports_temperature()`) live at the top of each
provider file and are the first place to update when vendors change this.

---

## API reference

### `complete()`

```python
def complete(
    *,
    system: str,
    messages: list[dict],      # [{"role": "user"|"assistant", "content": str}]
    provider: str | None,      # overrides OIC_LLM_PROVIDER
    weight: str | None,        # "light" | "heavy"; overrides OIC_LLM_WEIGHT
    max_tokens: int = 4096,
    temperature: float | None, # silently dropped for models that don't support it
) -> LLMResponse
```

### `LLMResponse`

```python
@dataclass
class LLMResponse:
    text: str           # generated text
    provider: str       # "anthropic" | "openai" | "gemini"
    model: str          # concrete model ID used (e.g. "claude-opus-4-8")
    usage: dict         # token counts — keys vary by provider (see below)
    raw: Any            # underlying SDK response object, for debugging
```

Usage key names by provider:

| Provider  | Keys |
|-----------|------|
| anthropic | `input_tokens`, `output_tokens` |
| openai    | `prompt_tokens`, `completion_tokens`, `total_tokens` |
| gemini    | `prompt_tokens`, `candidates_tokens`, `total_tokens` |

### `ProviderError`

```python
class ProviderError(Exception):
    provider: str   # "anthropic" | "openai" | "gemini"
    kind: str       # "auth" | "rate_limit" | "not_found" | "unknown"
    cause: Exception | None   # original SDK exception
```

---

## Error handling

```python
from oic_llm import complete, ProviderError

try:
    response = complete(system="...", messages=[...])
except ProviderError as e:
    if e.kind == "auth":
        print(f"Check your API key for {e.provider}")
    elif e.kind == "rate_limit":
        print("Rate limited — back off and retry")
    elif e.kind == "not_found":
        print(f"Model not in registry: check registry.py")
    else:
        print(f"Unexpected error: {e}")
```

---

## Provider notes

### Anthropic

- Auth: `ANTHROPIC_API_KEY`
- System prompt passed via the `system` parameter (not injected into messages)
- Thinking / tool-use blocks in the response are skipped; only `type="text"` blocks
  are returned in `response.text`
- `claude-opus-4-8` has adaptive thinking always on — temperature is ignored

### OpenAI

- Auth: `OPENAI_API_KEY`
- System prompt injected as a `{"role": "system"}` message at position 0
- GPT-5 series uses `max_completion_tokens` (not `max_tokens`); handled automatically
- GPT-5 and o-series models do not support custom temperature

### Gemini

- Auth: `GEMINI_API_KEY` (AI Studio) or Vertex AI ADC (GCP deployment)
- System prompt passed via `GenerateContentConfig(system_instruction=...)`
- Contents built with `types.Content` / `types.Part.from_text()` — plain dicts
  are not accepted by all model versions
- Response text extracted via `response.text` (SDK safe accessor) — do not
  iterate `candidates[0].content.parts` directly; it crashes on blocked responses

---

## Testing

### Interactive harness (requires API keys)

```bash
python scripts/test_llm_cli.py
```

Tests API key validity, shows the model matrix, and opens a chat session
to interactively verify each provider and weight combination.

### Model string validation (requires API keys)

```bash
python scripts/validate_models.py
```

Calls `client.models.list()` on each provider and checks that every model ID
in `registry.py` is still available. Run this after any model matrix update.

### Unit tests (no API keys needed)

```bash
# From the repo root
pytest tests/oic_llm/ -m "not integration"
```

### Integration / contract tests (requires API keys)

```bash
pytest tests/oic_llm/ -m integration
```

---

## What to monitor for model changes

The model strings in `registry.py` **will go stale**. Each provider deprecates
models on different schedules. Here is what to watch and where to check.

### Anthropic

- **Deprecation page:** https://docs.anthropic.com/en/docs/about-claude/model-deprecations
- **Models overview:** https://platform.claude.com/docs/en/about-claude/models/overview
- **Watch for:** New Opus, Sonnet, Haiku generation numbers (e.g. 4.9, 5.x).
  New adaptive-thinking models that drop temperature — add them to
  `_NO_TEMPERATURE_MODELS` in `anthropic_provider.py`.
- **Cadence:** Anthropic typically announces deprecations 3–6 months in advance.

### OpenAI

- **Models page:** https://platform.openai.com/docs/models
- **Deprecation notices:** https://platform.openai.com/docs/deprecations
- **Watch for:** New GPT-5.x minor versions (`gpt-5.5`, `gpt-5.6`, etc.) and
  new o-series reasoning models. All GPT-5 and o-series models drop temperature —
  the prefix check in `_NO_TEMPERATURE_PREFIXES` handles new minor versions
  automatically as long as the prefix stays `gpt-5` or `o[0-9]`.
- **Cadence:** OpenAI deprecates with ~3 months notice but moves fast on releases.

### Gemini

- **Models page:** https://ai.google.dev/gemini-api/docs/models
- **Deprecations:** https://ai.google.dev/gemini-api/docs/deprecations
- **Watch for:** Preview models (`gemini-3.1-pro-preview`) become stable or are
  replaced with a new preview. Google does not give long notice on preview
  deprecations — the minimum is typically 2 weeks.
- **Contents API changes:** Google updated the SDK contents format once between
  2024 and 2026. If you see `NoneType is not iterable` or `parts` errors, check
  the SDK changelog: https://github.com/googleapis/python-genai/releases
- **Cadence:** Preview models can be retired with as little as 2 weeks notice.
  Stable models get 3–6 months. Check the deprecation page monthly.

### SDK package versions

| Package | Current tested version | PyPI |
|---------|----------------------|------|
| `anthropic` | `>=0.39.0` | https://pypi.org/project/anthropic |
| `openai` | `>=1.0.0` | https://pypi.org/project/openai |
| `google-genai` | `>=0.3.0` | https://pypi.org/project/google-genai |

Breaking SDK changes that affected this package:
- **google-genai**: `GenerateContentConfig` became a frozen Pydantic model —
  temperature must be set in the constructor, not assigned afterwards.
- **google-genai**: Plain dict contents stopped working for some models —
  use `types.Content` / `types.Part.from_text()`.
- **openai**: `max_tokens` replaced by `max_completion_tokens` for GPT-5 models.

---

## Adding a new provider

1. Create `src/oic_llm/providers/<name>_provider.py` implementing `LLMProvider`
2. Add the class to `_PROVIDERS` in `registry.py`
3. Add `("name", "light")` and `("name", "heavy")` entries to `MODEL_MATRIX`
4. Add temperature support notes in the registry comments
5. Write contract tests in `tests/oic_llm/test_providers_contract.py`
6. Run `python scripts/validate_models.py` to verify model strings

---

## License

MIT
