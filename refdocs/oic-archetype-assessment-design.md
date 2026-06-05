## OIC — Archetype-Driven Assessment: Cross-Industry Cascades + Two-Path Product

**Doc:** OIC-DD-2026-006 · **Status:** draft for review · **Builds on:** OIC-DD-2026-005 (card integration)
**Companion:** OIC-PROC-CARDINT-002 (coding-agent instructions)

---

### 1. The core idea (and why it works)

Three things were being conflated and are now cleanly separated:

- **The archetype** is the cross-industry *cascade structure* — the ≤6 chokepoints any variant of
  this attack must pass through. It is curated, grounded, and **largely industry-independent**.
- **The industry** supplies *context and prevalence* — how common this attack is for that sector,
  what recent incidents look like, sector-specific loss magnitudes, and regulatory drivers.
- **Web search** supplies *recency* — current figures and incidents the static library can't hold.

A hospital, a bank, and a pipeline operator selecting "ransomware via phishing" all assess the
**same** cascade (`oic-ca-001-b`); only the industry context layered on top differs. That is the
design's central claim, and it's correct because the cascade is defined at the altitude of
adversary *objectives*, not techniques — objectives don't change by sector.

The LLM consumes both: the archetype is **authoritative for the cascade and its prerequisites**;
the industry context **only enriches the quantification inputs** (frequency, magnitude, sector
specifics, regulation). The industry context must never rewrite the cascade — see §6 precedence.

---

### 2. Two-path product architecture (both paths already exist)

The two paths are **already built and working** — they are the two cards on the current landing
page. This design does not add a path or a fork; it **strengthens the existing division** by giving
Path A a grounded-cascade mode. No working code is discarded.

- **Path A = the "AI-Generated Questionnaire" card.** Today: industry + region → AI proposes the top
  3–5 threats from MITRE ATT&CK / CISA / current intel. **Change:** after industry + org size, insert
  a `cascade_archetype` selection step. If the user picks an archetype, generation grounds on that
  card + industry context (the credible mode). If they choose "let AI suggest threats," the **current
  behavior runs unchanged** as the fallback. That existing generator becomes the discovery option
  inside Path A, not dead code.
- **Path B = the "Custom Risk Scenario Assessment" card.** Today: free-text scenario → AI researches
  it → tailored questionnaire. This is **already** the directional/open path. **Change:** card copy
  only (position it as the quick, directional option). Backend left as-is for the conference.

```
LANDING (two existing cards)

 PATH A — "AI-Generated Questionnaire"        PATH B — "Custom Risk Scenario"
   industry + org size  (existing)              free-text scenario  (existing)
   │                                            │
   NEW: select cascade_archetype  ── or ──>     web search = scenario + industry context
        "let AI suggest threats" (EXISTING)     (existing /generate-custom backend)
   │            │                               │
   archetype    fallback: current               LLM grounds the scenario
   card =       top-3–5 web/MITRE               (directional, no curated cascade)
   AUTHORITATIVE generation (unchanged)         │
   + industry web context                       │
   │                                            │
   questions from the ≤6 chokepoints            questions from the scenario
                                                              │
   └──────────────────────────┬───────────────────────────────┘
                              ▼   SHARED QUANTIFICATION + REVIEW BACKEND
        user answers questions → existing questionnaire walk
          → vulnerability (exposure) from answers
          → frequency (TEF) from data/industry context        [see §8, outstanding]
          → Monte Carlo (existing PERT/lognormal engine — untouched)
          → REVIEW STAGE:  per mitigation → resources to implement × modeled risk reduction
```

**The division gets stronger with archetypes, not newer.** Before cascades, both cards were
variations on "AI researches a threat and builds a questionnaire" — useful but similar in rigor.
Adding the archetype step gives Path A a **credible, grounded** mode Path B doesn't have, so the two
cards now mean clearly different things: Path A = structured/grounded analysis; Path B =
quick/directional/custom. Path B also remains the honest **fallback** for anything the archetype
library doesn't cover. Label them accordingly in the UI ("grounded analysis" vs "quick directional
view").

---

### 3. How one archetype crosses industries

Most archetypes are cross-industry; a few are domain-specific. Applicability is a **curated**
property of the archetype, not the broken auto-`sectors` field.

| Archetype | Domain | Hospital | Bank | Pipeline / process | Utility / grid |
|-----------|--------|----------|------|--------------------|----------------|
| `oic-ca-001-b` Email-borne ransomware | IT | ✓ | ✓ | ✓ (IT side; may force precautionary OT stop) | ✓ |
| `oic-ca-010` IT→OT pivot, grid ops | OT | – | – | ✓ | ✓ |
| `oic-ca-011` Safety-system (SIS) compromise | OT | – | – | ✓ (if SIS present) | ✓ (if SIS present) |

The ransomware archetype serves every sector; the OT archetypes are scoped to organizations that
*have* the targeted systems. What varies across the ✓ columns is **only the industry context** the
web layer feeds — prevalence, loss magnitude, regulation — not the cascade.

Implication for metadata: replace auto-`sectors` with two curated fields — `domain` (it | ot) and
`industry_relevance` (a curated list or `cross-industry`), plus an optional DBIR-prevalence note
used to rank which archetypes to surface per industry once the library grows past three.

---

### 4. Archetype lifecycle (the moat work)

This is the manual process AI can't shortcut without decades of field judgment — and the reason a
strong 15–20-archetype library built from 40–50 well-researched flows is hard to copy.

1. **Source** — find or author a comprehensive Attack Flow in MITRE's Attack Flow Builder (real
   incident/campaign). This is the explicit tie back to the MITRE model and the provenance anchor.
2. **Generate** — run the pipeline to a full grounded card (the detailed, e.g. 38-step, raw material).
3. **Compress** — abstract to ≤6 chokepoints: cluster by adversary objective, deduplicate, drop
   non-load-bearing color, keep the cut-set chokepoints, re-express each as a prerequisite. *(Lossy;
   human curation; the full flow is archived as the recoverable source — see §7 tradeoff.)*
4. **Tag cross-industry** — assign `domain` and `industry_relevance`; note DBIR prevalence.
5. **Validate** — confirm the chokepoints generalize across the variant space (the cut-set claim);
   expert/peer review of the selection.
6. **Publish** — to the library with the full flow archived (provenance), the compressed card
   (user-facing grounding), and the applicability metadata.

Target: 15–20 archetypes from 40–50 flows. The authoring and the compression judgment are the moat.

---

### 5. From chokepoints to quantification

Each chokepoint prerequisite becomes a plain-language **exposure question** the user (or their IT
contact) can answer — converting "how likely is ransomware?" (unanswerable) into "which of these
conditions hold for you?" (answerable). Answers drive the **vulnerability** side of LEF and feed the
existing vulnerability-management credit and the 5-category ordinal scale. The user never sees a
T-code or estimates a probability.

The **frequency** side (TEF) comes from data/industry context, not the user (§6).

---

### 6. The review stage

For each grounded mitigation on the selected archetype (already lever-classified likelihood/impact):

- **Modeled risk reduction** — re-run the Monte Carlo with that control's effect applied (your
  `/recalculate` likelihood/impact reduction already does this). Grounded.
- **Resources to implement** — cost/effort/time. **Not in the cards or ATT&CK.** New input:
  user-estimated, or a coarse control-cost-tier library (low/med/high effort). *Outstanding (§8).*

Pairing the two yields a prioritized "what's worth doing" view — leverage (the card's
`coverage_count`) and modeled reduction against resource cost. This is the payoff stage that turns
the assessment into a decision.

---

### 7. Compression tradeoff (state it to the engineering audience)

Compression is **abstraction along invariants**, not deletion. Gained: legibility (6 prerequisites
are assessable; 38 techniques aren't), generalization (one card grounds many real attacks),
prioritization (chokepoints → a tractable control set), and durability (objective chokepoints are
stable; technique detail churns — three T1562 sub-techniques were already revoked in 19.1). Lost:
detection value (the 38 techniques *are* the detection content — SOC engineers need the full flow),
sequence/branching fidelity (matters for probability composition), environment-specific specificity,
and tail variants (the modal path is captured; the unusual path isn't). Resolution: it's lossy
compression **with the original archived** — full flow for detection/forensics, card for decisions —
and the chokepoint selection is a **reviewable curator judgment**, not an assertion. The blind spot
(bespoke/innovate-around-the-gate variants) is a high-value-target problem, not an SME problem, so
the abstraction is well-matched to the target market.

---

### 8. Outstanding questions (you were right to be cautious)

1. **Mitigation cost/resource data has no source.** Reduction is modelable; cost is not. Decide:
   user-estimated vs a control-cost-tier library. Blocks the full review stage.
2. **Base-rate / TEF source.** The cascade firms up *exposure*, not *frequency*. Web snippets are a
   weak frequency source; the credible answer is likely a curated base-rate table per
   (archetype × industry × size) — another curation asset.
3. **Path B credibility.** Without a cascade, its numbers are directional. Label it so; don't let it
   masquerade as Path A.
4. **Archetype-to-N selection at scale.** Needs DBIR industry×pattern data to rank which archetypes
   to surface per industry once the library exceeds the demo three.
5. **Curation governance.** Cross-industry applicability and the chokepoint cut-set are human
   judgments — the moat *and* the maintenance/error surface. They need a review discipline.
6. **Web-context precedence.** Rules so industry context enriches quantification inputs without
   overriding the archetype cascade (see §6 of the instructions). Risk of grounding contamination.

---

### 9. Staging

- **Conference / now:** Both cards already work. Enhance **Path A** ("AI-Generated Questionnaire")
  by inserting the archetype-selection step after industry + org size, with the three demo archetypes
  shown and "let AI suggest threats" preserved as the existing fallback; render the cascade; generate
  questions from chokepoints. **Path B** ("Custom Risk Scenario") needs **card-copy changes only** —
  position it as the quick/directional option; backend untouched. Sliders/recalculate/vuln-credit
  untouched; review stage shows modeled reduction only (defer cost).
- **Post-conference:** refine Path B if desired; cost-tier library + full review stage;
  DBIR-prevalence ranking; base-rate table; grow the library to 15–20.

*Nothing in the current working app is replaced — Path A's existing generator becomes the fallback
inside the enhanced flow, and Path B is repositioned, not rebuilt.*
