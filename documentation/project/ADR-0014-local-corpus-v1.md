# ADR-0014 — Local File-Based Corpus (v1): Deterministic Pillar Grounding

**Status:** Accepted (beta) — likelihood pillar wired; magnitude pillar deferred to paid tier
**Supersedes:** the vector-RAG approach (Vertex AI RAG Engine + BigQuery embeddings) for the durable product
**Related:** ADR-0012 (corpus metadata filtering — this ADR is effectively its concrete implementation)
**Date:** 2026-06

---

## 1. Context

OIC needs to ground questionnaire generation in authoritative cyber-risk
reference data so the LLM proposes sector-credible scenarios instead of
plausible-sounding hallucinations. The product thesis is **curation-as-moat**:
the curated corpus is the differentiator, not the retrieval cleverness.

An earlier design used a vector RAG engine (Vertex AI RAG Engine, BigQuery
embedding pipeline) over unstructured text. That was evaluated and **rejected**
for the durable product. The reference data we actually have — Verizon DBIR, IBM
Cost of a Data Breach, NetDiligence Cyber Claims — is not free-form prose. It is
**structured, keyed tables**: indexed by industry/sector, and (for NetDiligence)
by revenue band, with numeric values carrying sample sizes (`n`), maxima, and
reliability flags. Semantic similarity retrieval would paraphrase and
decontextualize exactly the things that make these figures defensible.

## 2. Decision

Use a **deterministic, file-based corpus** loaded into memory at container
startup, queried by exact key lookup (industry, size/band, edition) rather than
embedding similarity.

### 2.1 Co-location of code and data (the "anti-pattern" exception)

Both the corpus **code** (`retrieve.py`, `schema.py`, `pillar_crosswalk.py`,
`pillar_reader.py`) and the **data** (`ref_pillars/` subfolders of curated YAML)
live under one parent package, `corpus/`, mounted at `/app` in the container.

This deliberately co-locates code and data. The "never mix data and compute"
anti-pattern has two meanings, and only the harmless one applies here:

- **The real anti-pattern (avoided):** mixing data and compute *at runtime* —
  letting user-supplied data reach an interpreter, `eval`-ing config, storing
  mutable state in the execution path. We do none of this. YAML is read-only
  reference parsed with `yaml.safe_load`; data never becomes executable.
- **What we actually do (endorsed):** ship a code module next to the read-only
  resources it operates on — the ordinary "package with bundled resources"
  pattern (cf. `importlib.resources`). Co-location keeps the coupling between
  crosswalk keys and data keys *visible* rather than scattered across packages.

**Why this is the right exception:** the corpus is the productized asset. A
self-contained `corpus/` package lets the free/paid split be "mount a leaner vs.
richer `ref_pillars/`" with identical compute above it. The swap unit is the
**data subfolder**, not the code.

### 2.2 Boundary discipline (constraints that keep the exception clean)

- **Dependency points one way:** compute reads data; data never names compute.
  No YAML field may reference a Python symbol, handler, or callable.
- **Read-only mount enforced at the mount**, not by convention — data must never
  become writable/stateful at runtime.
- **Code identical across tiers; only data differs.** If we ever ship different
  *crosswalk logic* per tier, that is the signal we have actually mixed concerns.
  Tiers differ in which data is present; compute tolerates absent rows
  (`coverage: False`, never raises).
- **Data versioned independently of code:** a corpus edition bump (new DBIR
  edition, new sectors) is a different cadence than a retriever bugfix. Each file
  carries `edition` and `review_status` (`[REVIEW]` until human-verified).

### 2.3 Directory layout

```
app/corpus/
├── retrieve.py            # CorpusRetriever — the seam the generator consumes
├── schema.py              # SOURCE_GOVERNANCE / DOMAIN_GOVERNANCE, web_usage rules
├── pillar_crosswalk.py    # OIC-authored industry taxonomy bridge
├── pillar_reader.py       # in-memory loader + slice methods
└── ref_pillars/
    ├── breach_reports/    # DBIR likelihood YAML (Verizon)
    ├── financial/         # NetDiligence + IBM cost YAML (magnitude)
    └── threat_landscape/  # reserved for future pillars
```

(Test fixtures are copies under `tests/fixtures/pillars/`, marked transitory.)

## 3. From string-parsed to parameter-based context construction

A foundational change accompanies this ADR: how grounding reaches the LLM
prompt.

**Before:** grounding was concatenated into a single opaque `rag_context`
string, mixed with whatever else occupied the foundational slot. Adding a second
grounding layer meant string-appending, and the gap analyzer read whatever
landed in that string.

**After:** each context layer is a **named parameter** passed into
`_build_user_message_with_contexts`, ordered and framed independently:

```
[grounding_context]        # cascade card (mode 3), authoritative + fixed
[pillar_likelihood_block]  # NEW named layer — DBIR composition
[web_context]              # recency supplement
[task + JSON schema]
```

Consequences:

- **Precedence is legible in code,** not implied by concatenation order. In
  cascade mode the card stays authoritative; the likelihood block is explicitly
  framed as subordinate ("may inform how often/credible; must NOT alter cascade
  steps").
- **The likelihood block is never an input to gap analysis or web-query
  selection** (the "qualitative framing" rule). Web search behaves identically
  whether grounding is on or off — a clean A/B, and `OIC_PILLARS_ENABLED=0`
  reproduces the web-only fork exactly.
- **Future inputs are just another parameter.** If vector RAG ever returns, it
  enters as a new named layer — it does not reopen the design. (The internal
  `rag_*` symbols in the grounding path were renamed to `grounding_*` for this
  reason; serialized metadata keys and the glitchy coaching routes were left
  untouched as tracked cruft.)

The retriever returns a lightweight `EvidenceDoc` (`content`, `source`,
`relevance_score`) — the shape the generator already consumes — not the unused
richer `ContextSlice`. This envelope is reused by magnitude (§6).

## 4. The taxonomy crosswalk (`pillar_crosswalk.py`)

The three publishers use incompatible industry taxonomies (DBIR = NAICS verticals;
IBM and NetDiligence each their own). DBIR explicitly warns against
cross-referencing its labels to IBM's. So an **OIC-authored crosswalk** is the
single sanctioned bridge — and is labeled as interpretation, not publisher-endorsed.

Key design points:

- **Columns are keyed on `comparable_series`** (`dbir-by-industry`,
  `ibm-cost-by-industry`, `netdiligence-cyber-claims`), not publisher name or
  filename. This is what makes 20–30 documents tractable: all editions of a
  series share one column; a different cut (e.g. `ibm-cost-by-region`)
  self-excludes; a new publisher is one new column, not a rebuild.
- **Values are per-publisher** (`str` or ordered `list[str]` for first-hit
  fallback), so resolution is explicit and a miss is a loud, logged `[]` rather
  than an accidental wrong match.
- **Normalization** lowercases, converts `_`/`-`/`/` to spaces, collapses
  whitespace, then applies an `ALIASES` table (dropdown spellings → canonical).
- **Judgment calls are annotated inline** (`# OIC judgment:`): e.g. NAICS-51
  `information` is shared by canonical technology/media/telecommunications;
  manufacturing → IBM `industrial`; real estate → DBIR's dedicated `real_estate`
  row (NOT construction) and NetDiligence `professional_services`.

Validated end-to-end: all 17 canonical industries (all 13 UI-dropdown values)
resolve to a real DBIR `figures` key; only `pharmaceuticals` (not selectable) is
an intentional miss.

## 5. Slicing facts from the YAML to drive FAIR **likelihood**

This is the core of v1. The reader (`pillar_reader.py`) loads all pillar YAML at
startup (eager), indexes `{comparable_series: {edition: parsed_dict}}`, and
selects the latest edition per series. `slice_likelihood(industry)` produces the
likelihood grounding for **DBIR only**.

### 5.1 Why DBIR maps to likelihood, not magnitude

In FAIR terms the pillars split cleanly:

- **DBIR → Loss Event Frequency / threat *composition*.** It answers "which
  attacks are credible for this sector, and how do they decompose (actors,
  motives, patterns)." It is the *qualitative* side of frequency.
- **IBM + NetDiligence → Loss Magnitude** (deferred — §6).

### 5.2 The honesty guard (the most important rule)

DBIR figures are **incident-corpus counts, not population base rates.** The slice
therefore carries counts and shares **as published** and **never derives a
probability** — no `annual_probability`, no `incidence_rate`, no annualized
percent-chance-of-breach. A test asserts no such key exists. This is why the
likelihood slice carries **no dollar figure** at all: magnitude is a separate
pillar, kept apart deliberately.

### 5.3 What gets sliced

Resolution: `resolve_industry_key(industry, SERIES_VERIZON_DBIR)` → ordered keys
→ first key present in the latest DBIR `figures` wins (DEBUG log on fallback).
The returned dict is **pass-through, not transformed** — fields are copied
verbatim from the YAML (no rename, recompute, round, or reformat), preserving the
"distilled not dumped / figures as the source presents them" discipline:

```
slice_likelihood("Healthcare") →
{
  "pillar": "likelihood",
  "coverage": true,
  "industry_canonical": "healthcare",
  "resolved_key": "healthcare",
  "source": "Verizon DBIR 2025",
  "provenance": { publisher, edition, comparable_series,
                  citation_url, evidence_type, review_status },
  "sector": {                       # the sector row, verbatim
    top_patterns, threat_actors, actor_motives,
    data_compromised, notable, incidents, breaches,
    incidents_small/large, breaches_small/large   # size splits IF present
  },
  "overall": {                      # corpus-wide anchors, ALWAYS present
    top_breach_patterns, leading_initial_vectors,
    ransomware_share_of_breaches, third_party_involvement,
    espionage_motive_share, smb_ransomware_share, median_ransom_paid_usd
  }
}
```

### 5.4 Coverage and graceful degradation

- A sector row that resolves → `coverage: true`, full `sector` block.
- An industry with no DBIR column (pharmaceuticals) → `coverage: false`,
  `resolved_key: null`, **but `overall` anchors still returned** as
  sector-agnostic framing. Never raises.
- `figures: null` / missing sections guarded with `or {}` (hand-curated YAML can
  contain nulls).
- Size splits (`incidents_small`, etc.) are copied verbatim but **not selected
  on** — they become useful only when org-size enters with magnitude.

### 5.5 Rendering and the gap-analyzer boundary

`format_context_for_prompt` renders the slice into a compact LIKELIHOOD block:
provenance header, composition, anchors, and a footer instructing the model to
frame *which* threats are credible, to avoid stating a derived percent chance,
and to cite "Verizon DBIR <edition>", never the YAML. The block is injected as a
named prompt layer and is **excluded from `_analyze_rag_content`** so it cannot
change web-search behavior.

> Known cruft (tracked): `_analyze_rag_content` infers data-freshness by scanning
> years from artifact prose. A cascade card's anchor-incident year (e.g. Black
> Basta 2022) is a historical reference, not data age. Freshness should come from
> structured `edition`/provenance, with cascade years excluded. Latent (only
> bites when a year ≥ current year); the always-on ultra-recent web query is the
> backstop.

### 5.6 UI trust signal (gated)

The generation page shows the grounding source ("Verizon DBIR <edition>") only
when `has_series(SERIES_VERIZON_DBIR)` is true (the flag-derived gate), and shows
a visible amber **"industry grounding unavailable — web research only"** notice
otherwise — so a degraded state is honestly surfaced without code inspection.
The old "IBM Cost of Data Breach — financial impact" claim was **removed** from
the free-tier page (money-adjacent claim not backed by the free tier).

## 6. How this design enables Loss **Magnitude** (next)

The architecture was built so magnitude drops in without reopening anything:

- **Same envelope.** `slice_magnitude(industry, org_size)` returns the same
  `EvidenceDoc` shape; it becomes a second named layer in the prompt builder. No
  generator restructuring.
- **Same crosswalk, more columns.** NetDiligence/IBM keys already resolve through
  `pillar_crosswalk` (`ibm-cost-by-industry`, `netdiligence-cyber-claims`
  columns exist). Magnitude adds the NetDiligence **revenue-band** axis:
  `org_size` → band (nano/micro/small/…), an OIC-authored headcount→revenue
  interpretation, labeled as such.
- **Composition rules already specified.** IBM and NetDiligence **compose, not
  duplicate**: NetDiligence supplies the SME size gradient (`banding: revenue`,
  claims); IBM anchors industry-level impact (`banding: none`, mid-size+
  breaches, not SME-scaled). The slicer must **never blend** IBM with
  NetDiligence, nor SME with large bands — select one primary, present the other
  as labeled context — and must propagate anecdotal flags (`n ≤ 5`).
- **Honesty/legal boundary.** Magnitude is a financial figure the user relies on;
  it is **reserved for the paid tier** (legal caution about being adjacent to the
  money) and excluded from free-tier loss math. The free tier grounds *which
  threats are credible*; the user supplies the dollars.
- **Monte Carlo handoff (open).** Whether the magnitude YAMLs frame the LLM's
  PERT inputs or drive TEF/severity ranges directly is unresolved; lognormal
  (not PERT) is the research-backed choice for loss-magnitude tails.

## 7. Consequences

**Positive:** auditable/deterministic retrieval; no Vertex/embedding dependency;
provenance preserved verbatim; corpus is a swappable productized unit;
flag-gated with a clean web-only fallback; the named-layer prompt structure makes
future inputs additive.

**Negative / accepted:** the crosswalk is hand-curated (that is the moat, but it
is manual); freshness heuristic cruft (§5.5); serialized `rag_*` metadata keys
and coaching-route naming left inconsistent (tracked, not migrated); region is
not a corpus axis (remains web-only).

## 8. Status of components

| Component | State |
|---|---|
| `pillar_crosswalk.py` | built, tested, validated against real DBIR keys |
| `pillar_reader.py` (load/cache, `slice_likelihood`, `has_series`, `latest_edition`) | built, 18 tests passing, eager-load |
| `retrieve.py` likelihood wiring (EvidenceDoc, `enabled`, render) | spec'd (step 3) |
| Generator STEP 1.5 + named-param injection (3 modes) | spec'd (step 3) |
| UI trust signal + degraded gate | spec'd (step 3) |
| `slice_magnitude` (NetDiligence + IBM, bands, never-blend) | deferred (paid tier) |
