# Implementation Brief — `oic_llm`: a shared multi-provider model module for all OIC apps

**For:** a coding agent. Creates a **standalone, reusable package** (`oic_llm`) that every OIC application imports to talk to Claude, GPT, or Gemini. Picking one of the big-three providers is a common pattern across OIC tools, so this is built **once, as a module**, not re-implemented per app.

**Why now:** Google is actively churning its auth model — AI Studio now issues only `AQ.` auth keys, Cloud Console greys out Gemini key creation, standard `AIza` keys are being phased out (June/Sept 2026), and the long-run direction is Google-Cloud-managed auth (ADC / service accounts on the "Agent Platform"/Vertex surface). **This will not be the last change.** The design goal is therefore to isolate *both* provider choice *and* auth mechanism behind one interface, so the next shift is a single edit in one package rather than a sweep through every app.

---

## 0. Design principles (the point of the module)

1. **One interface, three providers.** Every app calls `complete(...)` (or `provider.generate(...)`); the module hides which vendor and which SDK.
2. **Auth is an implementation detail the caller never sees.** Whether Gemini authenticates via an `AQ.` key, an `AIza` key, ADC, or a service account, the caller's code is identical. When Google changes auth again, only this module changes.
3. **Selection by configuration, not code.** Provider and model weight (light/heavy) are chosen via env vars / config file. Apps don't hardcode model strings.
4. **Graceful degradation.** Missing keys, unavailable providers, and auth failures produce clear errors and (where configured) fall back to a default provider — they don't crash the app with an SDK stack trace.
5. **Traceability.** Every response records which provider + concrete model produced it, so generated artifacts can cite their model.

---

## 1. Package layout

```
oic_llm/
  __init__.py            # exports: complete(), get_provider(), LLMConfig, LLMResponse, ProviderError
  base.py                # LLMProvider ABC, LLMResponse, LLMConfig, ProviderError
  registry.py            # name -> provider class; model-matrix resolution
  config.py              # load config from env + optional config file (env wins)
  providers/
    __init__.py
    anthropic_provider.py
    openai_provider.py
    gemini_provider.py    # dual auth-mode (api key OR ADC/vertex), selected by env
  tests/
    test_registry.py
    test_config.py
    test_providers_contract.py   # contract tests run against each provider via a shared suite
```

The package must be importable standalone (its own `pyproject.toml`/`setup.cfg`) so multiple OIC apps depend on it as a normal dependency.

---

## 2. The interface (`base.py`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

@dataclass
class LLMResponse:
    text: str
    provider: str          # "anthropic" | "openai" | "gemini"
    model: str             # concrete model id actually used
    raw: object = None     # underlying SDK response, for debugging
    usage: dict = field(default_factory=dict)

class ProviderError(Exception):
    """Normalized error: auth, rate-limit, not-found, etc. Wraps vendor SDK errors."""
    def __init__(self, message, *, provider, kind="unknown", cause=None):
        super().__init__(message)
        self.provider, self.kind, self.cause = provider, kind, cause

class LLMProvider(ABC):
    name: str
    @abstractmethod
    def generate(self, *, system: str, messages: list[dict], model: str,
                 max_tokens: int = 4096, temperature: float | None = None) -> LLMResponse: ...
```

Normalize the call shape across vendors inside each provider:
- **`system`** is always a separate argument. Anthropic → top-level `system=`; OpenAI → prepend a `{"role":"system"}` message; Gemini → `config={"system_instruction": ...}`.
- **`messages`** is a list of `{"role": "user"|"assistant", "content": str}`. Each provider adapts to its own format.
- Response text is extracted to `LLMResponse.text` (Anthropic `content[0].text`; OpenAI `choices[0].message.content`; Gemini `resp.text`).
- Wrap vendor exceptions in `ProviderError` with a normalized `kind` (`auth`, `rate_limit`, `not_found`, `unknown`) so callers handle errors without importing three SDKs' exception types.

---

## 3. The model matrix (`registry.py` + `config.py`)

Two orthogonal axes, resolved from config to a concrete model id:

- **provider:** `anthropic` | `openai` | `gemini`
- **weight:** `light` | `heavy`

```python
# registry.py — the ONE place model strings live. Update here when vendors rev models.
MODEL_MATRIX = {
    ("anthropic", "light"): "claude-sonnet-4-6",
    ("anthropic", "heavy"): "claude-opus-4-8",
    ("openai",    "light"): "gpt-5.1-mini",     # set to current ids at build time
    ("openai",    "heavy"): "gpt-5.1",
    ("gemini",    "light"): "gemini-3.5-flash",
    ("gemini",    "heavy"): "gemini-3-pro",
}
```

> The agent must set the OpenAI/Gemini ids to whatever is current at build time — do not trust these placeholders. Claude ids shown are current. Keep this table the single source of truth; nothing else hardcodes a model string.

Resolution order (env overrides file overrides default):
- `OIC_LLM_PROVIDER` (default `anthropic`)
- `OIC_LLM_WEIGHT` (default `heavy`)
- optional `oic_llm.toml` / `OIC_LLM_CONFIG` path for the same keys
- explicit args to `complete()` override everything (per-call override).

```python
# usage from any OIC app — this is the whole surface most callers need:
from oic_llm import complete
resp = complete(system=SYS, messages=[{"role":"user","content": prompt}])
print(resp.text, "via", resp.provider, resp.model)

# or pin a choice for one call:
resp = complete(system=SYS, messages=msgs, provider="gemini", weight="light")
```

---

## 4. Provider auth — and the Gemini multi-auth design (the part that will keep changing)

Each provider reads its own credentials from env. Keep Anthropic and OpenAI dead simple; put all the variability in Gemini.

**Anthropic** — `ANTHROPIC_API_KEY`. `Anthropic(api_key=...)`.
**OpenAI** — `OPENAI_API_KEY`. `OpenAI(api_key=...)`.

**Gemini — dual auth mode, selected by environment, behind the same interface.** This is the explicit hedge against Google's ongoing churn. The `google-genai` SDK takes the *same* `generate_content` call regardless of auth, so only the **client construction** differs:

```python
# gemini_provider.py
import os
from google import genai

def _make_gemini_client():
    """
    Auth precedence (first match wins). All produce a google-genai Client with an
    identical generate_content surface, so the rest of the provider is auth-agnostic.

    Google's auth surface is actively changing; when it changes again, edit ONLY this function.
    """
    # 1. Explicit Developer-API key (AI Studio). Works for BOTH the legacy AIza... keys
    #    AND the new AQ.Ab8... auth keys — the SDK sends whichever correctly.
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if api_key:
        return genai.Client(api_key=api_key)

    # 2. Vertex / Agent Platform via Application Default Credentials (no key material).
    #    Used in GCP containers (Cloud Run/GCE service account) and for `gcloud auth
    #    application-default login` locally. Triggered by GOOGLE_GENAI_USE_VERTEXAI=1
    #    or presence of a project id.
    if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") in ("1", "true", "True") \
       or os.environ.get("GOOGLE_CLOUD_PROJECT"):
        return genai.Client(
            vertexai=True,
            project=os.environ["GOOGLE_CLOUD_PROJECT"],
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )

    raise ProviderError(
        "No Gemini credentials: set GEMINI_API_KEY (AI Studio key, AIza or AQ form) "
        "for the CLI, or GOOGLE_CLOUD_PROJECT + ADC for in-GCP use.",
        provider="gemini", kind="auth")
```

Key facts for the agent (verified June 2026):
- The **`AQ.Ab8...`** key now issued by AI Studio is the current "auth key" format. It is passed to the SDK **the same way** as the old `AIza...` key: `genai.Client(api_key=...)`. The credential type changed; the call did not.
- If raw REST is ever used instead of the SDK, the `AQ.` token may need the `x-goog-api-key` header and **not** be combined with any other credential (the "Multiple authentication credentials received" error comes from sending two). **Use the SDK; don't hand-roll REST** — the SDK handles this.
- In GCP containers, prefer ADC (mode 2): no key material in the container, blast radius = the runtime service account's IAM scope. This is the production path.
- For the **CLI prototype**: set `GEMINI_API_KEY` to the AI Studio key (restrict it to the Gemini API in AI Studio — single-API blast radius). That's mode 1; nothing else required.

Because both modes return a `google-genai` `Client`, the provider's `generate()` is written once and works for whichever auth the environment supplies. **The next Google auth change is contained to `_make_gemini_client()`.**

---

## 5. CLI integration (this prototype)

- Add `--provider {anthropic,openai,gemini}` and `--weight {light,heavy}` to the existing CLI, defaulting to the config/env resolution (so flags are optional overrides).
- The app code calls `oic_llm.complete(...)` — it does not import any vendor SDK directly. Grep target: no `import anthropic` / `import openai` / `from google import genai` anywhere **outside** `oic_llm/providers/`.
- Record `resp.provider` + `resp.model` in generated artifacts (STIX `x_oic_context`, markdown summary header), per the reachability brief.
- `.env.example` documents all four credential paths:
  ```
  ANTHROPIC_API_KEY=sk-ant-...
  OPENAI_API_KEY=sk-...
  GEMINI_API_KEY=AQ.Ab8...        # AI Studio key (AQ or AIza), restrict to Gemini API
  # --- OR, for in-GCP / ADC instead of a Gemini key: ---
  # GOOGLE_GENAI_USE_VERTEXAI=1
  # GOOGLE_CLOUD_PROJECT=your-project
  # GOOGLE_CLOUD_LOCATION=us-central1
  ```

---

## 6. Tests (`tests/`)

- **Contract suite** (`test_providers_contract.py`): one shared set of assertions parametrized over all three providers — given a trivial prompt, `generate()` returns a non-empty `LLMResponse` with `provider`/`model` populated. Skip a provider automatically if its credentials are absent (so CI without all keys still passes the others). Mock the SDK clients for a no-network unit variant; mark live calls with an opt-in marker.
- **Registry/config** (`test_registry.py`, `test_config.py`): env overrides file overrides default; unknown provider/weight raises a clear error; per-call args override env.
- **Gemini auth selection**: unit-test `_make_gemini_client()` selection logic with monkeypatched env (key present → api-key mode; project+vertexai flag, no key → vertex/ADC mode; neither → `ProviderError(kind="auth")`). Don't make real calls.
- **Error normalization**: a simulated vendor auth error surfaces as `ProviderError(kind="auth")`, not the raw SDK exception.

---

## 7. Acceptance criteria

1. Any OIC app can `from oic_llm import complete` and run a generation against all three providers by setting env vars only — no app code change to switch providers.
2. `OIC_LLM_PROVIDER` / `OIC_LLM_WEIGHT` (env) and an optional config file select provider+model; per-call args override; defaults are anthropic/heavy.
3. The model matrix is the only place model strings live; `grep -rn` for vendor model ids outside `registry.py` returns nothing.
4. Gemini works in **both** auth modes with no change to caller code: (a) `GEMINI_API_KEY` set (AQ or AIza), (b) `GOOGLE_CLOUD_PROJECT`+ADC, no key. Switching modes is purely environmental.
5. No vendor SDK import exists outside `oic_llm/providers/`.
6. Every `LLMResponse` carries `provider` and the concrete `model`; generated artifacts record them.
7. Missing/blank credentials raise `ProviderError(kind="auth")` with an actionable message; a missing non-default provider can fall back to the default with a logged warning (configurable).
8. Contract tests pass for each provider whose credentials are present; absent-credential providers are skipped, not failed.

---

## 8. Out of scope / do not do

- Do **not** hand-roll REST calls to any provider — use the official SDKs (`anthropic`, `openai`, `google-genai`). The SDKs absorb auth-format changes (this is why the `AQ.` key "just works" through `genai.Client`).
- Do **not** hardcode model strings outside `registry.py`.
- Do **not** import vendor SDKs in app code; go through `oic_llm`.
- Do **not** put OIC domain logic (attack flows, STIX, prompts) in this module — it is a pure provider abstraction reused across apps. Prompts and schemas stay in the apps.
- Do **not** add service-account JSON key files for Gemini in the CLI path; the CLI uses a Gemini API key, in-GCP uses ADC. Service-account JSON is only for non-GCP automated environments and can be added to `_make_gemini_client()` later if needed (ADC already discovers `GOOGLE_APPLICATION_CREDENTIALS`).

---

## 9. Why a module, and why this shape (context)

Picking one of the big three is a recurring need across OIC apps, and the providers' auth is a moving target — Google most visibly, but rate-limit semantics, model ids, and error shapes drift for all three. Centralizing this means: a new model is one line in `registry.py`; a new Google auth mechanism is one function in `gemini_provider.py`; a new provider entirely is one new class plus a registry entry — and **every OIC app inherits all of it for free** by depending on `oic_llm`. The apps stay focused on attack-flow generation; the module owns the vendor churn. The `AQ.`-vs-`AIza`-vs-ADC saga is exactly the kind of thing that should never again touch application code.
