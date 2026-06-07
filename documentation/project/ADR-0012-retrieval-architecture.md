# ADR-0012: Retrieval Architecture — Markdown + Frontmatter with Metadata-Filtered Cached Injection

> **Assign the real number per your sequence.** This is written as `ADR-0012`; renumber to fit `documentation/` if you already have ADRs 0001–00NN. Cross-reference from `OIC-DD-2026-003` (5-category likelihood scale) and the design doc `OIC-DESIGN-2026-001`.

| Field | Value |
|-------|-------|
| **Status** | Proposed (supersedes the implicit "Vertex RAG corpus + BigQuery ingest" design) |
| **Date** | 2026-05-31 |
| **Deciders** | D. Leece (owner/architect) |
| **Supersedes** | Vertex AI RAG Engine as the *core* retrieval layer; the documented-but-unbuilt `tools/bq_rag_ingest` BigQuery embeddings pipeline |
| **Related** | `OIC-DD-2026-003` (likelihood scale), `OIC-DESIGN-2026-001` (end-to-end design) |
| **Tags** | retrieval, RAG, corpus, freemium-economics, vendor-portability |

---

## 1. Context and Problem Statement

OpenImpactCascade (OIC) grounds AI-generated risk questionnaires and chat assistance in a **curated corpus** of authoritative cybersecurity sources (NIST, CISA, OWASP, MITRE ATT&CK) plus original synthesized analysis from `caffeinatedrisk.com`. The original architecture used a managed **Vertex AI RAG corpus** (vector embeddings + semantic top-k retrieval) and a planned **BigQuery ingestion pipeline** with separate `documents`, `chunks`, `embeddings`, `retrieval_logs`, and `retrieval_log_results` tables.

Two things have changed since that design was set:

1. **The product goal is now explicit**: convert OIC into a **freemium SaaS for SMB risk management**. The conference (BSides-adjacent) is a *delivery forcing function*, not the objective. This makes free-tier unit economics and long-term defensibility first-class design drivers — not afterthoughts.
2. **The retrieval landscape shifted (late 2025 → mid 2026)**. Frontier models (Claude Sonnet 4.6 / Opus 4.7, Gemini, GPT) now ship **1M-token context windows at standard pricing with no long-context surcharge**, and **prompt caching reduces cached input cost by ~90%**. The pattern widely considered obsolete is precisely the one the original design implements: *chunk → embed → top-k → stuff*. Naive vector RAG is now a liability (chunking splits definitions from usage, embeddings age, failures are opaque and undebuggable) for corpora that are **fixed, curated, and small per query**.

OIC's corpus has exactly that profile. Any single questionnaire needs a **slice** — one industry, one region, a few domains/scenarios — which is a handful of documents well under 100K tokens, not the whole corpus. The dominant per-query operations are **metadata filtering** ("docs tagged healthcare + Canada") and **deterministic lookup** (MITRE technique IDs, advisory citation validation). Vector cosine similarity is the *wrong tool* for both of those.

**Problem:** Should OIC keep vector RAG as its core retrieval mechanism, or adopt a substrate and selection model better aligned to a curated corpus, freemium economics, and auditability?

---

## 2. Decision Drivers

In priority order for the SaaS goal:

1. **Free-tier marginal cost.** Many free users → grounding must be near-zero marginal cost per interaction. A static, *cached* corpus slice is the cheapest possible grounding; per-query embedding + vector search + web search is the opposite.
2. **Defensibility / "not just ChatGPT with confident wording."** The differentiator is the deterministic FAIR/Monte Carlo engine **plus source traceability**: "here is the authoritative document that grounded this estimate, and you can read it." Transparent markdown maximizes auditability; opaque vectors undercut it.
3. **Vendor portability.** Vector DBs are commoditized; the core product should not be welded to one vendor's proprietary corpus service.
4. **Maintainability for a solo, intermittent side project.** Markdown + a build-time index is debuggable with `grep` and `git diff`. A 5-table embedding pipeline is not, and has no users yet to justify its telemetry.
5. **Curation as the moat.** The metadata that expresses curator judgment should be *first-class, visible, and version-controlled*, not buried in a database.
6. **Headroom to evolve.** The design must allow vectors or agentic file-search to be added later **without rework** if the corpus outgrows a filterable slice.

---

## 3. Considered Options

**Option A — Keep Vertex RAG + BigQuery embeddings as core (status quo).**
Managed semantic retrieval, rich per-chunk feedback loop.
*Rejected:* highest marginal cost per query, vendor lock-in, opaque failures, premature telemetry (no users), and it's the pattern the field has moved past for fixed curated corpora. The per-chunk feedback loop is genuinely well-designed but solves a problem OIC does not yet have.

**Option B — Pure long-context "dump everything as markdown, no retrieval."**
Simplest possible.
*Rejected:* the full corpus across all industries plus MITRE ATT&CK exceeds 1M tokens, so "load everything" doesn't scale, and loading large context on every free interaction is expensive even cached. A selection step is unavoidable.

**Option C — Markdown + frontmatter substrate; metadata-filtered selection into a cached context block (CHOSEN).**
Sources stored as markdown with structured YAML frontmatter. A build-time index enables fast filtering by facet. The selected slice is injected into a *cached* context block. Deterministic FAIR/Monte Carlo remains the defensible core. Optional agentic file-read and optional vector shortlist are reserved as additive, vendor-swappable extensions.

**Option D — GraphRAG / knowledge-graph layer.**
Strong for relational reasoning across many entities.
*Rejected for now:* over-engineered for current corpus size and team; reconsider only if attack-path "cascade" analysis demands explicit entity relationships at scale.

---

## 4. Decision Outcome

**Adopt Option C.**

- **Substrate:** every source becomes a markdown file with a standardized YAML frontmatter block (schema in §5). PDFs are converted once at ingest; original blog content is authored natively in this format.
- **Selection (default path):** at request time, filter the corpus by frontmatter facets (industry, region, domain, scenario, tier eligibility), rank by `quality_rating` × `priority_weight`, and assemble a slice within a token budget (default target ≤ ~150K tokens).
- **Injection:** the slice is placed in a **cached** context block alongside the cached system/methodology prompt. Only the per-request dynamic content (user answers, the specific question) is uncached.
- **Grounding economics:** repeat questionnaires for the same industry/region hit the cache; cached input bills at ~10% of standard.
- **Citations:** the model is instructed to cite by stable document `id` and section anchor, so every grounded claim is traceable to a readable source.
- **Vector search is demoted to optional and future.** If a filtered slice ever exceeds the budget, add a **shortlist** step (vector or BM25) that narrows *within* an already-filtered facet set, then still reason over the shortlisted full documents in context. Implement vectors, if ever, in **pgvector on the existing Cloud SQL** (portable) rather than a proprietary corpus service.

The retrieval interface (`vertex_rag_v211.py` today) is replaced by a `corpus/` package exposing a stable `retrieve(facets, budget) -> ContextSlice` contract, so the mechanism behind it can change without touching callers.

---

## 5. Detailed Design — What "Markdown + Frontmatter" Actually Means

This is the section the rest of the project hangs on. "Frontmatter" = a fenced YAML block at the very top of each markdown file (between `---` delimiters) carrying structured metadata; the markdown body below it is the human-readable source content. The frontmatter is the part the **machine** filters on; the body is the part the **model** reads. Almost everything that was going into the BigQuery `documents` table moves here, unchanged in spirit — it just lives in version control instead of a database.

### 5.1 Folder taxonomy

Folders encode coarse facets so the tree itself is a visible map of the corpus (a curation artifact in its own right). Frontmatter is the source of truth; folders are a convenience and a fallback.

```
corpus/
├── _index.json                      # generated build artifact (do not hand-edit)
├── frameworks/                      # cross-industry authoritative standards
│   ├── nist-csf-2.0.md
│   ├── nist-ir-8286.md
│   └── owasp-top-10-2021.md
├── advisories/                      # time-sensitive, high freshness_sensitivity
│   ├── cisa-aa24-xxx.md
│   └── cccs-ncta-2023-24.md
├── attack/                          # MITRE ATT&CK technique notes
│   └── mitre-t1486-data-encrypted-for-impact.md
├── industry/
│   ├── healthcare/
│   │   └── healthcare-ransomware-profile-ca.md
│   └── finance/
│       └── finance-bec-profile.md
└── original/                        # caffeinatedrisk.com synthesized analysis (the moat)
    └── fair-tef-vulnerability-explained.md
```

### 5.2 The frontmatter schema (complete)

Every field, its type, whether it's required, what consumes it, and why it exists. Controlled-vocabulary fields **must** use the listed values so filtering is deterministic.

#### Identity & provenance

| Field | Type | Req | Consumed by | Purpose / rationale |
|-------|------|-----|-------------|---------------------|
| `id` | string (slug) | ✅ | citations, index, dedup | Stable, human-readable primary key (e.g. `nist-csf-2.0`). Never changes once published; renaming breaks citations. Lowercase, hyphenated. |
| `title` | string | ✅ | display, prompt header | Full human title. |
| `version` | string (semver-ish) | ✅ | change tracking | Version of *this corpus entry*, not the upstream doc. Bump on body edits. |
| `source_url` | URL | ✅ | provenance, re-fetch | Canonical upstream location. Empty only for `original` content. |
| `source_org` | enum | ✅ | trust signalling, filter | `NIST` \| `CISA` \| `CCCS` \| `OWASP` \| `MITRE` \| `FAIR-Institute` \| `CaffeinatedRisk` \| `other`. |
| `source_type` | enum | ✅ | trust weighting | `standards_body` \| `regulator` \| `advisory` \| `academic` \| `vendor` \| `analyst` \| `original_analysis`. |
| `publication_year` | int | ✅ | recency, staleness | Upstream publication year. |
| `retrieved_date` | date | ✅ | audit | When the curator captured/converted it. |
| `content_hash` | string (sha256) | auto | change detection, index | Hash of the body (below frontmatter). Generated by the build step; flags drift and dedups re-ingests. Do not hand-edit. |

#### Classification facets (the filter predicates)

These are what `retrieve()` filters on. Arrays mean "applies to all listed values."

| Field | Type | Req | Controlled vocabulary | Purpose |
|-------|------|-----|-----------------------|---------|
| `industry` | array<enum> | ✅ | `healthcare` \| `finance` \| `government` \| `energy` \| `retail` \| `technology` \| `manufacturing` \| `cross_industry` | Primary filter. Use `cross_industry` for framework docs that apply everywhere (so they're always eligible). |
| `region` | array<enum> | ✅ | `Canada` \| `US` \| `EU` \| `UK` \| `global` | Region filter. `global` is always eligible. SMB customers care about local advisories (CCCS for Canada, CISA for US). |
| `doc_type` | enum | ✅ | `standard` \| `framework` \| `guideline` \| `regulatory` \| `advisory` \| `runbook` \| `incident_report` \| `whitepaper` \| `academic_paper` \| `original_analysis` | Drives doc-type-aware handling and trust weighting. |
| `primary_domain` | enum | ✅ | `Identity` \| `Network` \| `Endpoint` \| `Cloud` \| `DevSecOps` \| `OT/ICS` \| `Physical` \| `Governance/ESRM` | Single best-fit control/risk domain. |
| `secondary_domains` | array<enum> | ⬜ | (same as `primary_domain`) | Additional domains this doc touches. Widens eligibility. |
| `scenario_tags` | array<enum> | ⬜ | `ransomware` \| `BEC` \| `data_exfil` \| `insider_threat` \| `supply_chain` \| `phishing` \| `ddos` \| `web_app` \| `credential_stuffing` \| `cloud_misconfig` \| `third_party` | Maps directly to the threat scenarios questionnaires are built around. The strongest relevance signal for scenario-specific generation. |
| `lifecycle_stage` | array<enum> | ⬜ | `strategy` \| `design` \| `implementation` \| `operations` \| `incident_response` \| `audit` \| `training` | Where in the program lifecycle the doc is useful. |
| `mitre_techniques` | array<string> | ⬜ | `Txxxx` / `Txxxx.xxx` IDs | **Enables deterministic MITRE alignment** without semantic search — exact-match lookup of technique IDs. This is why MITRE alignment is *not* "retrieval territory" in the vector sense. |
| `fair_components` | array<enum> | ⬜ | `TEF` \| `vulnerability` \| `LEF` \| `LM` \| `controls` \| `secondary_loss` | Which FAIR factor(s) this doc informs. Lets the questionnaire generator pull frequency-relevant docs when asking TEF questions, loss-relevant docs for magnitude, etc. |

#### Curation & quality (the moat, made explicit)

| Field | Type | Req | Values / format | Purpose |
|-------|------|-----|-----------------|---------|
| `quality_rating` | int | ✅ | 1–5 (see scale below) | Primary ranking signal. |
| `curator_notes` | string (free text) | ✅ | — | *Why this document matters* in your words. This is the 30-years-of-judgment field that competitors can't clone. Also surfaced in admin/debug views. |
| `authority_basis` | string | ⬜ | — | One line on *why* it's authoritative (e.g. "primary source, US federal standard"). |
| `freshness_sensitivity` | enum | ✅ | `low` \| `medium` \| `high` | How fast the content goes stale. **Drives the web-search gap logic**: `high` (advisories, threat trends) triggers a freshness check + web augmentation; `low` (foundational frameworks) never does. |
| `last_reviewed` | date | ✅ | — | Last curator review. Combined with `freshness_sensitivity` to flag re-review needs. |

`quality_rating` scale (carried over from the BigQuery design, unchanged):
1. Marketing material — vendor-biased, limited depth
2. General guidance — useful but not authoritative
3. Good reference — solid, reputable
4. Authoritative source — industry-recognized, well-researched
5. Gold standard — definitive, primary source

#### Governance & licensing (compliance encoded as data)

This is where the ISACA/ISC2 exclusion decision becomes enforceable rather than a note in someone's head.

Governance has **two independent axes**, because "exclude ISACA/ISC2" was always doing two different jobs:

- **`license_usage`** governs **corpus ingestion** — may this source be written into a `.md` file and *generated from*? This is the original exclusion and the main locus of ToS/copyright exposure.
- **`web_usage`** governs **live web-search results** — when the gap-fill path returns a page from this source, may the model *summarize/paraphrase* it, or only *cite the link*? Web results have no frontmatter, so this is resolved at runtime from a domain/org policy table (see §5.6.1), with the frontmatter field acting as a per-document override.

The legally meaningful line is **reproducing/generating from** a source versus **pointing at** it. Linking to and briefly attributing public content is ordinary citation; copying it into the corpus and generating derivative output is ingestion. A source can therefore be `license_usage: excluded` (never grounded) **and** `web_usage: link_only` (surfaced as a citation, body never injected) at the same time — which is exactly the ISACA/ISC2 posture.

> **Not legal advice.** Public accessibility ≠ permission, and AI-specific ToS clauses change. This schema makes the policy *explicit and enforceable in one place* so a lawyer can review a short, legible rule rather than the whole codebase; it does not substitute for that review.

| Field | Type | Req | Values | Purpose |
|-------|------|-----|--------|---------|
| `license_usage` | enum | ✅ | `ok_to_ground` \| `ok_to_quote` \| `reference_only` \| `excluded` | Governs **corpus use**. `ok_to_ground` = may inject full text for grounding. `ok_to_quote` = grounding + short quotes allowed. `reference_only` = cite the URL, never inject body. `excluded` = must never enter the corpus (build step **fails** if it sees this — see §5.8). ISACA/ISC2 content = `excluded`. |
| `web_usage` | enum | ⬜ (defaults from org policy) | `ok_to_summarize` \| `link_only` \| `blocked` | Governs **live web-search results** from this source. `ok_to_summarize` = may inject result text into the prompt and paraphrase (with citation). `link_only` = return the URL as a citation card **only**; never inject the page body. `blocked` = do not surface at all. If omitted, inherited from the source-org governance table. ISACA/ISC2 = `link_only`. |
| `license_note` | string | ⬜ | — | Free text: the actual ToS clause or reasoning. |
| `attribution_required` | bool | ⬜ | default `false` | If true, citations must name `source_org`. |

#### Retrieval control & tiering

| Field | Type | Req | Values | Purpose |
|-------|------|-----|--------|---------|
| `priority_weight` | float | ⬜ | default `1.0` | Manual boost (`>1`) or suppress (`<1`) in selection ranking, independent of `quality_rating`. Escape hatch for "always include this in ransomware slices." |
| `max_tokens_hint` | int | auto | — | Approx token cost to load this doc's body. Generated at build time; used by the budget-fitting selector so it never has to tokenize at request time. |
| `status` | enum | ✅ | `active` \| `draft` \| `deprecated` | Only `active` is eligible at runtime. |
| `include_in_free_tier` | bool | ✅ | default `true` | Freemium gating. Premium curated content (deep industry profiles, cascade-relevant analysis) → `false`, reserved for the Business tier. |

### 5.3 Body conventions

The body (everything below the closing `---`) is what the model reads, so structure it for both humans and machines:

- **One `# H1`** matching `title`. **`## H2`** for major sections; keep each H2 **self-contained** (a complete thought) so that *if* you ever add a shortlist/embedding step, sections are natural chunk boundaries with no split definitions.
- **Stable anchors.** Citations reference `id#section-slug`; don't rename headings casually.
- **Preserve inline source citations** from the original (page numbers, clause numbers). For `original_analysis`, cite the upstream frameworks you synthesized.
- **Lead each major section with a one-line "grounding takeaway"** in plain language — this is what the questionnaire generator leans on most.
- **No tables-as-images, no scanned figures.** Convert tables to markdown tables; describe essential figures in text. The model can't ground on a raster.
- **Footer provenance block** repeating `source_url`, `retrieved_date`, and `version` so a copied excerpt remains traceable.

### 5.4 A complete worked example

```markdown
---
id: healthcare-ransomware-profile-ca
title: "Ransomware Threat Profile — Canadian Healthcare (SMB)"
version: "1.2.0"
source_url: ""
source_org: CaffeinatedRisk
source_type: original_analysis
publication_year: 2026
retrieved_date: 2026-05-20
content_hash: ""            # filled by build step

industry: [healthcare]
region: [Canada]
doc_type: original_analysis
primary_domain: Endpoint
secondary_domains: [Identity, Governance/ESRM]
scenario_tags: [ransomware, phishing, data_exfil]
lifecycle_stage: [strategy, operations, incident_response]
mitre_techniques: [T1486, T1566, T1078]
fair_components: [TEF, vulnerability, LM]

quality_rating: 4
curator_notes: >
  Synthesized from CCCS NCTA 2023-24 + sector incident reporting. Calibrates
  TEF for small Canadian clinics (3-6 attempts/yr observed) and maps EDR+backup
  maturity to vulnerability %. Use this to seed PERT defaults for healthcare/CA.
authority_basis: "Synthesis of CCCS + public incident data; transparent sourcing."
freshness_sensitivity: high
last_reviewed: 2026-05-20

license_usage: ok_to_ground
web_usage: ok_to_summarize       # omit to inherit from source-org policy
attribution_required: false

priority_weight: 1.3
status: active
include_in_free_tier: true
---

# Ransomware Threat Profile — Canadian Healthcare (SMB)

## Threat Event Frequency (grounding takeaway: ~3–6 attempts/year for small clinics)
Canadian healthcare SMBs face ... (body grounded in CCCS NCTA 2023-24) ...

## Control Effectiveness → Vulnerability Mapping
For organizations with EDR + tested backups + staff training, observed attack
success rates fall to roughly 15% ...

## Loss Magnitude Considerations
Direct costs (recovery, downtime) plus secondary loss (regulatory, reputational) ...

---
*Source: original analysis (caffeinatedrisk.com) • retrieved 2026-05-20 • v1.2.0*
```

### 5.5 The corpus index (`_index.json`)

A **build-time** script (`corpus/build_index.py`) walks `corpus/`, parses every frontmatter block, computes `content_hash` and `max_tokens_hint`, validates against the schema and controlled vocabularies, and emits `_index.json`: an array of frontmatter records **plus body path and token cost, but not the body text**. At request time the selector loads only this index (small, fast) to filter and rank; it reads document bodies from disk/GCS **only for the docs that made the slice**. This is the BigQuery `documents` table's job, done by a JSON file in the repo — diffable, debuggable, no service to provision.

### 5.6 Selection algorithm (the default retrieval path)

```
retrieve(facets, budget=150_000, tier="free"):
  candidates = [d for d in index
                if d.status == "active"
                and d.license_usage != "excluded"      # belt-and-suspenders
                and (tier != "free" or d.include_in_free_tier)
                and matches(d.industry,  facets.industry  or "cross_industry")
                and matches(d.region,    facets.region    or "global")
                and (not facets.scenario or overlaps(d.scenario_tags, facets.scenario))
                and (not facets.domain   or d.primary_domain in facets.domain
                                          or overlaps(d.secondary_domains, facets.domain))]

  # Deterministic boosts, NOT vector similarity:
  score(d) = quality_rating(d) * priority_weight(d)
           + scenario_overlap_bonus(d, facets)
           + mitre_overlap_bonus(d, facets)
           + fair_component_match_bonus(d, facets)

  candidates.sort(by=score, desc)
  slice = greedily add docs until sum(max_tokens_hint) > budget
  return ContextSlice(docs=slice, total_tokens, citations_manifest)
```

Always include `cross_industry` + `global` framework docs (capped) so foundational grounding is present even for thin industry slices. If `candidates` is empty or the top scores are weak, that's the **corpus gap signal** that justifies a web search — recorded in a lightweight retrieval log (one row per request, not per chunk).

### 5.6.1 Runtime governance of web-search results (`web_usage`)

The gap-fill web search returns pages from sources that are **not in the corpus** and carry no frontmatter, so their handling is resolved at runtime from a **shared governance policy** (the same policy the ingest tool uses as its denylist — one source of truth). The policy is keyed by source org and by domain substring; each entry yields a `Governance(license_usage, web_usage)`.

The web-search component classifies each result's domain and branches on `web_usage`:

```
for result in web_search(query):
    match resolve_web_usage(result.url):     # from the shared governance table
        case "ok_to_summarize":
            inject(result.snippet_or_body)   # model may paraphrase, with citation
        case "link_only":
            add_citation_card(result.url)     # surface the link; DO NOT inject body
        case "blocked":
            drop(result)                      # do not surface at all
```

So an ISACA page found during gap-fill becomes a **citation card** ("authoritative guidance exists here: <link>") rather than text the model paraphrases. This preserves the user value of *knowing the source exists* — which actually strengthens the auditability story — without the system generating from prohibited content. The distinction is enforced at the point where results enter the prompt, not left to the model's discretion.

Defaults: unmapped domains fall back to a conservative `reference_only` / `ok_to_summarize`; restricted professional bodies (ISACA, ISC2, and similar) map to `excluded` / `link_only`. Adding a new restricted source = one line in the governance table.

### 5.7 Caching & token budget

Three context blocks per request:

1. **Cached — system + methodology** (FAIR rules, TEF×Vulnerability definitions, output schema). Rarely changes → near-permanent cache hit.
2. **Cached — corpus slice** for this `(industry, region, scenario, tier)` key. Repeat assessments of the same profile reuse it at ~10% input cost.
3. **Uncached — dynamic**: the specific question, the user's prior answers, any fresh web-search results (which are intentionally *not* cached because they're time-sensitive).

Budget math: target ≤ ~150K tokens of corpus context (≈15% of a 1M window), leaving generous headroom for instructions, history, and output, and keeping latency and uncached cost bounded. A healthcare/Canada/ransomware slice is realistically a handful of docs ≈ 30–80K tokens — comfortably inside budget with room for foundational frameworks.

### 5.8 Governance enforcement

Enforcement happens on **both axes**, in one shared module (`app/corpus/schema.py`):

- **Corpus (build time):** `build_index.py` **fails the build** (non-zero exit, no index emitted) if any file has `license_usage: excluded`, has a `source_org` whose policy is grounding-excluded while claiming a grounding license, is missing a required field, or uses an off-vocabulary enum value.
- **Ingest (front door):** the ingest utility refuses (or hard-flags) any source whose org/domain policy is `excluded`, so prohibited content never even becomes a `.md` file.
- **Web search (runtime):** the gap-fill path calls `resolve_web_usage(url)` and downgrades `link_only` sources to citation-only (§5.6.1).

This turns "we don't ingest ISACA/ISC2, but we may link to them" from a memory into three enforced checkpoints sharing one policy table. Add the build-time check to the pre-deploy gate.

---

## 6. Consequences

### Positive
- **Lowest free-tier marginal cost** via cached slices; aligns directly with the freemium model.
- **Auditability**: every grounded claim cites a readable source — the core "not just ChatGPT" differentiator.
- **Vendor-portable**: no proprietary corpus service in the critical path; vectors (if ever) go in pgvector on existing Cloud SQL.
- **Debuggable & git-native**: `grep`, `git diff`, and a JSON index replace a 5-table pipeline.
- **Curation is first-class**: the moat lives in version-controlled frontmatter, not a DB.
- **Compliance enforced in CI** (ISACA/ISC2 exclusion).

### Negative / costs
- **Manual conversion effort**: PDFs → markdown + frontmatter is upfront curator work (mitigated: it's the same metadata the BigQuery design already required, and it's the moat work anyway).
- **No semantic recall for unfaceted queries**: if a relevant doc is mis-tagged, filtering won't find it (mitigated by `cross_industry`/`global` always-eligible base + curator review; revisit if it bites).
- **Selection is only as good as the metadata**: garbage frontmatter → garbage slices. Requires discipline (mitigated by schema validation).

### Neutral
- The well-designed per-chunk feedback loop from the BigQuery design is **shelved, not deleted** — its concepts move to a future lightweight retrieval-log table once there are real users to generate signal.

---

## 7. Revisit Criteria (when to add vectors back)

Add a shortlist step (pgvector/BM25 *within* a filtered facet set) only when **all** of these hold:
1. A common filtered slice routinely exceeds the token budget, **and**
2. Quality degrades because the budget-cut is dropping relevant docs, **and**
3. There are enough real users/logs to measure the improvement.

Until then, adding vectors is paying 2023's premium to solve a problem whose shape has changed. Reconsider GraphRAG only if the premium "cascade" attack-path module needs explicit multi-entity relationship reasoning at scale.

---

## 8. Migration Notes
- Replace `app/vertex_rag_v211.py` with a `corpus/` package exposing `retrieve(facets, budget, tier) -> ContextSlice`. Keep the call sites unchanged by matching the existing interface shape where practical.
- Decommission the Vertex RAG corpus and the unbuilt `tools/bq_rag_ingest` plan; archive `README_bq-rag.md` to `documentation/_archive/` with a pointer to this ADR.
- Convert the sources currently listed in `tools/datasources/rag_cyber_risk_corpus_sources.json` into seed markdown files; that manifest becomes the conversion backlog.
