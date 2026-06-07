# OIC Step 3 — Wire DBIR Likelihood Grounding Into All Three Generation Modes

**Artifact:** `oic-pillar-likelihood-wiring-spec`
**Status:** proposed (OIC-authored)
**Scope:** Connect the (tested) DBIR `slice_likelihood` through `retrieve.py`
into `ai_question_generator.py` so all three generation modes receive
sector-grounded **likelihood** context. Likelihood only — no magnitude.
Properly structured (new named context layer, not string concatenation),
flag-gated, with the web-only fork preserved as the off-state.

**Depends on:** `pillar_crosswalk.py`, `pillar_reader.py` (steps 1–2, complete).

---

## 1. What ships

A user generating in any of the three modes gets DBIR sector composition
(top patterns, actors, motives, notable, corpus anchors) injected into the
prompt, cited to "Verizon DBIR <edition>":

- **Mode 1 — AI-generate** (`main.py:397`, `archetype_card=None`): likelihood is
  the foundational grounding. Highest value — keeps scenario selection on
  credible sector threats instead of plausible hallucinations.
- **Mode 2 — custom scenario** (`main.py:514`, `custom_scenario=...`): same
  injection; grounds the single user-defined scenario.
- **Mode 3 — cascade** (`main.py:397`, `archetype_card=<card>`): the card stays
  authoritative; likelihood is appended as a **subordinate** "currently observed
  in your industry" layer that may inform framing but must not alter the cascade.

## 2. The unifying design rule (read first)

**The likelihood block is added prompt context in every mode. It is NEVER an
input to gap analysis or web-query selection.**

Consequences, all intentional:
- Web search behaves **identically to the web-only fork** whether grounding is
  on or off. `_analyze_rag_content` keeps receiving exactly what it receives
  today (the card shim in mode 3; nothing in modes 1/2).
- Grounding on/off is a clean A/B: same web queries, the only delta is the added
  block. (This is the "qualitative framing" decision — likelihood is
  composition, not statistics; it must not suppress or trigger web queries.)
- Because it must not flow into the existing foundational slot (which the gap
  analyzer reads in mode 3), the block goes in a **new named parameter**, not the
  `rag_context`/`grounding_context` string.
- In mode 3 the card remains the web-search driver (card-grounded queries are
  unchanged). The likelihood block is context-only.

## 3. Non-goals (do NOT build here)

- No magnitude. No `slice_magnitude`, no NetDiligence, no IBM, no band logic.
- No change to `_assemble_card_grounding`, `_trim_to_single_threat`, the cascade
  card path's web queries, or the Monte Carlo / simulation code.
- No rename of serialized `questionnaire['metadata']` keys — only additive
  `pillar_*` keys are written (§6c). Existing `rag_*` keys are left untouched.
- No change to the chat / refine-scenario coaching routes in `main.py`
  (`_analyze_rag_content` calls at lines 603/901, `_perform_intelligent_web_search`
  at 617/915). They use `retrieve_coaching_context`, which stays a `[]` stub.
- No route signature changes — both call sites already pass industry/region/size.

## 4. EvidenceDoc contract (`retrieve.py`)

The generator consumes `ctx.content`, `ctx.source`, `ctx.relevance_score`. Add a
lightweight dataclass with exactly those fields (keep the unused `ContextSlice`
for the future `citations_manifest` work, or remove it — implementer's call):

```python
@dataclass
class EvidenceDoc:
    content: str            # the rendered likelihood block (ready for the prompt)
    source: str             # e.g. "Verizon DBIR 2025" — flows into metadata
    relevance_score: float  # 1.0 for a direct sector hit, lower for anchors-only
```

This is the envelope `slice_magnitude` will reuse in step 4, so get it right
here.

## 5. `retrieve.py` changes

**5a. `enabled` property.** Today it checks `corpus/_index.json` / bucket —
neither exists, so the generator's grounding branch never fires. Retie it to the
pillar reader:

```python
@property
def enabled(self) -> bool:
    from corpus.pillar_reader import get_pillar_reader
    from corpus.pillar_crosswalk import SERIES_VERIZON_DBIR
    return get_pillar_reader().has_series(SERIES_VERIZON_DBIR)
```

Add the tiny helper to `PillarReader` (returns whether `_latest(series)` is not
None):

```python
def has_series(self, series: str) -> bool:
    if not self._loaded:
        self.load()
    return self._latest(series) is not None
```

(`get_pillar_reader()` already honors `OIC_PILLARS_ENABLED`; when disabled the
reader loads nothing, so `has_series` → False → `enabled` → False. The flag gate
is automatic.)

**5b. `retrieve_risk_identification_context`.** Replace the TODO stub:

```python
def retrieve_risk_identification_context(self, industry, region,
                                         organization_size=None,
                                         max_results=5, tier="free") -> List[EvidenceDoc]:
    # region & organization_size accepted but unused — likelihood is industry-only.
    if not self.enabled:
        return []
    slice_ = get_pillar_reader().slice_likelihood(industry)
    block = self._render_likelihood_block(slice_)   # see 5c
    score = 1.0 if slice_.get("coverage") else 0.5
    return [EvidenceDoc(content=block, source=slice_.get("source") or "Verizon DBIR",
                        relevance_score=score)]
```

Return a doc even when `coverage` is False — the corpus-wide anchors are useful
sector-agnostic framing; the block says so honestly (5c).

**5c. Rendering — `_render_likelihood_block(slice_)` + `format_context_for_prompt`.**
Render the compact LIKELIHOOD block from the agreed mockup: a header with
publisher/edition provenance, composition (patterns/actors/motives/notable),
the overall anchors, and a footer instruction. Coverage-False renders
"No sector-specific DBIR row for <industry>; corpus-wide anchors only" + anchors.
Example shape:

```
======================================================================
INDUSTRY LIKELIHOOD GROUNDING — <industry>
Source: Verizon DBIR 2025 (incident corpus; counts, not base rates)
======================================================================
Top attack patterns: ...
Threat actors: External 73%, Internal 27% (breaches)
Actor motives: Financial 95%, Espionage 2% (breaches)
Notable: ...
Corpus anchors: ransomware share of breaches 44%; SMB ransomware share 88%;
                median ransom paid $115,000
======================================================================
Use this to frame WHICH threats are credible for this sector. These are
corpus composition figures, not annual probabilities — do NOT state a
derived percent chance of breach. Cite "Verizon DBIR 2025", never the YAML.
======================================================================
```

`format_context_for_prompt(contexts, max_length=None)` joins `doc.content`.
**Keep the `max_length` keyword** — `main.py`'s chat route calls it with
`max_length=3000` (line 943); dropping it breaks that route. Honor it by
truncation or accept-and-ignore for now.

## 6. `ai_question_generator.py` changes

**6a. New STEP 1.5 — fetch likelihood in ALL modes.** Today the retriever is only
called in the `elif self.rag_engine and self.rag_engine.enabled:` branch (modes
1/2). Restructure STEP 1 so:

- The **card** still owns the foundational/authoritative slot and the gap-analysis
  shim, exactly as now (the `if archetype_card is not None:` branch at ~636–644
  is unchanged).
- The old `elif self.rag_engine ...` branch (which put retriever output into
  `grounding_context` and into the gap-analysis contexts) is **removed**. The
  retriever no longer feeds the foundational slot or gap analysis.
- After the card branch, unconditionally (all three modes), fetch the likelihood
  block into a new local:

```python
pillar_likelihood_block = ""
pillar_sources = []
if self.grounding_retriever and self.grounding_retriever.enabled:
    try:
        docs = self.grounding_retriever.retrieve_risk_identification_context(
            industry=industry, region=region, organization_size=organization_size)
        if docs:
            pillar_likelihood_block = self.grounding_retriever.format_context_for_prompt(docs)
            pillar_sources = [{"source": d.source, "relevance": d.relevance_score} for d in docs]
    except Exception as e:
        print(f"⚠️  Pillar likelihood retrieval failed: {e}")  # never fatal
```

STEP 2 (gap analysis, ~678) and STEP 3 (web search) are **unchanged** — they run
over the card shim (mode 3) or empty (modes 1/2), exactly as the fork.

**6b. Message builder — new named parameter.** Add
`pillar_likelihood_block: str = ""` to `_build_user_message_with_contexts`
(signature at ~875). Inject it **between** the foundational block and the web
block, with mode-aware framing:

```
[grounding_context (card, if mode 3)]      # FIRST, authoritative — unchanged
[pillar_likelihood_block]                  # SECOND, the new layer
[web_context]                              # THIRD — unchanged
[task + JSON schema]                       # unchanged
```

Framing for the likelihood block:
- Modes 1/2 (no card): "The above is industry likelihood grounding from Verizon
  DBIR. Prioritise these sector-credible threats; cite the publisher."
- Mode 3 (card present): "The cascade archetype above is AUTHORITATIVE and FIXED.
  The industry likelihood grounding below shows what is currently observed in
  this sector — it may inform how often/credible this is, but must NOT add,
  remove, or alter cascade steps, prerequisites, or mitigations."

Pass `pillar_likelihood_block=pillar_likelihood_block` at the call site (~702).

**6c. Metadata — additive keys only.** Add (do not rename existing keys):

```python
questionnaire['metadata']['pillar_grounding_enabled'] = bool(pillar_likelihood_block)
if pillar_sources:
    questionnaire['metadata']['pillar_sources'] = pillar_sources
```

Leave `grounding_mode`, `rag_grounding_enabled`, `rag_sources`, etc. as-is
(`grounding_mode` already distinguishes cascade vs web_only).

## 7. Rename sub-task — `rag` → `grounding` (narrow, in-scope only)

Rename only the `rag_*` symbols in the **context-loading path of the generator**
that have clear line of sight and **no caller outside this file** — purely local
state, no cross-file coordination, no touching the (separate, glitchy) chat /
refine coaching routes. Specifically:

- `rag_context` → `grounding_context` (the local in `generate_questionnaire` and
  the `_build_user_message_with_contexts` parameter). Fully internal — no
  external caller. This is the symbol you flagged.
- `self.rag_engine` → `self.grounding_retriever` (verified: `main.py` uses its
  own local `rag_engine`, never `ai_generator.rag_engine`).
- `rag_sources_used` → `grounding_sources` (local in `generate_questionnaire`).
- Update the adjacent in-prompt prose ("RAG context" → "grounding context") in
  `_build_user_message_with_contexts`.

**Explicitly leave alone** (entangled with the coaching routes or cross-file —
not in scope, not worth the risk):
- `_analyze_rag_content`, the `rag_analysis` param/local, `rag_contexts`,
  `_perform_intelligent_web_search`'s param — these are gap-analysis / web-search
  machinery reached into by `main.py`'s chat and refine routes.
- The class name, the `get_rag_engine` factory, and every serialized
  `questionnaire['metadata']` key. New code adds `pillar_*` keys (§6c); existing
  `rag_*` keys stay exactly as written.

## 8. Flag-gating / fork parity

`OIC_PILLARS_ENABLED=0` → reader loads nothing → `enabled` False →
`pillar_likelihood_block` empty → message identical to the web-only fork in all
three modes. This is the demo safety net and an acceptance test.

## 9. Generation-page trust signal + degraded-state indicator

The two generation templates carry source claims today. They must (a) be honest
about likelihood-only grounding, (b) show the DBIR promise **only when grounding
is actually active**, and (c) show a plain-language, visually distinct notice when
it is **not** — so the user knows the assessment fell back to web-only without
reading any code.

**9a. Template files (confirmed applicable):**
- `generate.html` — modes 1 (AI-generate) and 3 (cascade).
- `generate_custom.html` — mode 2 (custom scenario).
- The results template is **out of scope** — per-threat `rationale_summary`
  citations already carry resolved provenance there.

**9b. Route context (both GET renders).** Where each template is rendered, pass
two variables. No route signature change — just added `render_template` kwargs.

```python
from corpus.pillar_reader import get_pillar_reader
from corpus.pillar_crosswalk import SERIES_VERIZON_DBIR

reader = get_pillar_reader()
pillar_grounding_enabled = reader.has_series(SERIES_VERIZON_DBIR)  # encodes OIC_PILLARS_ENABLED
dbir_edition = reader.latest_edition(SERIES_VERIZON_DBIR)          # "" when unavailable
# render_template('generate.html', ..., pillar_grounding_enabled=pillar_grounding_enabled, dbir_edition=dbir_edition)
```

Add the accessor to `PillarReader` (public; reuses `_latest`):

```python
def latest_edition(self, series: str) -> str:
    if not self._loaded:
        self.load()
    latest = self._latest(series)
    return latest.get("edition", "") if latest else ""
```

`has_series` already returns False when `OIC_PILLARS_ENABLED=0` (reader loads
nothing), so this single flag drives both the prompt wiring and the UI — they
can never disagree.

**9c. Small CSS for the degraded state** (add once to each template's `<style>`):

```css
.info-box.warning { background: #fff7ed; border-left-color: #f59e0b; }
.info-box.warning strong { color: #b45309; }
```

**9d. `generate.html` — replace the existing "Authoritative Sources Used" info-box:**

```html
<div class="info-box {% if not pillar_grounding_enabled %}warning{% endif %}">
  {% if pillar_grounding_enabled %}
  <strong>📊 How this questionnaire is grounded:</strong>
  <ul>
    <li>Verizon DBIR{% if dbir_edition %} {{ dbir_edition }}{% endif %} — observed attack patterns, actors, and motives for your industry</li>
    <li>MITRE ATT&amp;CK — threat techniques and tactics</li>
    <li>CISA &amp; national CERTs — recent advisories (current web search)</li>
  </ul>
  {% else %}
  <strong>⚠️ Industry grounding unavailable</strong>
  <p style="margin-top:8px; font-size:0.9em;">
    Curated industry breach data could not be loaded. This questionnaire will be
    built from current web research only and may be less specific to your sector.
  </p>
  {% endif %}
</div>
```

Note what was removed and why: the old box claimed *"IBM Cost of Data Breach —
Financial impact data."* The free tier is likelihood-only and uses **no** IBM /
financial data — that claim is the money-adjacent overstatement to delete. DBIR
is reworded from "breach statistics" to "attack patterns" to stay honest
(composition, not derived probability).

**9e. `generate.html` — gate the first loading step** (leave steps 2–4 as-is):

```html
{% if pillar_grounding_enabled %}
<div class="loading-step active" id="step1">🔍 Grounding scenarios in Verizon DBIR{% if dbir_edition %} {{ dbir_edition }}{% endif %} attack patterns for your industry…</div>
{% else %}
<div class="loading-step active" id="step1">🔍 Researching current threat intelligence (web only)…</div>
{% endif %}
```

Only one `id="step1"` ever renders (one branch), so the existing step-animation
JS is unaffected.

**9f. `generate_custom.html` — gate the source line in the "How This Works" box**
(replace the current line 407 `<li>`):

```html
{% if pillar_grounding_enabled %}
<li>AI researches that threat using MITRE ATT&amp;CK and Verizon DBIR{% if dbir_edition %} {{ dbir_edition }}{% endif %} industry attack patterns</li>
{% else %}
<li>AI researches that threat using MITRE ATT&amp;CK and current web research <em>(industry grounding unavailable — results may be less sector-specific)</em></li>
{% endif %}
```

Also add the `warning` class to that info-box div when grounding is off:
`<div class="info-box {% if not pillar_grounding_enabled %}warning{% endif %}">`.

**9g. `generate_custom.html` — gate the first loading step:**

```html
{% if pillar_grounding_enabled %}
<div class="loading-step active" id="step1">🔍 Grounding your scenario in Verizon DBIR{% if dbir_edition %} {{ dbir_edition }}{% endif %} industry patterns…</div>
{% else %}
<div class="loading-step active" id="step1">🔍 Researching scenario-specific threat intelligence (web only)…</div>
{% endif %}
```

**9h. Honesty boundary (state it so the agent doesn't over-reach).** The
generation page is client-side and renders *before* the server resolves which
DBIR sector matched, so this indicator reflects the **subsystem flag only**
(grounding available vs. not) — not per-sector coverage. Per-sector coverage
(anchors-only, e.g. pharmaceuticals) is only knowable post-generation. It is not
reachable through the current dropdown — all 13 selectable industries resolve to
a real DBIR row — so no results-page indicator is needed for the demo. If partial
coverage ever becomes selectable, surface it on the results page via
`metadata['pillar_grounding_enabled']`, not here.

**9i. UI acceptance tests** (Flask test client):

```python
def test_generate_page_shows_dbir_when_grounded(client_with_pillars):
    html = client.get("/generate").data.decode()
    assert "Verizon DBIR" in html
    assert "grounding unavailable" not in html.lower()

def test_generate_page_shows_degraded_notice_when_off(client_pillars_disabled):
    html = client.get("/generate").data.decode()
    assert "grounding unavailable" in html.lower()
    assert "info-box warning" in html        # amber cue present
    assert "IBM Cost of Data Breach" not in html   # old overclaim is gone

def test_custom_page_mirrors_grounding_states(...):
    # same two assertions against /generate_custom
    ...
```

## 10. Acceptance tests

Use a generator with the retriever pointed at `tests/fixtures/pillars/`. Where a
live LLM call is undesirable, assert on the assembled user message via
`_build_user_message_with_contexts` and on the STEP 1.5 wiring directly.

```python
def test_mode1_aigen_injects_likelihood_block():
    # archetype_card=None: block present, names Verizon DBIR, before web context
    ...
def test_mode2_custom_scenario_injects_likelihood_block():
    ...
def test_mode3_cascade_card_first_then_likelihood_subordinate():
    # card block precedes likelihood block; likelihood carries the
    # "must NOT alter the cascade" framing
    ...
def test_likelihood_never_enters_gap_analysis():
    # web queries with grounding ON == web queries with grounding OFF (same set)
    ...
def test_flag_off_reproduces_web_only_message():
    # OIC_PILLARS_ENABLED=0 -> message has no pillar block in any mode
    ...
def test_no_derived_probability_in_block():
    # rendered block contains no "% chance" / annual-probability phrasing
    ...
def test_uncovered_industry_renders_anchors_only_no_crash():
    # e.g. pharmaceuticals -> anchors-only block, coverage flag respected
    ...
def test_evidence_doc_contract():
    # retrieve_risk_identification_context returns objects with
    # .content/.source/.relevance_score
    ...
def test_max_length_kwarg_preserved():
    # format_context_for_prompt(contexts, max_length=3000) does not raise
    ...
def test_metadata_additive_keys_present():
    # pillar_grounding_enabled set; existing rag_* keys untouched
    ...
```

## 11. Open items to confirm

1. **Surfacing `pillar_sources`** — do you want the DBIR provenance shown in the
   result UI for the demo, or kept in metadata only? (No need to inspect the
   existing `rag_*` keys — they are untouched.)
2. **Eager load** — call `get_pillar_reader().load()` in the app factory at
   startup (where `ai_generator` is constructed, `main.py:221`) so first request
   isn't slow; lazy fallback stays.
3. **`relevance_score` for anchors-only** — confirm 0.5 vs 1.0 split is fine, or
   pick values you want surfaced in `pillar_sources`.
