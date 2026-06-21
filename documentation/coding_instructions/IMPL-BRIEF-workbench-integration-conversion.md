# Implementation Brief — Convert the Attack Flow Workbench to `oic_llm` + `oic_search`

**For:** a coding agent working in `tools/attack_flow_workbench/`.
**Goal:** Replace the workbench's direct Anthropic client and legacy `web_search.py` with the shared `oic_llm` and `oic_search` packages, so the generator is provider-agnostic (any of the 3 model vendors × 2 weights) and grounded through the curated search profiles. This is the **swap only** — the multi-flow comparison loop and the 2026-044 multi-path capability are separate follow-on briefs that depend on this landing first.
**Status of dependencies:** `oic_llm` and `oic_search` are built, tested, and confirmed working (3 vendors × 2 weights; Tavily + Brave search backends live). This brief wires the workbench onto them.

---

## 0. Critical context that shaped this brief (read first)

Three facts discovered after the packages were built — they change the defaults:

1. **Google Custom Search is dead for this project.** The Custom Search JSON API is closed to new customers; GCP project `oicv3-052026` was created after the cutoff and is permanently entitlement-blocked (403 PERMISSION_DENIED even with the API showing "Enabled"). **Do not wire the workbench to Google CSE.** The default search provider is **Tavily** (purpose-built for LLM grounding / cutoff supplementation), with Brave as the configured alternate. The legacy `web_search.py` (single-engine CSE) is being **deleted**, not adapted.

2. **The prompt-cache collision is real and must be handled deliberately** (see §3). `config.build_system()` returns an Anthropic-native content-block list with `cache_control`; `oic_llm.complete()` takes a plain string. You cannot pass one through the other.

3. **The model matrix is capability-aligned and settled.** Confirm `src/oic_llm/registry.py` has `("openai","light"): "gpt-5.4"` (NOT `gpt-5.4-mini`). If it still says mini, that's a separate fix — flag it but don't block on it.

---

## 1. What changes, at a glance

| File | Change |
|------|--------|
| `attack_flow_generator.py` | Remove direct `anthropic` client → call `oic_llm.complete()`. Remove `web_search` → call `oic_search.search()`. Add `provider`/`weight` params. Record model in provenance. |
| `cli.py` | Add `--provider`/`--weight`/`--search-provider` flags. Soften the hard `ANTHROPIC_API_KEY` check. |
| `config.py` | Annotate `OIC_MODEL`/`OIC_MODEL_FAST` as superseded; keep `build_system()` for now but generator stops calling it. |
| `web_search.py` | **Delete.** Superseded by `oic_search`. |
| `requirements.txt` / deps | Depend on `oic_llm` and `oic_search` (under `src/`, editable install). Remove direct `anthropic`/`requests`-for-search needs from the workbench. |

---

## 2. `attack_flow_generator.py` — the core swap

### 2.1 Imports and `__init__`

Remove:
```python
import anthropic
from config import OIC_MODEL, OIC_MODEL_FAST, build_system
from web_search import get_web_search
```
Add:
```python
from oic_llm import complete, ProviderError
from oic_search import search, SearchError
```

In `__init__`:
- Remove the `anthropic` import guard, the `ANTHROPIC_API_KEY` check, and `self.client = anthropic.Anthropic(...)`. Credential validation now belongs to `oic_llm`, which raises `ProviderError(kind="auth")` for the *selected* provider at call time — the generator must not assume Anthropic.
- Add `provider: Optional[str] = None` and `weight: Optional[str] = None` parameters; store as `self.provider`, `self.weight`. `None` means "let `oic_llm` resolve from env/config."
- Remove `self.web_search = get_web_search()`. Keep `self.grounding` (corpus/DBIR) and `self.mitre` unchanged.

### 2.2 The LLM call (`_generate_with_llm`)

Replace the `self.client.messages.create(...)` block with:
```python
try:
    resp = complete(
        system=system_prompt,                       # raw STRING from _build_system_prompt()
        messages=[{"role": "user", "content": user_prompt}],
        provider=self.provider,                     # None -> oic_llm env/config default
        weight=self.weight,
        max_tokens=4000,
    )
    content = resp.text
    self._last_model = resp.model                   # capture for provenance
    self._last_provider = resp.provider
    self._last_usage = resp.usage
except ProviderError as e:
    logger.error(f"LLM generation failed ({e.provider}/{e.kind}): {e}")
    return self._generate_fallback_flow(industry, threat_patterns)
```
- Keep the existing JSON-extraction logic (`content.find("{")` … `json.loads(...)`) unchanged — it is provider-agnostic.
- Keep the `json.JSONDecodeError` → fallback path.
- Note the typed `ProviderError` log: a model-not-found vs an auth failure must be distinguishable in the logs (this is why the typed errors exist — don't collapse them to a bare `except`).

### 2.3 Web search (`generate_flow`)

Replace the `self.web_search.search_threats(...)` block with a call through `oic_search`, defaulting to the `incident` profile (best fit for "recent breaches/threats by industry/region") and using a recency window to target post-cutoff material:
```python
web_text = ""
search_provider_used = "none"
search_performed = False
if include_web_search:
    try:
        q = f"{industry} {region} cyber attack breach ransomware"
        sr = search(q, profile="incident", num=5, time_range="year")  # Tavily recency
        if sr.results:
            web_text = self._format_search_results(sr)
            search_provider_used = sr.provider
            search_performed = True
    except SearchError as e:
        logger.warning(f"web search unavailable ({e.kind}): {e}")   # NON-FATAL
```
- **Web search is best-effort. A `SearchError` must never abort generation** (the old code treated it as optional; preserve that).
- `time_range="year"` is a Tavily param; Brave's equivalent is `freshness="py"`. Both are passed via `**opts`. Since the default provider is Tavily, use `time_range`; if you want provider-neutrality, branch on the configured provider or just omit the recency param (the profiles already bias toward current sources). Keep it simple: pass `time_range="year"` and let Brave ignore it (Brave will treat an unknown param harmlessly or you can map it — note it, don't over-engineer).
- Add a small `_format_search_results(self, sr) -> str` that renders each result's title, `source`, `published`, and `snippet`/content into the same prompt-block shape the old `format_results_for_prompt` produced, so the prompt format is unchanged. **Include `source` and `published`** so the model can weight authority and recency — this matters because (as observed in testing) the model will state web-sourced claims with whatever confidence the source implies; surfacing the domain lets it (and the reader) judge authority.

### 2.4 Provenance (`generate_flow`, after generation)

Extend `x_oic_context` so every artifact self-identifies the model and search that produced it:
```python
flow_data["x_oic_context"].update({
    "llm_provider": getattr(self, "_last_provider", "unknown"),
    "llm_model": getattr(self, "_last_model", "unknown"),
    "search_provider": search_provider_used,
    "search_performed": search_performed,
})
```
`search_performed` is a real signal worth capturing: a flow generated without grounding is a different artifact from one that was grounded, and the reader should know which.

---

## 3. The prompt-cache collision (§0 item 2) — resolve, don't smuggle

`config.build_system()` returns `[{"type":"text","text":..., "cache_control":{"type":"ephemeral"}}]`. `oic_llm.complete(system: str)` wants a string. **Do not** try to pass the list through.

Pick one:
- **(Preferred, preserves caching)** Add an optional `cache_system: bool = False` to `oic_llm.complete()` and `AnthropicProvider.generate()`. When set, the Anthropic provider wraps the system string in the `cache_control` block *internally*; other providers ignore it. The generator passes `cache_system=True`. This keeps prompt-caching a provider concern, out of app code. (Touches `oic_llm`, so coordinate with that package.)
- **(Simplest, acceptable now)** Drop prompt caching: generator passes the raw string, no caching. Leave `# TODO: restore prompt caching via oic_llm cache_system flag`. For a workbench/harness the cost is negligible.

Either is fine; **do not block the swap on this.** State which you chose in the PR.

---

## 4. `cli.py` — provider/weight/search flags

- Add optional `--provider {anthropic,openai,gemini}` and `--weight {light,heavy}` (default `None` → `oic_llm` resolves from env/config). Pass into `AttackFlowGenerator(provider=..., weight=...)`.
- Add optional `--search-provider {tavily,brave,null}` (default `None` → `oic_search` env/config default, which is Tavily). Wire it through to the generator's `search()` call via an env set or a passed param. `null` cleanly disables live search for offline runs (equivalent to but cleaner than `--no-web-search`).
- Keep `--no-web-search` working (maps to `include_web_search=False`).
- **Soften `_check_environment()`:** it currently hard-fails without `ANTHROPIC_API_KEY`. Change it to warn only if *none* of `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) is set, and let `oic_llm` raise the precise `ProviderError` for the actually-selected provider. Do the same softening for search: warn if neither `TAVILY_API_KEY` nor `BRAVE_SEARCH_API_KEY` is set, but don't hard-fail (search is optional).

---

## 5. `config.py` and `web_search.py`

- `config.py`: add a comment that `OIC_MODEL` / `OIC_MODEL_FAST` are **no longer used by the generator** (the authoritative model matrix is `src/oic_llm/registry.py`). Leave them defined for backward-compat; don't delete in this PR. `build_system()` stays defined (other callers may exist) but the generator no longer calls it.
- `web_search.py`: **delete it.** Grep the repo first for any other importer (`grep -rn "web_search" tools/ app/ src/`); if the main app imports it, leave a thin shim that raises a clear "use oic_search" error, or migrate that caller in the same PR. Do not leave two web-search paths alive.

---

## 6. Acceptance criteria

1. `python cli.py -i healthcare -r "United States" -s "500-1000"` generates a flow through `oic_llm` (default provider) and `oic_search` (Tavily), writes the STIX bundle + viewer, and the markdown header names the model used.
2. `--provider gemini --weight heavy` generates via `gemini-3.1-pro-preview` with no code change; `--provider openai --weight heavy` uses `gpt-5.5`.
3. A missing key for the *selected* provider raises a clear `ProviderError(kind="auth")`, not a generic crash; a missing key for a non-selected provider does nothing.
4. Web search runs through Tavily by default; `--search-provider brave` switches it; `--search-provider null` (or `--no-web-search`) disables it; a search failure logs a warning and generation still completes.
5. `x_oic_context` in the output records `llm_provider`, `llm_model`, `search_provider`, `search_performed`.
6. `grep -rn "import anthropic\|from web_search\|OIC_MODEL\b" tools/attack_flow_workbench/attack_flow_generator.py` returns nothing.
7. `web_search.py` is gone (or a shim) and no live importer remains.
8. `pip install -e .` from repo root resolves `oic_llm` and `oic_search`.

---

## 7. Out of scope (explicitly defer)

- The **multi-flow comparison loop** (`--compare` across models) — next brief, builds on this.
- The **2026-044 multi-path capability** (terminal-anchored, three-verdict) — separate brief, builds on the loop.
- Google CSE — do not wire it; it's dead for this project.
- Any `succeeds when` control content — firewall; generation stays observed-shape only.
- The main OIC app migration — flagged separately; if `web_search.py` deletion forces a main-app touch, handle just that import, don't migrate the whole app here.

---

## 8. Verify before the PR

1. Single-flow run green for at least **two** providers (e.g. anthropic + gemini), proving provider-agnosticism.
2. A run with `TAVILY_API_KEY` set and a deliberately wrong model string (temporarily) surfaces `ProviderError(kind="not_found")`, confirming typed errors flow through.
3. A run with search disabled completes and `search_performed=false` appears in the output.
4. Grep checks in §6 pass.
5. PR notes which prompt-cache option (§3) was chosen.

---

## Why this shape (context)

The packages were built precisely so this conversion is small: the generator stops knowing about vendors and credentials and just calls `complete()` and `search()`. Defaulting search to Tavily (not the now-dead CSE) keeps the workbench aligned with the post-closure reality, and Tavily's extracted-content model is the right fit for supplementing the model's knowledge cutoff — which was the original reason web search exists in the product. Once this lands, "compare models" is a loop over `provider/weight`, and "multiple attack paths" (2026-044) is a loop over entry points — both become small additions on top of a generator that no longer cares which model or search backend it's using.
