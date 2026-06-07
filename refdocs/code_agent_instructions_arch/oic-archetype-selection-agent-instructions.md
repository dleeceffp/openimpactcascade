# OIC — Archetype Selection + Two-Path Question Generation + Review (Coding Agent)

**Doc:** OIC-PROC-CARDINT-002 · **Status:** draft · **Implements:** OIC-DD-2026-006
**Builds on:** OIC-PROC-CARDINT-001-B (v1 card grounding). Keep everything flag-gated and additive;
flag off → today's app. Do not touch the Monte Carlo engine, the vulnerability-management credit,
or the questionnaire JSON schema except where this doc explicitly extends metadata.

This is intentionally verbose. Read it fully before writing code.

---

## 0. What we're adding

**Both paths already exist as the two landing-page cards.** Do not build a new fork or a path
chooser. Enhance the existing routes:

- **Path A = the "AI-Generated Questionnaire" card** (existing `/generate`, `generate_questionnaire`).
  Today it takes industry + region + org size and the AI proposes the top 3–5 threats. **The only
  change:** after industry + org size, add a `cascade_archetype` selection step. If an archetype is
  chosen → ground generation on that card + industry context (credible mode). If the user chooses
  "let AI suggest threats" → the **existing generation runs unchanged** (the fallback). The current
  generator is reused, not replaced.
- **Path B = the "Custom Risk Scenario Assessment" card** (existing `/generate-custom`). It is
  **already** the directional/open path. **Change: card copy only** — position it as the quick,
  directional option. Leave the backend logic as-is for the conference (including, for now, the
  existing org_size handling — do not refactor it under deadline).

Both paths already converge on the existing questionnaire walk and Monte Carlo. This doc adds: the
archetype-selection step in Path A, the cascade grounding, the chokepoint→question mapping, and the
shared **review stage**. Nothing working is discarded.

Hard rules carried forward: determinism boundary (card facts verbatim, no invention); industry web
context **enriches quantification inputs only and never overrides the cascade**; Path B stays the
honest fallback for uncovered scenarios; everything behind flags; **do not touch the Monte Carlo
engine, the vulnerability-management credit, the sliders, or the questionnaire JSON schema.**

---

## 1. Config additions

```python
OIC_ARCHETYPE_SELECT   = os.getenv("OIC_ARCHETYPE_SELECT", "0") == "1"   # Path A archetype step
OIC_ARCHETYPE_LIMIT    = int(os.getenv("OIC_ARCHETYPE_LIMIT", "3"))      # max choices shown
OIC_REVIEW_STAGE       = os.getenv("OIC_REVIEW_STAGE", "0") == "1"       # mitigation review
OIC_REVIEW_COST_MODE   = os.getenv("OIC_REVIEW_COST_MODE", "user")       # "user" | "tier" | "off"
```

Reuse `OIC_CARDS_ENABLED`, `OIC_CARDS_DIR`, the three model tiers, and `build_system` caching.

---

## 2. Archetype metadata (curated fields — fix the auto-`sectors` problem)

In `cards/library.py`, read these **curated** frontmatter fields (do not rely on auto-`sectors`):

- `domain`: `it` | `ot`
- `industry_relevance`: `cross-industry` OR a list of sectors (e.g. `[oil_gas, chemical, water]`)
- (optional) `dbir_prevalence`: a hint used for ranking later

Add:

```python
def archetypes_for(self, industry: str, org_size: str, limit: int) -> list[Card]:
    """Path A selection.
    1. KEEP cards whose industry_relevance == 'cross-industry' OR contains `industry`.
    2. If `domain == ot`, keep only when the org plausibly has OT (org_size/industry heuristic or a
       prior intake answer); otherwise IT archetypes only.
    3. RANK: dbir_prevalence for `industry` if present, else cross-industry first, else stable order.
    4. Return top `limit` (default 3). With the demo's 3 cards this returns all three."""
```

No LLM here — deterministic selection from curated metadata. Embedding/DBIR-prevalence ranking is a
later upgrade; for now the curated fields + a small prevalence map are enough.

---

## 3. UI flow change (enhance the existing cards — no new chooser)

The landing page already has the two cards. The user picks a card as today; that *is* the path
choice. Do not add a separate path-selection screen.

**Path A — "AI-Generated Questionnaire" (existing `/generate`):**
1. **Step 1 — Context (existing).** The form collects industry + org size (+ region). Unchanged.
2. **Step 2 — Archetype pick (NEW, gated on `OIC_ARCHETYPE_SELECT`).** After Step 1, show a screen
   listing `archetypes_for(industry, org_size, OIC_ARCHETYPE_LIMIT)` as cards (label, one-line
   scenario, domain badge), **plus an explicit "Let AI suggest threats from current intelligence"
   option** that maps to the existing behavior. Store `selected_archetype_id` (or `none`) in session.
3. **Step 3 — Generate.** If an archetype was chosen → `generate_from_archetype` (§4). If "let AI
   suggest" → the **existing `generate_questionnaire` runs unchanged** (fallback). Either way, the
   existing questionnaire walk renders the result.

**Path B — "Custom Risk Scenario Assessment" (existing `/generate-custom`):**
1. Card copy update only — frame it as the quick/directional option (see §5). The existing free-text
   scenario flow and backend are untouched for the conference.

`AssessmentContext` additions: `path` (`cascade` | `ai_suggest` | `custom`), `selected_archetype_id`,
`industry_context` (cached web context), `card_reduction_options` (already added in v1), `review`
(computed in §6). Include all in `to_dict`/`from_dict`. When `selected_archetype_id` is `none`, the
context behaves exactly as today.

---

## 4. Path A — cascade question generation

In `ai_question_generator.py`, add `generate_from_archetype(industry, region, org_size, archetype_id)`:

```
1. card = card_lib.get(archetype_id)                      # AUTHORITATIVE cascade
2. card_grounding = assemble_card_grounding([card])       # code, verbatim, cached
3. industry_ctx = web_search_industry_context(industry, region, card)   # see §4.1; recency/context only
4. user_msg = build_archetype_user_message(
        card_grounding,        # FIRST — fixed cascade
        industry_ctx,          # SECOND — variable context, explicitly subordinate
        org_size, industry, region)
5. questionnaire = call_model(OIC_MODEL, user_msg, cached_blocks=[card_grounding])
6. metadata: grounding_mode="cascade", selected_archetype_id, selected_card_ids=[card.id],
             card_reduction_options=card_reduction_options([card])
```

### 4.1 Industry context web search (NOT threat discovery)

Reuse the existing intelligent-search machinery, but the queries target **industry context for this
archetype**, not the attack itself (the card already owns the attack):

- "{industry} {card.dbir_pattern} incidents {current_year}"
- "{industry} breach cost / loss magnitude {current_year}"
- "{industry} {region} regulatory drivers" (e.g. HIPAA, PCI, NIS2, TSA pipeline directives)
- prevalence/frequency signals for {industry} + {org_size}

This feeds the **frequency and magnitude** side of quantification. Default web search to the
existing toggle; if off, proceed with the card alone.

### 4.2 Precedence (determinism-adjacent — enforce in the system prompt)

> "The cascade and its prerequisites below are AUTHORITATIVE and fixed. The industry context that
> follows may inform *how often* this occurs in this sector, *how costly* it tends to be, and which
> regulations apply — it must NOT change, add, or remove cascade steps, prerequisites, or
> mitigations. Generate the questionnaire's exposure questions from the cascade's chokepoints; use
> the industry context only to set frequency/magnitude framing and sector relevance."

### 4.3 Questions FROM chokepoints

Each of the ≤6 chokepoints yields one plain-language **exposure question** (the prerequisite, phrased
as a yes/partial/no the user can answer), feeding the **vulnerability** side. The industry context
sets the **frequency** framing. Keep the existing PERT/LEF/LM question shape and JSON schema so the
frontend and Monte Carlo are unchanged. Each generated question records its source chokepoint
(`source_step`) and `selected_archetype_id`.

---

## 5. Path B — Custom Risk Scenario (existing route; minimal change)

This path **already exists** as the "Custom Risk Scenario Assessment" card and the
`/generate-custom` route. It is already the directional/open path. **For the conference, change card
copy only** — do not refactor the backend.

- **Card copy:** reposition it as the quick, directional option. Suggested framing: "Define any
  threat scenario and get a fast, directional questionnaire — best when no grounded attack pattern
  fits. For credible analysis, use the AI-Generated Questionnaire with a cascade archetype." Keep the
  existing tags; optionally add a "Directional" tag.
- **Backend:** leave `/generate-custom` as-is. (The known org_size-string handling can be cleaned up
  post-conference; do not touch it under deadline.)
- **Metadata only:** when this route runs, set `grounding_mode="custom"`, `directional=True` in the
  questionnaire metadata so the UI can show a "quick directional view" label and so the review stage
  (§6) marks its mitigation items `grounded=False`.

No new generation function is required for Path B; it is the route you already have. The
`generate_from_open_question` design above is **deferred** — only build it post-conference if you
decide to replace the custom backend with an ERM-principles grounding. For next week, Path B = the
existing custom flow + reworded card.

---

## 6. Review stage (shared backend)

After the questionnaire is answered and the base FAIR result is computed, build the review:

```python
def build_review(context) -> dict:
    """For each mitigation option:
       - source: card mitigations (Path A, grounded=True) or general (Path B, grounded=False)
       - effect: 'likelihood' | 'impact' | 'both'  (from the card; general for Path B)
       - coverage_count: leverage hint (Path A only)
       - modeled_reduction: re-run the EXISTING Monte Carlo with this control's
         likelihood_reduction/impact_reduction applied (reuse /recalculate logic — do NOT
         modify the engine)
       - resources: per OIC_REVIEW_COST_MODE:
            'user' -> ask the user a coarse effort estimate (low/med/high)
            'tier' -> look up a control-cost-tier table (post-conference asset)
            'off'  -> omit cost; show reduction only
    Return options sorted by (grounded desc, modeled_reduction desc, coverage_count desc)."""
```

Render a "what's worth doing" view: reduction vs resources, grounded items first. **Reuse the
existing recalculate math; do not alter the engine, the sliders, or the vuln credit.** If
`OIC_REVIEW_COST_MODE="off"` (conference default), show modeled reduction and leverage only.

---

## 7. Model usage

| Stage | Model |
|-------|-------|
| Archetype selection | none (deterministic, curated metadata) |
| Industry-context / ERM web search | existing search tooling (no LLM, or FAST to compose queries) |
| Prompt assembly | none (code) |
| Question generation (A and B) | `OIC_MODEL` |
| Review modeling | none (reuses Monte Carlo) |
| Premium deep cascade write-up (later) | `OIC_MODEL_DEEP` |

---

## 8. Data contracts

- **Archetype frontmatter (curated):** `domain`, `industry_relevance`, optional `dbir_prevalence`,
  plus the existing card fields and `mitigations[]`.
- **Questionnaire metadata:** `grounding_mode` (`cascade` | `open`), `path`, `selected_archetype_id`,
  `selected_card_ids[]`, `directional` (Path B), `card_reduction_options`.
- **Question:** `source_step` (chokepoint id, Path A), `selected_archetype_id`.
- **AssessmentContext:** `path`, `selected_archetype_id`, `industry_context`, `review`.
- **Review item:** `id`, `name`, `effect`, `grounded`, `coverage_count?`, `modeled_reduction`,
  `resources?`.

---

## 9. Guardrails

- Determinism boundary: card facts verbatim; LLM invents nothing; assembly has no LLM.
- Precedence: industry/ERM context never alters the cascade (enforced in prompt + by construction —
  the cascade block is assembled separately and marked authoritative).
- Honesty: Path B is labeled directional; Path B review items are `grounded=False`.
- Additivity: every new behavior gated; flags off → current app, including the working sliders,
  vuln credit, Monte Carlo, and schema.
- Cost data is acknowledged as not-yet-grounded; `OIC_REVIEW_COST_MODE="off"` is a valid, honest
  default until the tier library exists.

---

## 10. Acceptance

1. Flags off → byte-for-byte current behavior (both cards, generation, sliders, vuln credit,
   recalculate, chat).
2. Path A archetype mode: industry+size → archetype list (≤ `OIC_ARCHETYPE_LIMIT`) from curated
   metadata, **plus a "let AI suggest threats" option**; pick an archetype → questionnaire grounded
   in that card; `grounding_mode="cascade"`; **same JSON schema**.
3. Path A fallback: choosing "let AI suggest threats" runs the **existing** `generate_questionnaire`
   unchanged (`grounding_mode="ai_suggest"`) — current behavior preserved, no regression.
4. Cross-industry: the ransomware archetype appears for hospital, bank, and pipeline; the OT
   archetypes appear only for OT-capable orgs.
5. Precedence: with web context on, generated cascade steps/prerequisites match the card; industry
   context appears only in frequency/magnitude/regulatory framing, not as new steps.
6. Path B: the existing custom route is unchanged in behavior; card copy reworded; metadata sets
   `grounding_mode="custom"`, `directional=True`; review items `grounded=False`.
7. Review: each option shows modeled reduction from the existing Monte Carlo; `cost_mode="off"`
   omits cost cleanly; sliders/engine/vuln credit untouched.
8. Questions trace to chokepoints (`source_step`) in Path A archetype mode.

---

## 11. Staging (match the deadline)

- **Conference:** `OIC_CARDS_ENABLED=1`, `OIC_ARCHETYPE_SELECT=1` with the three demo archetypes (plus
  the "let AI suggest" fallback), `OIC_REVIEW_STAGE=1` + `OIC_REVIEW_COST_MODE=off`. Path B = the
  existing custom card with reworded copy only. Web search per the existing toggle.
- **Post-conference:** optional Path B backend refinement (ERM grounding); `cost_mode=tier` +
  control-cost-tier library; DBIR-prevalence ranking; base-rate table for TEF; grow library to 15–20.

*Net effort next week: one new archetype-selection screen wired into the existing `/generate` flow
(with the current generator kept as fallback), the cascade grounding + chokepoint questions, the
review stage in reduction-only mode, and a copy edit on the Custom Risk Scenario card. The existing
two-card structure, both generators, the Monte Carlo, sliders, and vuln credit are all preserved.*
