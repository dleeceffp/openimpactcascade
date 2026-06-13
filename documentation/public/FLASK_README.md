# OpenImpactCascade — Application Reference

| Field | Value |
|-------|-------|
| **Version** | 3.1.0 |
| **Entry point** | `app/main.py` |
| **Default port** | 8080 |
| **Date** | 2026-06-13 |

This document is a reference map of the application: its pages, routes, and file layout. It is not a user guide or a deployment guide — see the links below for those.

| Purpose | Document |
|---------|----------|
| How to use the application | [USER_GUIDE.md](USER_GUIDE.md) |
| AI vendor, data privacy, and safeguards | [AI_DESIGN_AND_CONTROLS.md](AI_DESIGN_AND_CONTROLS.md) |
| Layered controls feature | [LAYERED_CONTROLS_FEATURE.md](LAYERED_CONTROLS_FEATURE.md) |
| Installation and deployment | Deployment guide (see repository root) |

---

## Application Pages

### Public / Pre-authentication

| Route | Template | Description |
|-------|----------|-------------|
| `/login` | `login.html` | Username/password login. Credentials are set via `APP_USERNAME` and `APP_PASSWORD` environment variables. All other routes require an authenticated session. |

---

### Home and Navigation

| Route | Template | Description |
|-------|----------|-------------|
| `/` | `home.html` | Landing page. Presents the two assessment entry points (Industry Risk Assessment and Custom Scenario) and links to the learning pages. |
| `/logout` | — | Clears the session and redirects to `/login`. |

---

### Assessment Generation

| Route | Template | Description |
|-------|----------|-------------|
| `GET /generate` | `generate.html` | Industry risk assessment form. User selects industry, region, and optionally organization size. When cascade archetypes are enabled (`OIC_CARDS_ENABLED`), a card selector is also presented. |
| `POST /generate` | — | Submits the generation form. Calls the AI question generator with corpus and optional web-search grounding. Redirects to `/questionnaire` on success. Generation typically takes 15–40 seconds. |
| `GET /archetype/view/<id>` | `archetype_view.html` | Standalone view of a single cascade archetype card. Opens in a new tab from the archetype selector on the generate form so the user can read the full card without losing their in-progress selection. |
| `GET /generate-custom` | `generate_custom.html` | Custom scenario form. User provides a plain-language description of their risk concern along with industry, region, and organization size. The AI refines the narrative into structured scenario options before generating. |
| `POST /generate-custom` | — | Submits the custom scenario form. Generates a questionnaire targeted at the user-described scenario. Redirects to `/questionnaire` on success. |
| `POST /refine_scenario` | — (JSON) | AJAX endpoint called during custom scenario entry. Takes a narrative description and returns 2–3 structured scenario options for the user to choose from before committing to generation. |

---

### Questionnaire

| Route | Template | Description |
|-------|----------|-------------|
| `GET /questionnaire` | `questionnaire_chat_rationale.html` | The interactive questionnaire. Loads the generated questionnaire from the session, presents questions in sequence, and includes the inline chat assistant sidebar. |
| `POST /context/update` | — (JSON) | AJAX endpoint that records question answers, current question state, and FAIR estimate updates as the user progresses. Persists to SQLite session storage. Used by the questionnaire JavaScript to keep the backend context current for the chat assistant. |

---

### Chat Assistant

| Route | Description |
|-------|-------------|
| `POST /api/chat` | Primary chat endpoint used during the questionnaire. Receives the user message and returns a context-aware response. The assistant has access to the full assessment context: industry, region, org size, questions answered, threat scenario, control tier, and accumulated FAIR estimates. |
| `POST /chat/assist` | Alias endpoint for questionnaire-phase chat assistance. |
| `POST /chat/results` | Chat endpoint for the results page. Operates on the completed assessment context. |
| `GET /chat/export` | Returns the chat transcript for the current session as a downloadable file. |
| `POST /chat/save` | Saves the current chat transcript to the session and optionally to disk. |

---

### Results and Simulation

| Route | Template | Description |
|-------|----------|-------------|
| `POST /analyze` | `results.html` | Runs the Monte Carlo simulation (10,000 iterations) on the FAIR inputs captured during the questionnaire and renders the results page. Displays expected annual loss, 90th-percentile loss, loss distribution chart, and FAIR component summary. |
| `POST /recalculate` | — (JSON) | AJAX endpoint on the results page. Accepts adjusted control parameters and returns recalculated simulation results without a page reload. Used for what-if control adjustment. |

---

### Downloads

| Route | Description |
|-------|-------------|
| `GET /download/<filename>` | Serves a generated questionnaire JSON file by filename. |
| `GET /api/download` | API variant of the download endpoint; accepts `filename` as a query parameter. |

---

### Learning / Reference Pages

These pages are linked from the questionnaire and generate forms. They open in new tabs and can be closed without losing assessment state.

| Route | Template | Description |
|-------|----------|-------------|
| `/about/mitre` | `about_mitre.html` | Overview of the MITRE ATT&CK framework and how it informs the threat scenarios used in assessments. |
| `/about/fair` | `about_fair.html` | Introduction to the FAIR (Factor Analysis of Information Risk) methodology — TEF, vulnerability, LEF, and loss magnitude. |
| `/about/cascade` | `about_cascade.html` | Explanation of cascade attack archetypes: what they are, how they are constructed from MITRE Attack Flows, and why the compression to tactics-level is a gain rather than a loss. |
| `/about/probability-weighting` | `about_probability_weighting.html` | Explanation of the probability weighting adjustments applied in the FAIR quantification engine — PERT distributions, lognormal loss magnitude, and the rationale for each. |
| `/about/layered-controls` | `about_layered_controls.html` | Defense-in-depth principle and the AND-gate mathematics behind the layered controls toggle. Includes a feature feedback link. |

---

### Infrastructure

| Route | Description |
|-------|-------------|
| `GET /health` | Health check endpoint. Returns `{"status": "healthy", "ai_enabled": true/false}`. Used by Cloud Run and load balancers. Does not require authentication. |

---

## File Layout

```
oicv31_dev/
│
├── app/                            # Application package (deployed into container)
│   ├── main.py                     # Flask entry point — all routes defined here
│   ├── ai_question_generator.py    # Questionnaire generation: corpus + web search + LLM
│   ├── simulation.py               # Monte Carlo engine (local, no API cost)
│   ├── config.py                   # Model identifiers, feature flags, build_system() helper
│   ├── user_tracking.py            # SHA-256 user ID hashing, JSONL API call logging
│   ├── context_storage.py          # SQLite-backed assessment context persistence
│   ├── vertex_rag.py               # Legacy Vertex RAG shim (retained for compatibility)
│   │
│   ├── corpus/                     # Local file-based grounding corpus
│   │   ├── retrieve.py             # CorpusRetriever — the seam the generator calls
│   │   ├── schema.py               # Source governance and domain governance rules
│   │   ├── pillar_crosswalk.py     # OIC-authored industry taxonomy bridge
│   │   ├── pillar_reader.py        # In-memory loader for DBIR / IBM / NetDiligence YAML
│   │   └── ref_pillars/            # Reference data YAML (DBIR, NetDiligence, IBM)
│   │       ├── breach_reports/     # Verizon DBIR likelihood data
│   │       ├── financial/          # IBM + NetDiligence magnitude data
│   │       └── threat_landscape/   # Reserved for future pillars
│   │
│   ├── cards/                      # Cascade archetype card library
│   │   ├── __init__.py
│   │   └── library.py              # Card loader and selector
│   │
│   ├── templates/                  # Jinja2 HTML templates
│   │   ├── home.html
│   │   ├── login.html
│   │   ├── generate.html
│   │   ├── generate_custom.html
│   │   ├── questionnaire_chat_rationale.html
│   │   ├── results.html
│   │   ├── archetype_view.html
│   │   ├── about_mitre.html
│   │   ├── about_fair.html
│   │   ├── about_cascade.html
│   │   ├── about_probability_weighting.html
│   │   ├── about_layered_controls.html
│   │   ├── error.html
│   │   └── partials/
│   │       └── chat_sidebar.html
│   │
│   └── static/                     # CSS, JS, images
│       └── css/
│           └── chat_sidebar.css
│
├── generated/                      # Generated questionnaire JSON files (runtime, not committed)
│
├── logs/
│   └── api_calls/                  # Daily JSONL API call logs (YYYY-MM-DD_api_calls.jsonl)
│
├── tools/                          # Operator utilities (not part of the running app)
│   ├── investigate_abuse.py        # Search logs by hashed user ID for abuse investigation
│   ├── analyze_costs.py            # API cost analysis from logs
│   ├── api_cost_tracker.py         # Cost tracking utilities
│   ├── inspect_corpus.py           # Corpus coverage inspection
│   ├── cascade_cards/              # Card authoring and validation tools
│   └── bq_rag_ingest/              # Legacy BigQuery ingest pipeline (archived reference)
│
├── tests/                          # Test suite
│   ├── fair_model/                 # FAIR/simulation unit tests
│   ├── fixtures/                   # Pillar reader and crosswalk tests
│   └── ui_features/                # Context storage and UI feature tests
│
├── documentation/                  # Project documentation
│   ├── USER_GUIDE.md               # End-user guide (use cases, interaction instructions)
│   ├── AI_DESIGN_AND_CONTROLS.md   # AI vendor, data privacy, safeguards
│   ├── LAYERED_CONTROLS_FEATURE.md # Layered controls feature reference
│   ├── flask_readme.md             # This file — application reference and site map
│   ├── project/                    # Design documents and ADRs
│   │   ├── OIC-DESIGN-2026-001-end-to-end.md
│   │   ├── OIC-DESIGN-2026-002-cascade-compression-revB.md
│   │   ├── ADR-0012-retrieval-architecture.md
│   │   ├── ADR-0012-crosswalk-spec.md
│   │   └── ADR-0014-local-corpus-v1.md
│   └── historical/                 # Superseded documents (reference only)
│
└── archives/                       # Superseded application files (reference only)
```

---

## Key Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key. Managed via GCP Secret Manager in production. |
| `APP_USERNAME` | Yes | Login username (default: `admin`). |
| `APP_PASSWORD` | Yes | Login password. No default — application will not start without this. |
| `SECRET_KEY` | Yes (prod) | Flask session secret key. Use a strong random value in production. |
| `OIC_MODEL` | No | Primary LLM model (default: `claude-sonnet-4-6`). |
| `OIC_MODEL_FAST` | No | Fast model for lightweight tasks (default: `claude-haiku-4-5`). |
| `OIC_MODEL_DEEP` | No | Deep model for intensive analysis (default: `claude-opus-4-8`). |
| `OIC_PROMPT_CACHE` | No | Enable prompt caching (`1`/`0`, default: `1`). |
| `OIC_CARDS_ENABLED` | No | Enable cascade archetype card library (`1`/`0`, default: `1`). |
| `OIC_ARCHETYPE_SELECT` | No | Show archetype selector step on generate form (`1`/`0`, default: `1`). |
| `OIC_ARCHETYPE_LIMIT` | No | Maximum archetypes shown in selector (default: `3`). |
| `OIC_PILLARS_ENABLED` | No | Enable DBIR/IBM/NetDiligence pillar grounding (`1`/`0`, default: `1`). |
| `OIC_MC_COMPOUND` | No | Enable compound Monte Carlo simulation mode (`1`/`0`, default: `1`). |
| `GOOGLE_CUSTOM_SEARCH_API_KEY` | No | Enables web search gap-filling during generation. If not set, generation falls back to corpus-only. |

For full deployment instructions and infrastructure configuration see the deployment guide.
