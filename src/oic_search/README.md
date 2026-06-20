# oic_search

Shared pluggable search/grounding module for OIC applications. Provides a single
`search()` call that works across Google Programmable Search Engine, Brave Search,
and Tavily, with curated OIC source profiles, a TTL cache for quota protection and
reproducibility, and normalized errors.

**Sibling of `oic_llm`** — same design philosophy: one interface, swappable backends,
credentials and quotas hidden from app code.

**Location:** `src/oic_search/` (canonical source)

---

## Quick start

```python
from oic_search import search

# Simple search against the "incident" profile (CISA, IC3, Verizon, ENISA...)
resp = search(
    "ransomware healthcare sector 2026",
    profile="incident",
    num=5,
)

for r in resp.results:
    print(r.title, r.source, r.url)

print(f"provider={resp.provider}  profile={resp.profile}  cached={resp.cached}")
```

### Multi-profile (ICS/OT queries)

OT attacks start on the IT side — search both ICS and incident profiles together:

```python
from oic_search import search_multi

resp = search_multi(
    "DERMS ransomware energy grid 2026",
    profiles=["ics", "incident"],
    num=5,
)
```

---

## Installation

```bash
# From the repo root (editable install picks up src/)
pip install -e .

# Only `requests` is required at runtime; all search backends use it directly.
```

---

## Configuration

All configuration via environment variables. No hardcoded credentials anywhere in
application code.

```bash
# --- Provider selection (choose one) ---
export OIC_SEARCH_PROVIDER=google_cse   # default
# export OIC_SEARCH_PROVIDER=brave
# export OIC_SEARCH_PROVIDER=tavily
# export OIC_SEARCH_PROVIDER=null       # "search off" / offline testing

# --- Profile selection ---
export OIC_SEARCH_PROFILE=default       # default

# --- Google CSE credentials ---
export GOOGLE_SEARCH_API_KEY=AIza...    # must have Custom Search API enabled in GCP project
export OIC_SEARCH_CSE_DEFAULT=<cx>      # one engine ID per profile
export OIC_SEARCH_CSE_INCIDENT=<cx>
export OIC_SEARCH_CSE_FRAMEWORK=<cx>
export OIC_SEARCH_CSE_THREATINTEL=<cx>
export OIC_SEARCH_CSE_ICS=<cx>
# Backward-compat fallback for single-engine setups:
# GOOGLE_SEARCH_CSE_ID=<cx>

# --- Brave Search credentials ---
export BRAVE_SEARCH_API_KEY=BSA...

# --- Tavily credentials ---
export TAVILY_API_KEY=tvly-...

# --- Cache settings (optional) ---
export OIC_SEARCH_CACHE_DIR=/tmp/oic_search_cache
export OIC_SEARCH_CACHE_TTL=86400       # seconds, default 24h

# --- Config file (optional, overridden by env) ---
# export OIC_SEARCH_CONFIG=./oic_search.toml
```

See `.env.example` at the repo root for a copy-paste template.

---

## Source profiles

OIC curated site lists live **only** in `profiles.py` — the single source of truth,
mirroring `registry.py` in `oic_llm`.

| Profile | Sites | Site-Restricted eligible | Use case |
|---------|-------|--------------------------|----------|
| `default` | 22 | No (standard CSE) | General-purpose grounding |
| `framework` | 7 | Yes | ATT&CK, CAPEC, CVE, NVD, VERIS |
| `threatintel` | 6 | Yes | Mandiant, Microsoft, CrowdStrike, Palo Alto, Talos |
| `incident` | 7 | Yes | CISA, IC3, Verizon DBIR, ENISA, NCSC, CCCS |
| `ics` | 8 | Yes | Dragos, Claroty, Nozomi, NERC, EISAC, ISA |

**Site-Restricted profiles** use Google's `customsearch/v1/siterestrict` endpoint,
which has no daily query limit. Profiles > 10 domains fall back to the standard
endpoint (100 queries/day free).

---

## API reference

### `search()`

```python
def search(
    query: str,
    *,
    provider: str | None,        # overrides OIC_SEARCH_PROVIDER
    profile: str | None,         # overrides OIC_SEARCH_PROFILE
    num: int = 10,               # max results (1–10)
    force_refresh: bool = False, # bypass cache, re-execute live
    use_cache: bool = True,      # False = no cache read or write
    **opts,                      # provider-specific pass-through
) -> SearchResponse
```

### `SearchResponse`

```python
@dataclass
class SearchResponse:
    results: list[SearchResult]  # normalized results
    provider: str                # "google_cse" | "brave" | "tavily" | "null"
    query: str                   # original query string
    profile: str | None          # OIC profile used
    cached: bool                 # True = served from cache
    raw: Any                     # underlying HTTP response, for debugging
```

### `SearchResult`

```python
@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str                 # short description / extract
    source: str                  # domain, e.g. "cisa.gov"
    published: str | None        # ISO date when available
```

### `SearchError`

```python
class SearchError(Exception):
    provider: str   # "google_cse" | "brave" | "tavily" | "null"
    kind: str       # "auth" | "quota" | "not_configured" | "rate_limit" | "not_found" | "unknown"
    cause: Exception | None
```

---

## Error handling

```python
from oic_search import search, SearchError

try:
    resp = search("pass-the-hash 2024 onward", profile="incident")
except SearchError as e:
    if e.kind == "auth":
        print(f"Check credentials for {e.provider}")
    elif e.kind == "quota":
        print("Daily quota exhausted — switch provider or wait for reset")
    elif e.kind == "not_configured":
        print("Engine not set up — check CSE ID env vars and GCP API enablement")
    elif e.kind == "rate_limit":
        print("Per-minute throttle — back off and retry")
    else:
        print(f"Unexpected error: {e}")
```

**Important:** `quota` and `not_configured` are distinct `kind` values. A Google
`403` that means "API not enabled in GCP project" is `not_configured`; a `403` that
means "daily limit hit" is `quota`. Do not conflate them — the remediation is
completely different.

---

## Caching

The cache is **on by default** — every live result is stored after retrieval.

- Key: `sha256(provider + profile + query + num)`
- Storage: SQLite at `~/.cache/oic/search/oic_search_cache.db` (or `OIC_SEARCH_CACHE_DIR`)
- TTL: 24 hours (or `OIC_SEARCH_CACHE_TTL`)
- `SearchResponse.cached = True` when served from cache

The cache provides two guarantees:
1. **Quota protection** — repeated calls for the same query don't re-bill.
2. **Reproducible model comparisons** — the test harness feeds all three models
   identical search evidence when using "injected" mode.

---

## How this composes with `oic_llm`

```
oic_search (retrieval)  +  oic_llm (reasoning)  =  injected mode
oic_llm alone with a search tool                 =  native mode
```

In injected mode, the test harness calls `search()` once, caches the result, then
calls `oic_llm.complete()` three times (one per model) with the identical evidence
injected into the prompt. This makes model comparisons fair.

In native mode, each LLM's server-side search tool runs independently inside
`oic_llm` — `oic_search` is not involved.

---

## What to monitor for backend changes

### Google Custom Search

- **Status:** Google is actively steering users toward Vertex AI Search. New
  Programmable Search Engines are capped at 50 domains. The Site-Restricted
  endpoint no-daily-limit perk may be withdrawn.
- **Monitor:** https://developers.google.com/custom-search/v1/overview
- **Deprecations:** https://cloud.google.com/blog/?q=custom+search
- **Action if Site-Restricted disappears:** Set `SITE_RESTRICTED_ELIGIBLE` to `False`
  for all profiles in `profiles.py`; the provider falls back to standard endpoint +
  quota automatically.

### Brave Search

- **API reference:** https://api.search.brave.com/app/documentation/web-search
- **Monitor:** Subscription tier changes, endpoint version bumps (`/v1/` → `/v2/`)
- **HTTP status codes:** 401 = auth, 422 = quota/subscription inactive, 429 = rate limit

### Tavily

- **API reference:** https://docs.tavily.com/docs/rest-api/api-reference
- **Monitor:** Endpoint URL, `include_domains` parameter support
- **HTTP status codes:** 401 = auth, 429 = quota/rate limit

---

## Testing

### Unit tests (no API keys, no network)

```bash
pytest tests/oic_search/ -m "not integration"
```

### Integration / live API tests

```bash
pytest tests/oic_search/ -m integration
```

Providers without credentials are automatically skipped, not failed.

---

## Adding a new provider

1. Create `src/oic_search/providers/<name>_provider.py` implementing `SearchProvider`
2. Import and register in `registry.py` `_load_providers()`
3. Add `"name"` to `_VALID_PROVIDERS` in `config.py`
4. Document credentials and `kind` mapping in the provider file
5. Add mocked contract tests to `tests/oic_search/test_providers_contract.py`

---

## License

MIT
