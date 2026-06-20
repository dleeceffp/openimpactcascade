# oic_llm

A shared multi-provider LLM module for OIC applications. Provides a unified interface for Anthropic Claude, OpenAI GPT, and Google Gemini, with built-in support for Google's evolving authentication models.

## Features

- **Unified interface**: Single `complete()` function works with all three providers
- **Model matrix**: Light/heavy model selection via configuration
- **Dual auth for Gemini**: Supports both API keys and Vertex AI/ADC
- **Error normalization**: Consistent error types across providers
- **Environment-based config**: No hardcoded credentials or models
- **Provider traceability**: Every response records which provider/model was used

## Required Dependencies

Before using oic_llm, install these Python packages:

```bash
pip install anthropic openai google-genai
```

- `anthropic` - For Claude API access
- `openai` - For GPT API access  
- `google-genai` - For Gemini API access (supports both API key and Vertex AI auth)

## Quick Start

### 1. Install Dependencies

```bash
pip install anthropic openai google-genai
```

### 2. Use in Your Code

```python
from oic_llm import complete

response = complete(
    system="You are a helpful assistant.",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.text)  # The response
print(response.provider)  # e.g., "anthropic"
print(response.model)  # e.g., "claude-3-5-sonnet-20241022"
```

## Installation

### 1. Install Dependencies

```bash
# Core dependencies for all providers
pip install anthropic openai google-genai

# Optional: for development/testing
pip install pytest pytest-cov
```

### 2. Install the Package

```bash
# Install in development mode (recommended for development)
pip install -e .

# Or install normally
pip install .
```

### Quick Install Command

```bash
pip install anthropic openai google-genai && pip install -e .
```

## Configuration

Set environment variables for your providers:

```bash
# Anthropic
export ANTHROPIC_API_KEY=sk-ant-...

# OpenAI
export OPENAI_API_KEY=sk-...

# Gemini (choose one method)
# Method 1: AI Studio API key
export GEMINI_API_KEY=AQ.Ab8...
# Method 2: Vertex AI / ADC
export GOOGLE_GENAI_USE_VERTEXAI=1
export GOOGLE_CLOUD_PROJECT=your-project
```

Optional defaults:

```bash
export OIC_LLM_PROVIDER=anthropic
export OIC_LLM_WEIGHT=heavy
```

## Model Matrix

| Provider | Light | Heavy |
|----------|-------|-------|
| Anthropic | claude-3-5-sonnet-20241022 | claude-3-5-sonnet-20241022 |
| OpenAI | gpt-4o-mini | gpt-4o |
| Gemini | gemini-1.5-flash | gemini-1.5-pro |

## Testing

### Run the Test Harness

First install dependencies, then run the test harness:

```bash
# Install dependencies
pip install anthropic openai google-genai

# Run the interactive test harness
python test_llm_cli.py
```

### Run Unit Tests

```bash
# Install test dependencies
pip install -e ".[test]"

# Run the test suite
pytest oic_llm/tests/
```

## Provider-Specific Notes

### Gemini Authentication

The Gemini provider supports two authentication modes:

1. **API Key** (`GEMINI_API_KEY`): Use an AI Studio key (AQ.* or AIza.* format)
2. **Vertex AI/ADC**: Set `GOOGLE_GENAI_USE_VERTEXAI=1` and `GOOGLE_CLOUD_PROJECT`

The provider automatically detects which mode to use based on your environment.

### Error Handling

All provider errors are wrapped in `ProviderError` with a `kind` field:

- `auth`: Authentication failed
- `rate_limit`: Rate limit exceeded
- `not_found`: Model not found
- `unknown`: Other errors

## Development

This package is designed to be reused across OIC applications. When adding support for a new provider:

1. Create a new provider class in `oic_llm/providers/`
2. Add it to the registry in `oic_llm/registry.py`
3. Update the model matrix
4. Add contract tests in `oic_llm/tests/test_providers_contract.py`

## License

MIT