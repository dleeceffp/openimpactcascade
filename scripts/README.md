# scripts/

Operational scripts for development and validation. These are not part of the deployed application or any importable package — they are run directly from the repo root.

## Scripts

| Script | Purpose | Run as |
|--------|---------|--------|
| `test_llm_cli.py` | Interactive API key validator and chat test for all three LLM providers | `python scripts/test_llm_cli.py` |
| `validate_models.py` | Validates every model ID in `src/oic_llm/registry.py` against the live provider APIs | `python scripts/validate_models.py` |

## Prerequisites

```bash
pip install anthropic openai google-genai
```

Set your API keys (see `.env.example` at the repo root):

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
export GEMINI_API_KEY=AQ.Ab8...
```

## Notes

- Run from the **repo root**, not from inside `scripts/`.
- Both scripts add `src/` to the Python path automatically, so `oic_llm` is importable without a prior `pip install`.
- `validate_models.py` skips any provider whose credentials are absent — it does not fail.
