# Implementation Brief — `oic_search`: a shared pluggable search/grounding module for all OIC apps

**For:** a coding agent. Creates a **standalone, reusable package** (`oic_search`), the third OIC shared module alongside `oic_llm` (model providers) and the attack-flow tooling. Every OIC app that needs web grounding imports it. It abstracts the *search backend* the same way `oic_llm` abstracts the *model vendor* — so when a search provider deprecates or changes (and Google's Custom Search is actively doing so), the change is one class, not a sweep through every app.

**Why a separate module, and why now:** Grounding queries against curated sources is a recurring OIC need (the test harness, the production generation pipeline, future tools). The search backend is a moving target — Google has deprecated "search the entire web," capped new Programmable Search Engines at 50 domains, is steering users to Vertex AI Search, and full-index access now needs a custom quote. Isolating the backend behind one interface is the same hard-won lesson as `oic_llm`: vendor churn must not reach application code.

**Mirror `oic_llm`'s structure exactly** — same shape of interface, registry, config, normalized response, typed errors, and contract tests. A developer who knows `oic_llm` should find `oic_search` immediately familiar.

---

## 0. Before you build — orient

1. Read the `oic_llm` package in full (`base.py`, `registry.py`, `config.py`, `providers/`, `tests/`). `oic_search` is its sibling; copy the patterns, don't invent new ones.
2. Note the design intent: apps call one function (`search(...)`); the module hides which backend (Google Custom Search, Brave, Tavily, Vertex AI Search, or the OIC-curated profiles) actually served it.

---

## 1. Package layout (parallel to oic_llm)

```
oic_search/
  __init__.py            # exports: search(), get_provider(), SearchConfig, SearchResult, SearchResponse, SearchError
  base.py                # SearchProvider ABC, SearchResult, SearchResponse, SearchConfig, SearchError
  registry.py            # name -> provider class; profile -> engine/site mapping
  config.py              # load config from env + optional config file (env wins)
  profiles.py            # the curated source profiles (the OIC site lists live here, ONE place)
  cache.py               # query cache (protects quota, makes comparisons reproducible)
  providers/
    __init__.py
    google_cse_provider.py     # Google Programmable Search Engine (standard + site-restricted)
    brave_provider.py          # Brave Search API (LLM-grounding friendly, non-Google)
    tavily_provider.py         # Tavily (purpose-built for LLM grounding) — optional
    null_provider.py           # returns nothing; for "search off" / offline tests
  tests/
    test_registry.py
    test_config.py
    test_profiles.py
    test_cache.py
    test_providers_contract.py
```

Standalone `pyproject.toml` so OIC apps depend on it as a normal package.

---

## 2. The interface (`base.py`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    source: str = ""          # domain, for provenance/weighting
    published: Optional[str] = None   # ISO date if the backend provides it

@dataclass
class SearchResponse:
    results: List[SearchResult]
    provider: str             # "google_cse" | "brave" | "tavily" | "null"
    profile: Optional[str] = None     # which OIC profile was searched, if any
    query: str = ""
    cached: bool = False
    raw: object = None

class SearchError(Exception):
    """Normalized error across backends."""
    def __init__(self, message, *, provider, kind="unknown", cause=None):
        super().__init__(message)
        self.provider, self.kind, self.cause = provider, kind, cause
        # kind: "auth" | "quota" | "not_configured" | "rate_limit" | "unknown"

class SearchProvider(ABC):
    name: str
    @abstractmethod
    def search(self, query: str, *, profile: Optional[str] = None,
               num: int = 10, **opts) -> SearchResponse: ...
```

Normalization rules (the whole point — every backend returns the same `SearchResult` shape):
- `title`, `url`, `snippet`, `source` (domain), optional `published` date — map each backend's native result shape into this.
- Wrap backend exceptions in `SearchError` with a normalized `kind`. **Critically: a quota-exhausted error is `kind="quota"`, a model/engine-misconfig is `kind="not_configured"`** — do NOT string-match into the wrong bucket (this is the exact bug that bit `oic_llm`, where a 404 was mislabelled as a rate limit). Catch typed backend errors where the SDK provides them.

---

## 3. The OIC source profiles (`profiles.py`)

The curated site lists live here, in ONE place, the way model strings live only in `oic_llm/registry.py`. This is the single source of truth for "which sources ground which kind of query."

```python
# Each profile is <= 10 domains so it qualifies for Google's Site-Restricted CSE
# (no-daily-limit endpoint) AND stays under the 50-domain new-engine cap. Keeping
# profiles small is also what keeps grounding context low-noise.
PROFILES = {
    "default":   [...],   # the consolidated 22-site list, used when no profile is specified
    "framework": ["attack.mitre.org", "ctid.mitre.org", "capec.mitre.org",
                  "verisframework.org", "cve.org", "nvd.nist.gov",
                  "center-for-threat-informed-defense.github.io"],
    "threatintel": ["mandiant.com", "microsoft.com", "crowdstrike.com",
                    "unit42.paloaltonetworks.com", "talosintelligence.com",
                    "cloud.google.com"],
    "incident":  ["cisa.gov", "ic3.gov", "verizon.com", "enisa.europa.eu",
                  "ncsc.gov.uk", "cyber.gc.ca", "github.com/vz-risk/veris"],
    "ics":       ["cisa.gov/topics/industrial-control-systems", "dragos.com",
                  "claroty.com", "nozominetworks.com", "attack.mitre.org/matrices/ics",
                  "nerc.com", "eisac.com", "isa.org"],
}
```

> The agent should populate `default` with the consolidated 22-site list from the project's source-profile decision and confirm each profile is ≤10 domains. **Constraint to enforce in `test_profiles.py`:** every profile (except possibly `default`) has ≤10 entries and no bare TLD patterns, so each maps to a Site-Restricted-eligible Google CSE. `default` may exceed 10 (then it uses the standard CSE with quota) — flag this in a comment.

**Profile ↔ engine mapping:** Google CSE requires one engine (`cx`) per site list. So each profile maps to its own engine id, configured via env/config (e.g. `OIC_SEARCH_CSE_ICS=<cx>`). The provider picks the engine from the profile. The ICS note from the design discussion holds: OT queries usually want `ics` + `incident` together (OT attacks start on the IT side), so the registry should allow a query to target **multiple** profiles and merge+dedupe results.

---

## 4. Providers and credentials

**`google_cse_provider.py`** — the primary backend today. Two modes, auto-selected:
- **Site-Restricted endpoint** (`customsearch/v1/siterestrict`) when the engine is ≤10 sites with no TLD patterns — **no daily query limit.** Prefer this per profile.
- **Standard endpoint** (`customsearch/v1`) otherwise — 100/day free, 10k/day paid.
- Credentials: `GOOGLE_SEARCH_API_KEY` + per-profile engine ids (`OIC_SEARCH_CSE_<PROFILE>`). The Custom Search API must be **enabled** on the key's GCP project (a disabled-service 403 → `SearchError(kind="not_configured")`, not `quota`).
- **VERIFY AT BUILD TIME:** confirm the Site-Restricted endpoint still exists and still carries no daily limit — Google is mid-deprecation (steering toward Vertex AI Search), and this perk may be withdrawn. If gone, fall back to standard endpoint + quota, and surface quota clearly.

**`brave_provider.py`** — non-Google alternative, built for LLM grounding. `BRAVE_SEARCH_API_KEY`. Site-scoping is done via query operators / result filtering rather than pre-configured engines, so the profile's domain list is applied as a filter. This is the hedge against Google churn — having a second real backend proves the abstraction works.

**`tavily_provider.py`** (optional) — purpose-built for LLM grounding, returns clean snippets. `TAVILY_API_KEY`. Include if cheap to add; skip if it delays the core.

**`null_provider.py`** — returns an empty `SearchResponse`. Used for "search off" mode and offline/no-network tests. Always available, needs no credentials.

---

## 5. Caching (`cache.py`) — not optional for this module

A cache is required, for two reasons specific to OIC's use:
1. **Quota protection** — re-running the same test question must not re-bill (matters even with site-restricted, and essential on the standard endpoint).
2. **Reproducible comparisons** — when the test harness compares three models on the *same* evidence (injected mode), all three must see *identical* search results. A cache keyed on `(provider, profile, query, num)` guarantees this; a live re-pull would give each model slightly different evidence and invalidate the comparison.

Implement a simple keyed store (SQLite or JSON files under a cache dir), with a TTL (default e.g. 24h, configurable) and a `force_refresh` flag. `SearchResponse.cached` reports whether a hit was served from cache.

---

## 6. Config & top-level API (`config.py`, `__init__.py`)

Resolution order (env > file > default), mirroring `oic_llm`:
- `OIC_SEARCH_PROVIDER` (default `google_cse`)
- `OIC_SEARCH_PROFILE` (default `default`)
- `GOOGLE_SEARCH_API_KEY`, `OIC_SEARCH_CSE_<PROFILE>`, `BRAVE_SEARCH_API_KEY`, `TAVILY_API_KEY`
- optional `oic_search.toml` / `OIC_SEARCH_CONFIG`

```python
# the whole surface most callers need:
from oic_search import search
resp = search("percentage of attacks involving pass-the-hash since 2024", profile="incident")
for r in resp.results:
    print(r.title, r.url, r.source)
# resp.provider, resp.profile, resp.cached are all populated for traceability
```

---

## 7. How the apps use it (integration, not part of this package)

- **Production OIC apps** keep their existing specific search instructions, now sourced through `oic_search` with the production profile. The module replaces the bespoke search wiring; the prompt-construction logic stays in the app.
- **The model test harness** uses `oic_search` for its `injected` search mode (run search once, feed identical results to all three models via `oic_llm`). The harness's `native` mode does NOT use this module — that's each vendor's own server-side search, inside `oic_llm`. So the two modules compose: `oic_search` (retrieval) + `oic_llm` (reasoning) = injected mode; `oic_llm` alone with a search tool = native mode.
- App code must not import a search SDK directly — go through `oic_search`. Grep target: no `googleapiclient` / `requests`-to-search-endpoints outside `oic_search/providers/`.

---

## 8. Tests

- **Contract suite** parametrized over providers: given a query, `search()` returns a `SearchResponse` with normalized `SearchResult`s; skip a provider whose credentials are absent; `null` always works. Mock HTTP for unit runs; mark live calls opt-in.
- **Profiles:** every non-default profile ≤10 domains, no bare TLD patterns (Site-Restricted eligibility); `default` populated; multi-profile merge dedupes by URL.
- **Cache:** identical query served from cache on second call; `cached` flag set; `force_refresh` bypasses; TTL expiry works.
- **Error normalization:** simulated quota error → `kind="quota"`; disabled-service 403 → `kind="not_configured"`; missing key → `kind="auth"`. (Explicitly assert these don't collapse into a generic bucket — the `oic_llm` mislabel bug must not recur.)

---

## 9. Acceptance criteria

1. Any OIC app can `from oic_search import search` and ground a query by setting env vars only; switching backend is env-only, no app change.
2. Profiles live solely in `profiles.py`; `grep` for hardcoded site lists elsewhere returns nothing.
3. Google CSE provider uses the Site-Restricted endpoint for ≤10-site profiles and standard endpoint otherwise, selected automatically; a build-time note documents whether Site-Restricted still has no daily limit.
4. At least two real backends work behind the same interface (Google CSE + Brave), proving the abstraction (this is the anti-churn guarantee).
5. Cache serves identical results for repeated queries; `cached`/`force_refresh`/TTL all function.
6. Errors normalize to correct `kind` (quota vs not_configured vs auth vs rate_limit) via typed handling, not string-matching.
7. `SearchResponse` carries `provider` and `profile` for traceability; every result has `source` (domain) for provenance/weighting.
8. No search SDK import outside `oic_search/providers/`.

---

## 10. Out of scope / do not do

- Do **not** hardcode site lists outside `profiles.py`.
- Do **not** import search SDKs in app code; go through `oic_search`.
- Do **not** put OIC domain logic (attack flows, prompts, ranking heuristics specific to one app) in this module — it is pure retrieval abstraction. Source *selection* (profiles) lives here; how an app *uses* results stays in the app.
- Do **not** build on "search the entire web" — it's deprecated for new engines; profiles are site-restricted by design.
- Do **not** assume the Site-Restricted no-limit perk is permanent; isolate the backend so a swap to Brave/Tavily/Vertex AI Search is a one-class change.
- Do **not** merge with `oic_llm`; they compose, they don't combine. Search is retrieval; oic_llm is reasoning.

---

## 11. Why this shape (context)

Grounding is a recurring OIC need and the search backend is the most volatile dependency in the stack — Google is actively deprecating the cheap path, and the right hedge is the same one used for models: one interface, swappable backends, credentials and quotas hidden, results normalized. Profiles encode the curated-source decision once and map cleanly onto Google's ≤10-site Site-Restricted engines (which also keeps grounding context low-noise — the original design goal). The module composes with `oic_llm`: retrieval here, reasoning there, and the test harness's injected mode is literally the two modules chained. When Google's next deprecation lands — and the pattern says it will — only `google_cse_provider.py` changes, and apps don't notice.
```
