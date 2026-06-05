# OIC — Card Grounding v1 (Minimal Build)

**Doc:** OIC-PROC-CARDINT-001-B · **Status:** authoritative for next week's build.
**Supersedes** the implementation detail in OIC-PROC-CARDINT-001 and -001-A. Build only what's here.

## Scope (exactly two things)

1. **Card grounding injection** — load the relevant cascade card(s) and inject their content into
   the questionnaire-generation prompt **before** the web search, in the slot the old RAG engine
   occupied. Cards are foundational; web search still fills recency gaps after.
2. **Display panel** — render the selected card's cascade on the questionnaire/results page so it's
   visible to the user.

Everything else stays as-is. Gate both on `OIC_CARDS_ENABLED`; flag off → today's behavior exactly.

## Do NOT touch (working spine)

- The reduction **sliders** and `/recalculate` endpoint.
- The **vulnerability-management credit** (control maturity → vulnerability %).
- The **Monte Carlo** engine.
- The **questionnaire JSON schema** — the generator must emit the same shape it does today.
- **Web search** — keep it and its existing on/off toggle; it's producing good questionnaires.

The safety property: cards only enrich the *grounding text* fed to generation; the output JSON
contract is unchanged, so sliders, vuln credit, and recalculate keep working untouched.

## Determinism boundary

Card facts enter the prompt **verbatim, assembled by code** — the model reasons over them but never
invents a technique, mitigation, statistic, or scenario. No LLM call in the loader, selection, or
assembly.

---

## 1. Card loader (`cards/library.py`)

Parse every `oic-ca-*.card.md` once (cached singleton): split the YAML frontmatter from the body,
keep both. Expose:

```python
class CardLibrary:
    def load(self) -> None: ...
    def get(self, card_id: str) -> Card | None: ...
    def select(self, industry: str, scenario: str | None) -> list[Card]:
        """Simplest selection that covers the demo: match `sectors` to industry
        (plus 'sector-agnostic'), optionally narrow by a scenario keyword against
        label/entry/tags. Return the best 1–2. No LLM, no embeddings."""
```

Selection uses `sectors`, `entry`, `terminal_impact`, `tags`, `label` — **not** the `veris_*` fields
(still manual). If nothing matches, return `[]` and the caller proceeds with web search only
(no corpus exists to fall back to).

## 2. Grounding injection (`ai_question_generator.py`)

Cards take the RAG engine's position in `generate_questionnaire`. The order is the point:

```
STEP 1  CARD GROUNDING (was RAG retrieve)
        cards = self.card_lib.select(industry, scenario)
        card_grounding = assemble_card_grounding(cards)      # code, verbatim
STEP 2  GAP ANALYSIS (unchanged machinery)
        run the existing _analyze_rag_content over the card text so web search
        targets what the cards DON'T cover (recency, regional, current stats)
STEP 3  WEB SEARCH (unchanged) — fills the gaps
STEP 4  BUILD USER MESSAGE — card_grounding FIRST, then web_context
        (mirror today's _build_user_message_with_contexts ordering: foundational first)
STEP 5  Claude call (OIC_MODEL) — same call, same JSON schema out
```

Minimal-effort reuse note: `_analyze_rag_content` iterates `ctx.content`. Wrap each card's text in a
tiny shim (`type("Ctx",(),{"content": card_text})`) so the existing gap→web-search logic runs
unchanged with cards as the grounding base.

`assemble_card_grounding(cards) -> str`: emit each card's label, entry, terminal_impact, the cascade
("Succeeds when …" steps with lever), and the likelihood/impact mitigation split — verbatim, wrapped
in clear delimiters. Put this block in a **cached** content block (it's reused across the session).

System-prompt addendum for the card path: "Grounded cascade scenarios are provided first below; base
the questionnaire's threats and rationales on them. Web results that follow add recent stats/incidents
only. Do not invent threats, techniques, mitigations, or numbers absent from these sources." Keep the
existing rationale/PERT/MITRE/JSON-shape requirements so output is schema-identical.

Record in metadata: `selected_card_ids`, `grounding_mode` (`cards` | `web_only`).

## 3. Display panel (questionnaire + results pages)

The selected card body is presentation-ready markdown. On the questionnaire and results pages, read
`selected_card_ids` from the questionnaire metadata, load the card(s), and render to HTML:

- the **cascade** — the "Succeeds when …" steps with the odds/dwell/spread/size lever, and
- the **Reducing this risk** split (Reduce likelihood / Reduce impact) as **read-only** text.

A markdown→HTML render into a side panel is enough. **Do not** wire these mitigations into the
sliders or `/recalculate` — display only. The sliders already work and stay as they are.

## 4. Config

```python
OIC_CARDS_ENABLED = os.getenv("OIC_CARDS_ENABLED", "0") == "1"
OIC_CARDS_DIR     = os.getenv("OIC_CARDS_DIR", "app/generated")
```

## 5. Acceptance

1. `OIC_CARDS_ENABLED=0` → questionnaire output, sliders, vuln credit, recalculate, and chat are
   identical to today.
2. With the flag on and a matching card, the generated questionnaire's threats/rationales reflect the
   card's cascade; `grounding_mode="cards"`; output JSON validates against the **existing** schema.
3. Card grounding appears **before** web context in the prompt; web search still runs for gaps.
4. No match → `grounding_mode="web_only"`, web-search path runs (no corpus reference).
5. The cascade panel renders on the questionnaire/results page from `selected_card_ids`.
6. `/recalculate`, the sliders, and the vuln-management credit are unchanged and untouched.

## Deferred (post-conference)

Two-stage routing, coverage-menu intake, embeddings, the `card_reduction_options → /recalculate`
wiring, free-text/custom intake, interactive per-question generation, and building the corpus.
