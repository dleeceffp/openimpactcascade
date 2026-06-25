# OIC-DESIGN-2026-042: Custom Attack Path Analysis — impact-first generation of candidate attack flows

| Field | Value |
|-------|-------|
| **Status** | `[DRAFT]` — proposes a new feature not yet built. Specifies the elicitation, the generation contract, and the firewall between generation and compression. No code exists yet; treat as a build-sprint proposal. |
| **Date** | 2026-06-13 |
| **Owner** | D. Leece |
| **Primary purpose** | Let an asset owner who *doesn't yet know what to be afraid of* describe their environment in ≤3 plain questions and receive 5 plausible, concrete candidate attack flows — emitted as MITRE Attack Flow (`.afb`) files they can open in the Attack Flow Builder — patterned on publicly observed incidents in their sector. |
| **Relationship to existing work** | This is the **generation** pipeline. It is deliberately kept *separate* from the **compression** pipeline (`OIC-DESIGN-2026-002`). The two share one seam — the `.afb` file — but never merge. See §7. |
| **Companion docs** | `OIC-DESIGN-2026-002 Rev B` (compression; the pyramid rationale this doc inverts on purpose); `OIC-DESIGN-2026-001` (end-to-end brief). |

> **How to read this.** §1–§2 are the *why*: a different user than the triage CIO, and why impact-first/scenario-first elicitation is the only rung that works for a layperson. §3 is the 3-question elicitation. §4–§6 are the generation method and the `.afb` output contract. §7 is the firewall — the single most important design decision in this doc. §8 is guardrails and honest limits. §9 is the feasibility verdict and sprint backlog.

---

## 1. The use case: the asset owner who doesn't know what to be afraid of yet

`OIC-DESIGN-2026-002` serves a CIO with a *known* shortlist of ten risks and four hours to triage them. This document serves the person one step earlier in the funnel — the asset owner who has **a vague asset and a handful of half-formed worries**, and who cannot yet write the shortlist at all.

Their input looks like: *"I need to protect my AD."* That is the whole brief. They may have a couple of injects in mind ("someone clicks a bad link," "a vendor laptop gets in") but no structured sense of how those become a domain-wide problem, and no vocabulary for the outcomes. They are not under-informed because they are careless; they are an application owner, a clinic manager, a plant supervisor — someone whose job is the asset, not the threat landscape.

The job here is **enumeration, not triage**: help them surface a credible, concrete set of "this could happen to you" scenarios so they *have* a shortlist — which they can then take into the triage process the cards support. The output is therefore not a compressed card. It is the opposite: **five concrete, legible, story-shaped attack flows** they can look at and react to — "yes, that's a real worry here," "no, we don't have that," "oh, I never thought of that path."

This is a generation feature, and its success test is recognition: *did we hand the owner five scenarios concrete enough that they can tell us which ones are real in their environment?*

---

## 2. Why impact-first and scenario-first — not CIA, not tactics, not techniques

The compression doc argued cards should live at the **top** of the Pyramid of Pain (tactics and goals — durable, general) because the triage user is reasoning across many risks and needs the volatile detail stripped away. This feature serves the opposite cognitive need, so it sits at the opposite rung — **on purpose**.

Walk the rungs from the layperson's point of view:

- **"Are you worried about availability or integrity?"** — the CIA triad is an *abstraction above* the layperson. It is the analyst's vocabulary, not theirs. Asking it gets blank looks or guesses. **Too abstract.**
- **"Which ATT&CK tactics concern you — lateral movement? credential access?"** — tactics are the durable layer that makes *cards* travel, but they are still an analyst abstraction. A clinic manager does not think in TA-codes. **Too abstract.**
- **"Which techniques — T1566, T1078?"** — technique-level free-association is the unbounded-chasing failure mode (`2026-002 §2`): combinatorial, volatile, and meaningless to a layperson. **Wrong layer, and unbounded.**
- **"Hospitals like yours have had patient systems encrypted and ambulances diverted after a phishing email reached an unpatched workstation."** — a concrete, observed *scenario*, told as a story about someone like them. This is the rung a layperson reasons on. **This is the right level for elicitation.**

So the elicitation and the output both live at the **concrete-scenario** level — low on the pyramid, rich in specifics — because concreteness is what lets a non-expert recognise their own environment. The generated `.afb` flows are technique-level and forensic-shaped (like the existing AFB flows) precisely *because* the user needs concreteness, and because — critically — **these outputs are disposable hypotheses for a human to react to, not authoritative grounding.** Volatile, specific detail is a defect in a card (which is frozen grounding) and a virtue here (where it is an editable prompt). The pyramid rung is chosen to fit the user and the artifact's job, not by habit.

**The unifying picture.** Generation *descends* the pyramid to concreteness for elicitation; compression *ascends* it to generality for triage; a human-and-evidence-gated promotion path connects them (§7). They sit at opposite rungs by design and must never be allowed to merge, because merging would let a concrete hypothesis masquerade as durable grounding.

---

## 3. The elicitation: three questions, no jargon

The user explains their environment in **three questions or fewer**. None mentions CIA, tactics, or techniques. Each maps, *invisibly to the user*, onto one structural anchor of the flow to be generated.

**Q1 — "What are you trying to protect?"** (free text, with autocomplete suggestions)
*Examples:* "my Active Directory," "patient records," "the plant's control system," "our customer database," "our payment system."
→ *Anchors the **terminal** (the bottom of the flow).* The system maps the named asset to its likely observed impact(s) behind the scenes — AD → domain-wide control / encryption / persistence; patient records → data exposure + care disruption; plant control system → process manipulation / safety shutdown — **without making the user name an impact category.** The asset→impact map is curated and maintained by analysts, not asked of the user.

**Q2 — "What kind of organization are you?"** (sector pick-list, free-text fallback)
*Examples:* healthcare provider, municipal utility, manufacturer, professional services, SaaS vendor.
→ *Selects the **observed-scenario corpus** the generation is patterned on (§5).* Adjacent sectors are included automatically so a small or unusual org still gets credible matches (a rural clinic inherits hospital scenarios; a boutique manufacturer inherits industrial ones).

**Q3 — "Which way in worries you most?"** (single- or multi-select from exactly four options)
The entry vector is constrained to a fixed, layperson-legible set:

| Option | Plain framing | Seeds the entry node as… |
|---|---|---|
| **Phishing** | "Someone is tricked into clicking or opening something" | Initial Access via Phishing (T1566) / User Execution |
| **Remote access** | "Something we expose to the internet is used to get in" | External Remote Services / exploit public-facing app / valid accounts (T1133 / T1190 / T1078) |
| **Physical intrusion (office or plant)** | "Someone gets into our premises" | Physical access — hardware/media additions, console access; bridges to ICS entry for plant assets (T1200 / physical) |
| **Over-provisioned AI agent** | "An automated assistant we gave too much access to is misused or manipulated" | Subversion/abuse of an agent holding excessive privilege (e.g. indirect prompt injection → the agent acts with its over-broad scope) |

→ *Anchors the **entry** (the top of the flow).*

**Optional enrichment, never a required question:** a free-text "anything else you already worry about?" lets the user drop in their handful of injects ("a vendor laptop," "an admin's reused password"). This conditions generation without adding a fourth gate. If the user offers nothing, Q1–Q3 are sufficient.

That is the entire intake: **asset (terminal) + sector (pattern corpus) + entry (one of four)**.

---

## 4. What gets generated, and why it's bounded

The app generates **five plausible candidate attack flows**, each a path from the chosen *entry* to the asset's *impact*, patterned on observed sector incidents — each at the detail level of the existing AFB flows (technique-level action nodes, conditions, branch logic, infrastructure, notes).

### Why this is tractable and not unbounded technique-chasing

`2026-002 §2` warned that forward generation explodes combinatorially. This feature escapes that for a structural reason: **both ends are pinned and the middle is exemplar-grounded.**

- The **entry is fixed** to one of four archetypes (top of the flow pinned).
- The **terminal is fixed** by the named asset (bottom of the flow pinned).
- The **middle is patterned on observed incidents** in the sector corpus, not free-associated.

So the generator is not asking "what could an attacker do next?" (open-ended). It is asking "what observed paths connect *this* entry to *this* impact in *this* kind of organisation?" — a **reachability-between-two-posts** problem, instantiated from real exemplars. That is bounded, and it is why the output is plausible rather than fan fiction.

### Why five

Five gives the owner a *spread* to react against: different middles (different escalation routes, different lateral paths, different objectives en route to the same asset) drawn from different observed patterns. The value is in the diversity — the owner learns as much from the path they *reject* as the one they recognise. Five is enough to cover the obvious and the non-obvious without overwhelming a non-expert; it is a default, tunable, not a law.

### Each path carries its lineage

Every generated flow cites, in its `note` and `external_references`, the observed incident(s) it is patterned on (§5). This is the generation analogue of the card's anchor section: even a hypothesis declares *why it is plausible*, distinguishing "patterned on the 2021 incident at a peer org" from pure invention. It gives the owner a credibility signal and somewhere to read more — and it is the first line of the speculation-typing discipline (§8).

---

## 5. Grounding: the observed-scenario corpus

Generation is grounded, not free. Three sources, in priority order:

1. **A curated observed-incident library**, keyed by sector and asset-type — public breach disclosures, IR write-ups, CISA/sector-ISAC advisories, and the existing `.afb` corpus itself. This is the primary pattern source and the thing Q2 selects against. Adjacent-sector entries are included by design.
2. **MITRE ATT&CK** (and ATT&CK for ICS where the asset is a plant/control system) to populate action nodes with legitimate, correctly-tagged techniques rather than invented ones.
3. **Card-grounded web search** (the existing mechanism) to refresh sector prevalence and recent incidents at generation time.

The generator's discipline is **"instantiate observed patterns between the pinned posts,"** which is what keeps the five paths credible. Where the sector corpus is thin (a novel asset, an under-reported sector), the system widens to adjacent sectors and **lowers the stated confidence** rather than inventing detail to fill the gap — see the evidence-typing rule in §8.

---

## 6. Output contract: valid `.afb` for the Attack Flow Builder

Outputs are emitted in the **Attack Flow Builder native format** (`"schema": "attack_flow_v2"`) so the owner can open them in the MITRE reader they may already use, and so they slot into the existing `.afb` → compression seam (§7).

### Object set the generator must emit, per flow

From the schema observed in the existing corpus (e.g. `Tesla_Kubernetes_Breach.afb`):

- **One `flow`** — `name`, `description`, `scope` (set to `"anticipated"`/synthesized, *not* `"incident"` — see §8), `created`, and an `author` block that marks the flow as app-generated. `external_references` carry the patterned-on incident citations (§4).
- **`action` nodes** — the technique steps. Each needs `name`, `tactic_id`, `tactic_ref`, `technique_id`, `technique_ref`, `description`, and the `ttp` `[tactic, technique]` pair. These must be *real* ATT&CK IDs (grounded via source 2), not fabricated.
- **`condition` nodes** — preconditions (e.g. "admin console exposed, no auth"), used as the entry gate and at decision points.
- **`AND_operator` / `OR_operator`** — branch logic where the path genuinely forks or requires conjunction (the Tesla miner sat behind an `AND` of three nodes).
- **`infrastructure` / `asset` / `note`** — attacker infra, the protected asset as a node, and analyst caveats (including the speculation marker).

### The geometry problem (the real engineering lift)

The `.afb` format is a *visual graph*: nodes own `anchors` (a position→instance map), anchors own `latches`, and `dynamic_line` edges connect latches via `handles`. The Builder will not render a file that has the semantic graph but no layout geometry. **The fiddly, deterministic part is the layout, not the content.**

Recommended split, because it also reduces schema-invalidity risk:

1. **The LLM emits semantics only** — a plain `{nodes, edges, branch-logic}` JSON. This is what a language model does reliably.
2. **A deterministic serializer** converts that to valid `.afb`: it lays the spine out vertically (fixed `x`, incrementing `y`), generates anchors at the standard offset pattern seen in the corpus (`0, 30, 60, …`), creates latches/handles, and wires `dynamic_line` objects between them.

This keeps the LLM away from geometry (where it will produce broken files) and away from schema mechanics (where it will drift), and confines correctness to testable code. The serializer is reusable and is the bulk of the build (§9).

> **Note:** if Builder-renderable geometry proves costly, the fallback is to emit the **STIX 2.1 Attack Flow** serialization (semantically complete, no geometry) and treat Builder-native `.afb` as a later enhancement. But the user requirement is explicitly "viewable in their reader," so geometry is in scope.

---

## 7. The firewall: generation and compression never merge

**This is the load-bearing decision.** Generation produces *hypotheses*; compression produces *curated grounding*. They share the `.afb` format but must stay separate pipelines, for the reason established in the prior modeling discussion: `2026-002 §8` makes the *card body* verbatim, un-paraphrasable, "do not alter" grounding. If a synthesized path could flow automatically into that pipeline, a hypothesis would inherit the authority of an observed fact. That is the one thing the architecture must prevent.

```
   ELICITATION (this doc)                       COMPRESSION (2026-002)
   asset + sector + entry                        observed .afb
        │                                              │
        ▼                                              ▼
   generate 5 candidate .afb  ──►  [.afb seam]  ──►  PRUNE/CLUSTER/ABSORB
   (synthesized, scope=anticipated)      │            │
        │                                │            ▼
        ▼                                │        6-link card
   human reacts: keep / reject / edit    │     (observed grounding)
        │                                │
        └── a kept path worth curating ──┘
            ↑ ONLY via: research it into an OBSERVED flow first,
              then compress. Human + evidence gated. NEVER automatic.
```

The seam is the `.afb` file, but crossing it *upward* (hypothesis → grounding) is a deliberate, gated act, never a pipe:

- A generated flow is stamped `scope: anticipated` and carries `evidence_confidence: speculative | reported` per node. It is **not eligible** for `_assemble_card_grounding`.
- For a generated path to become a curated card, an analyst must first **promote it by gathering real evidence** — turning the hypothesis into an observed flow (or confirming a public incident matches it) — and *then* run the normal compression method on the now-observed `.afb`. The promotion is the analyst's evidence work, not a format conversion.
- Until then, generated paths live in a separate store, are labelled synthesized in the UI, and are never web-search-grounded as authoritative archetypes.

Keeping them separate is also why this doc does **not** try to also compress the five paths into cards. Two pipelines, one seam, gated promotion.

---

## 8. Guardrails and known limitations

**Hard rules:**

- **Pinned posts only.** Generation fills the middle between a fixed entry (one of four) and a fixed asset-impact. It does not generate free-floating paths, and it does not chain *synthesised* hops onto synthesised hops (the multi-hop speculation explosion). One bounded path, entry to impact, per flow.
- **Real ATT&CK IDs.** Action nodes use grounded, correctly-tagged techniques. No invented technique IDs.
- **Synthesized ≠ observed, everywhere.** `scope: anticipated`, per-node `evidence_confidence`, UI labelling, separate store, ineligible for card grounding. The firewall (§7) is not optional.
- **Lineage on every path.** Each flow cites the observed incident(s) it is patterned on; where the corpus is thin, confidence drops rather than detail being invented.
- **Geometry is code, not LLM.** Semantics from the model, layout/schema from a deterministic serializer (§6).

**Known limitations (state them so users calibrate):**

- **No validation oracle.** A compressed card is checkable against its source `.afb`; a *generated* path has nothing to check against. Its quality test is "consistent with observed sector patterns," which is weaker than provenance and closer to peer review. This is inherent to generation and is the price of coverage.
- **LLM fluency is the seductive failure mode.** A language model will produce plausible attack narratives whether or not they are realistic — and here it is the *source*, not a compressor of a source, so the artifact risk is higher than in compression. The bounding (pinned posts, exemplar grounding, real IDs, single bounded path) is what holds fluency in check; the human reaction step is the backstop.
- **Concreteness can over-anchor.** Five vivid scenarios can make the owner fixate on exactly those and miss adjacent ones. The UI should frame the five as *examples of a class*, not an exhaustive list, and invite "what else is like this?"
- **The asset→impact map is a curation dependency.** Q1's invisible mapping is only as good as the analyst-maintained table behind it; a missing asset type degrades silently. Needs an explicit "unmapped asset" fallback.
- **The four entry archetypes are a deliberate simplification.** Supply-chain, insider, and lost-device entries are not offered. That is acceptable for the layperson intake but should be a stated scope boundary, revisited as the corpus grows.

---

## 9. Feasibility verdict and sprint backlog

**Verdict: feasible, and well-bounded by construction.** The design avoids the open-ended-generation trap because both ends of every path are pinned and the middle is exemplar-grounded — it is reachability between two posts, not free synthesis. The genuine engineering work is the deterministic `.afb` serializer (geometry), not the semantic generation. The genuine *risk* work is the firewall and the speculation-typing, both of which reuse mechanisms already proposed for compression (`evidence_confidence`). The feature sits cleanly upstream of the existing pipeline and shares its one artifact format.

**Backlog (scoped, with rationale):**

- **F1 — Asset→impact mapping table (analyst-curated) (data, medium).** The spine of Q1. Start with the asset types the corpus already covers (AD, cloud compute, data stores, control systems). *Why:* keeps the user concrete while the system reasons about impact. Includes an unmapped-asset fallback.
- **F2 — Three-question intake UI (app, small).** Asset autocomplete, sector pick-list with adjacency, four-option entry selector, optional enrichment text. *Why:* the whole layperson on-ramp; ≤3 questions is the constraint.
- **F3 — Observed-scenario corpus + sector/adjacency index (data, medium).** Seed from the existing `.afb` corpus + public IR/advisory sources. *Why:* the grounding that makes paths credible (§5).
- **F4 — Semantic generator (LLM) → `{nodes, edges, logic}` (code, medium).** Pinned-post, exemplar-grounded, real-ATT&CK-ID generation of 5 diverse paths with lineage. *Why:* §4–§5. Output is semantics only.
- **F5 — Deterministic `.afb` serializer + layout (code, large — the main lift).** Converts semantics to Builder-renderable `.afb` with computed anchors/latches/lines. Reusable; testable in isolation. *Why:* §6; keeps the LLM out of geometry and schema.
- **F6 — Firewall plumbing (code/schema, medium).** `scope: anticipated`, per-node `evidence_confidence`, separate synthesized store, grounding-ineligibility, UI labelling, and the gated promotion path. *Why:* §7 — non-negotiable. Reuses `evidence_confidence` from `2026-002 §9-R6`.
- **F7 — Reaction UI (app, small).** Keep / reject / edit / "what else is like this?" on each of the five. *Why:* recognition is the success test (§1); also the input that turns enumeration into the triage shortlist.

**Sequencing:** F1+F3 (data) and F5 (serializer) can proceed in parallel and are the long poles. F4 depends on F1/F3. F2+F7 are light front-end work. F6 must land before any generated path is allowed near the card-grounding path — gate the release on it.

---

*This draft specifies a generation feature that meets the layperson where they are — a named asset and a vague worry — and returns five concrete, lineage-carrying candidate attack flows in the Attack Flow Builder format. It deliberately inverts the compression doc's pyramid posture (descending to concreteness for elicitation rather than ascending to generality for triage) and erects a firewall so that synthesized hypotheses can never silently become curated grounding. Build the serializer and the firewall first; everything else is assembly.*
