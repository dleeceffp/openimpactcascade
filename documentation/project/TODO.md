# OIC Project — Open To-Do List
*Last updated: June 2026*

This document tracks outstanding work items across the OIC platform.  Items are grouped by component and roughly ordered by priority within each section.  Completed items are removed at each update cycle — see `README_CHANGELOG.md` for the historical record.

---

## Web Search / oic_search

- [ ] **Search result caching review** — the `oic_search` cache uses a file-based store with configurable TTL (`OIC_SEARCH_CACHE_TTL`, default 86400 s).  Validate that Cloud Run's ephemeral filesystem does not cause stale-cache misses across revisions; consider wiring to GCS or Memorystore for a shared cache in multi-instance deployments.
- [ ] **Tavily `search_depth=advanced`** — current integration uses `basic` depth (1 credit/query).  Evaluate whether `advanced` (2 credits, higher relevance) improves quality for ICS/OT scenarios where shallow snippets miss key context.
- [ ] **Recency filter** — Tavily supports `time_range="month"` and Brave supports `freshness="pm"`.  The "ultra_recent_incidents" query is already time-targeted by query string; consider also passing the provider recency flag to filter at the API level.
- [ ] **ICS/OT multi-profile search** — `oic_search.search_multi()` supports fan-out across `["ics", "incident"]` profiles.  The question generator currently uses single-profile `"incident"` for all queries.  Evaluate using multi-profile for industrial/OT industry inputs.
- [ ] **Fallback chain observability** — add a `/health` endpoint field that reports which search providers are reachable, so ops can confirm failover state without digging into logs.
- [ ] **Google CSE removal deadline** — Google CSE deprecated January 1, 2027.  No further code action needed (already removed), but verify no residual references remain in docs, `.env.example`, or CI configs before that date.

---

## OIC Web Application (app/)

- [ ] **Prompt caching** — `ENABLE_PROMPT_CACHE` is wired in `config.py` and `build_system()` but the static system prompt is large.  Measure cache hit rate and token savings in production; confirm the Anthropic `ephemeral` cache_control block is being honoured.
- [ ] **LLM provider abstraction** — `ai_question_generator.py` still instantiates `anthropic.Anthropic()` directly.  The workbench has been migrated to `oic_llm`; evaluate migrating the app to the same shared module for consistent provider switching and model registry.
- [ ] **Streaming responses for chat** — the chat endpoint waits for the full LLM response before returning.  Implement SSE streaming to reduce perceived latency on long coaching responses.
- [ ] **Session context persistence** — `context_storage.py` uses SQLite in the container filesystem, which is ephemeral in Cloud Run.  Migrate to Cloud Spanner or Firestore for durable context across restarts and scale-out.
- [ ] **Rate limiting** — no per-user rate limit on questionnaire generation or chat.  Add token-bucket rate limiting to prevent runaway API spend.
- [ ] **Assessment export** — no way for users to export a completed assessment as PDF or structured JSON.  Add an export endpoint.

---

## Attack Flow Workbench (tools/attack_flow_workbench/)

- [ ] **Multi-path output viewer** — extend `attack_flow_viewer.html` to load multiple STIX bundles side-by-side for multi-path comparisons (OIC-DESIGN-2026-044).
- [ ] **STIX validation gate** — add a `stix2-validator` call inside `write_run_output()` for each `route_NN_*.json` bundle.  Reject bundles that fail validation rather than writing them silently.
- [ ] **Multi-run aggregation** — implement OIC-DESIGN-2026-045: cross-run pattern detection, convergence scoring, and aggregate markdown report across multiple `generate` invocations against the same asset/terminal.
- [ ] **Prompt caching in workbench** — `attack_flow_generator.py` dropped prompt caching with a `# TODO` comment when migrating to `oic_llm`.  Re-implement once the provider abstraction supports cache control.
- [ ] **2x2 model matrix** — `MultiPathGenerator` has a stub for a 2x2 weight x provider model selection matrix (OIC-DESIGN-2026-044 section 4).  Implement the full matrix so credibility assessment uses a different model tier than route generation.

---

## Shared Modules (src/)

- [ ] **`oic_llm` OpenAI provider** — the OpenAI provider has known limitations noted in the README (temperature handling, streaming not implemented).  Validate against the current OpenAI API version.
- [ ] **`oic_search` Google CSE deprecation warning** — add a startup warning if `google_cse` is selected, reminding operators of the January 2027 end-of-life.
- [ ] **Shared test suite CI** — `src/oic_search/` and `src/oic_llm/` each have `tests/` directories.  Wire them into a CI pipeline (GitHub Actions or Cloud Build trigger) so provider contract tests run on every push.
- [ ] **`oic_search` async support** — all providers are currently synchronous.  An async variant (`httpx`-backed) would allow parallel query execution across entries in multi-path workbench runs without thread-pool overhead.

---

## Infrastructure & Deployment

- [ ] **Secret rotation runbook** — document the procedure: update the Secret Manager secret version, then force a new Cloud Run revision (`gcloud run deploy --no-traffic` then traffic shift).
- [ ] **Cloud Armor / WAF** — the service is publicly reachable (`--allow-unauthenticated`).  Evaluate adding a Cloud Armor security policy for rate limiting and geo-restriction.
- [ ] **Alerting policies** — create Cloud Monitoring alert policies for: (a) search provider auth errors (expired key), (b) all search providers exhausted (grounding degraded), (c) Anthropic quota errors.
- [ ] **Staging environment** — no staging environment exists.  Provision a second Cloud Run service (`APP_NAME=openimpactcascade-staging`) backed by separate secrets to validate builds before production promotion.
- [ ] **`.env.example` completeness** — `OIC_SEARCH_FALLBACK` and `APP_USERNAME` / `APP_PASSWORD` are currently absent.  Audit against all env vars read by `config.py`, `ai_question_generator.py`, `oic_search/config.py`, and `oic_llm/config.py`.

---

## Documentation

- [ ] **User Guide update** — `documentation/USER_GUIDE.md` predates cascade-archetype card grounding and recent chat assistant improvements.  Update the walkthrough and step-by-step instructions.
- [ ] **`oic_search` README** — `src/oic_search/README.md` was last updated before the fallback chain was added.  Update to document `search_with_fallback()`, `OIC_SEARCH_FALLBACK`, and the provider priority model.
- [ ] **Architecture diagram** — no up-to-date architecture diagram exists.  Create a Mermaid diagram in `documentation/public/` showing the app, oic_llm, oic_search, corpus, and GCP service relationships.

---

## Technical Debt

- [ ] **Remove `_smoke_test_*.py` files from repo root** — `_smoke_test_search.py` and `_smoke_test_fallback.py` were development artefacts.  Move to `tests/` or delete.
- [ ] **`requests` in `app/requirements.txt`** — now used only by `oic_search` providers (bundled via PYTHONPATH).  Verify whether `app/` code still needs `requests` directly; remove if not.
- [ ] **Version string centralisation** — `cli.py` and `main.py` both hardcode `version="0.1.0"`.  Centralise to `pyproject.toml` or a `__version__` module.
- [ ] **Python version target** — `app/requirements.txt` notes Python 3.8–3.11 compatibility; the Dockerfile uses `python:3.11-slim-bookworm`.  Evaluate upgrading to 3.12 and removing the caveat.
