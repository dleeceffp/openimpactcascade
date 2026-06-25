# OIC-DESIGN-2026-002 (Rev B): Cascade Archetype Compression — from MITRE Attack Flow to the Triage-Ready Card

| Field | Value |
|-------|-------|
| **Status** | `[REVIEW]` — Rev B supersedes the 2026-06-11 draft. Describes the existing manual process **and** proposes additions (§9) now entering a build sprint. Verify worked crosswalks against the source `.afb` files before treating the method as canonical; treat §9 as proposed, not yet implemented. |
| **Date** | 2026-06-12 |
| **Owner** | D. Leece |
| **Primary purpose** | Document *how* a full MITRE Attack Flow is compressed into a triage-ready cascade card, *why* that compression is a gain rather than a lossy summary, and *what* to build next so the method scales across a corpus. |
| **Worked examples** | `Black_Basta_Ransomware.afb` → `oic-ca-001-b` (38 nodes → 6 links); `Tesla_Kubernetes_Breach.afb` → `oic-ca-002-a` (9 nodes → 5 links). Crosswalks held as separate audit artifacts. |
| **Companion docs** | `OIC-DESIGN-2026-001` (end-to-end brief); the cards themselves; the two crosswalk files; `ai_question_generator.py` (`_assemble_card_grounding`). |

> **How to read this.** §1–§2 are the *why* — the triage use case the cards serve, and the threat-intelligence principle (the Pyramid of Pain) that makes compression legitimate rather than lossy. They are new in Rev B and are the reasoning a future author most needs. §3–§8 are the working method (largely carried from Rev A, with the BRIDGE step and the schema extended). §9 is the sprint backlog: proposed improvements, each with its rationale and its cost. §10 is the audit discipline.

---

## 1. The use case: ten things keeping a CIO up at night, and four hours to triage them

Everything about this method follows from one scenario, so it is stated first.

A CIO has a shortlist of roughly **ten risks** that could plausibly hurt the organization. A working group — security, IT, a business owner or two — has **four hours** to decide which of those ten to act on first. They are not doing a quantitative risk analysis on any single risk; they are *triaging ten of them* against each other, fast, well enough to allocate the next quarter's attention.

That is the job the cascade card is built for. It is the reason the card is not a MITRE Attack Flow.

A full Attack Flow is a technique-complete forensic graph — 38 nodes for Black Basta, every branch and evasion behaviour recorded for auditability. It is the right artifact for an incident responder reconstructing what happened. It is the *wrong* artifact for a triage room: nobody reads ten 38-node graphs in four hours, and even if they could, the forensic detail buries the few facts the room actually needs — where does this start, what has to go wrong for it to land, and how big is it if it does. **Ten cards have to be legible side by side in an afternoon.** That budget is the binding design constraint.

So compression is not summarisation. It is a deliberate **ascent to the abstraction level at which the triage question is answerable** — and the triage question is always the same:

> **"How would that happen *here*?"**

A card succeeds when someone who was not in the original incident can read it, look at their own environment, and reason honestly about whether the same shape could complete against them — including what a threat actor might do *differently* here that still reaches the same end. A card fails when it reads as a report about somebody else's 2018 outage. The whole method exists to push every card toward the first and away from the second.

This reframes two things people get wrong about the cards:

- **The incident is the footnote; the structure is the product.** The Tesla card is not "the Tesla breach, shortened." It is "the exposed-orchestrator-to-resource-hijacking *pattern*, with the Tesla breach as evidence the pattern is real." The anchor proves the cascade can complete in the wild; it does not define the cascade.
- **Generality is a feature, not imprecision.** A card that says "exposed admin control plane" is *more* useful in the triage room than one that says "Kubernetes dashboard," because the shop in the room might run ECS, Nomad, or a SaaS admin console and still needs to recognise themselves. Specificity that excludes the reader is a defect under this use case, even when it is forensically accurate.

---

## 2. Why moving up the pyramid is legitimate, not lossy (the Bianco principle)

The obvious objection to compression is that it throws away detail. The answer is that it throws away *the volatile detail on purpose*, and keeps the durable detail — and there is a well-established threat-intelligence reason this is the right trade.

David Bianco's **Pyramid of Pain** ranks indicators by how much pain it costs an adversary to change them. At the bottom sit hash values, IP addresses, and domain names — trivial for an attacker to rotate, so chasing them is a treadmill. Higher up sit host and network artifacts, then tools. At the **top sit tactics, techniques, and procedures — the adversary's goals and methods** — which are expensive to change because they reflect *how the actor operates and what they are trying to achieve*. Forcing an adversary to abandon a tactic costs them far more than forcing them to register a new domain.

The cascade card is deliberately built at the **top of the pyramid**. This is the whole justification for the compression:

- **Tools and indicators churn; tactics and goals are sticky.** It is foolish to assume a threat actor will reuse the same loader, the same C2 domain, or the same port when they meet a different environment. They will vary tools and techniques to fit what they find. What they vary far *less* is the tactical shape — get in, gain control, deploy a payload, stay quiet, achieve the objective — and the objective itself. Grounding the archetype at that level means the card stays true across environments and across the attacker's tooling choices. A card pinned to specific indicators would be stale the moment the next variant shipped.
- **This is exactly the credibility-versus-chasing trade-off.** An organisation that triages at the indicator level is always reacting to the last IOC dump and can never tell which threats are *credible against them*. An organisation that triages at the tactic/goal level can ask "do we have the conditions this pattern needs?" and get a durable answer. The card is an instrument for the second posture.
- **"How would that happen here" is a top-of-pyramid question.** It is not "did we see this hash" — it is "could this *method* reach this *goal* in our environment, possibly by a different route." Answering it requires the durable layer and is actively hindered by the volatile one.

### The layering discipline this forces

If the pyramid is why we compress, then the pyramid also dictates *where each kind of detail is allowed to live in the card*. This is the single most important authoring rule in Rev B, because it is what keeps cards general and gives the reviewer a mechanical test:

| Card element | Pyramid level | Holds | Example |
|---|---|---|---|
| **Named link** | top (tactics/goals) | the durable step in the attacker's progression | "Take control of the orchestrator" |
| **`succeeds when` gate** | (defender's controls) | the condition the defender can close | "control plane requires no authentication" |
| **Anchor section only** | bottom/middle (tools, indicators, specific TTP instances) | the volatile, illustrative evidence | "routed the pool through a CDN on a non-standard port" |

**The leakage test (for authors and reviewers):** if a *link name* or a *gate clause* names a specific product, vendor, port, or one incident's tradecraft, then volatile anchor detail has leaked upward into the durable layer, and the card is too narrow for triage. "Kubernetes dashboard" in a link name is a leak; "exposed admin control plane" is the fix. The forensic specifics are not lost — they live in the anchor, doing their proper job of proving the pattern is real.

This also dissolves most of the "N = 1 anchoring" worry. A single-incident anchor (Tesla) is only dangerous if incident-specific tradecraft is load-bearing in the cascade. Under strict layering it is not: the anchor is illustrative, the cascade is generic, and the card describes a *class* (exposed orchestrator → unauthorised workload → resource hijack) that today more often enters via leaked kubeconfigs or exposed kubelet APIs than via the now-deprecated dashboard. The class is what the room reasons over.

---

## 3. What this documents (and what it is *not*)

The cascade-archetype mode ships pre-built attack-pattern cards. Each card is a hand-curated **5–7 link cascade** distilled from a full MITRE Attack Flow. The output expresses the same intrusion as a small number of decisive links plus an odds-vs-size frame and (Rev B) a loss-shape tag.

**This compression is a curation act, not an algorithm**, and Rev B is blunt about the consequence: the judgment is *underdetermined*. Two competent curators can produce two different, individually-correct cards from the same flow. The two worked examples in this very document are the proof — the Tesla flow yielded two valid drafts that differed in how the entry was split into links and in the VERIS entry tag, both passing every audit gate. The §10 checklist verifies a card is internally consistent and faithful to its source; it cannot certify that the chosen compression is *the* compression, because there isn't one. The defences against drift are therefore conventions (§5, §9) and review (§10), not an appeal to a unique right answer.

**LLM assistance is allowed but never authoritative.** An offline Opus pass may propose the cluster/absorb split or a first-draft card; it will also introduce artifacts — inconsistent tag use, leaked specifics, plausible-but-wrong VERIS normalisation. **Correcting those is the reviewer's job and is a known, accepted limitation.** Rev B's response is to give the reviewer *normative targets* (defined tags, the leakage test, a normalisation rule) so correction is a checklist rather than unaided judgment.

**Non-goals.** This doc does not automate the compression and does not claim a unique output. §9 proposes schema and help-text additions; until those land, they are proposals.

---

## 4. The core idea: two-axis reduction + reframe

A full Attack Flow is a *technique-complete forensic graph*. A cascade card is a *decision-complete risk model* — it keeps only the links a defender's controls actually gate, on the one branch that reaches the card's declared terminal, expressed at the top of the pyramid. The compression moves between the two by three reductions and two reframes:

```
   Full Attack Flow (many technique nodes, multiple tactics, branches)
        │
   (A) PRUNE   ── drop branches that don't reach this card's terminal_impact
        │
   (B) CLUSTER ── group remaining techniques into kill-chain phases (the durable links)
        │
   (C) ABSORB  ── demote enabling/evasion/recon/tooling techniques into "succeeds when" gates
        │
   5–7 candidate links
        │
   (D) REFRAME ── each link = plain-language tactic name + "succeeds when" control gate
        │
   (E) BRIDGE  ── tag each link odds (LEF) vs size (LM); set loss_shape; name the pivot
        │
   The triage-ready cascade card
```

(A) is *horizontal* — which branch survives. (B)+(C) are *vertical* — how the surviving spine collapses. (D) and (E) are what make the result a **risk** object, and (per §2) what hold it at the durable layer of the pyramid.

---

## 5. The reduction operations, defined

### (A) PRUNE — keep only the branch that reaches the declared terminal

Every card declares **one** `terminal_impact`. Any branch leading elsewhere is pruned, recorded in a drop list, and reserved for a future card. One flow can spawn several cards, each scoped to one terminal.

Rev B adds a second, distinct pruning rationale surfaced by the Tesla flow. There, the credential→S3 arm was pruned for **two** reasons that the method previously conflated:

- **Terminal mismatch** (a *scoping* decision): the arm serves a confidentiality terminal, not this card's availability terminal.
- **Unevidenced** (an *epistemic* decision): the source flow's own note marks the arm speculative — no evidence the actors ever used the keys.

These are different and should be recorded differently in the drop list, because a future card built on a *speculated* branch is epistemically weaker than one built on a *confirmed* branch. (See §9-R6: an `evidence_confidence` field.)

### (B) CLUSTER — collapse the surviving spine into kill-chain phases

Group surviving techniques by adjacent ATT&CK tactic, because the questionnaire and controls operate at phase granularity. **Split a tactic into two links only where the defender's control lever differs.** Black Basta splits Impact into N5 (recovery inhibition — immutable backups) and N6 (encryption — segmentation/EDR). Tesla splits the single "exposed console" entry fact into "reach the control plane" (network-exposure lever) and "take control" (authentication/RBAC lever). Same rule, both times: distinct lever ⇒ distinct link ⇒ distinct triage question.

### (C) ABSORB — demote enabling techniques into "succeeds when" gates

Most nodes are not links; they are **preconditions**. Defense-evasion, discovery, and tooling techniques rarely advance the chain by themselves — they describe the conditions under which a link completes. Each surviving link carries a `succeeds when` clause naming the control gap, and the absorbed techniques live inside it (and, per §2, the tool-level specifics live only in the anchor). **Promote a technique to a named link only if it has its own distinct control and moves odds or size; otherwise absorb it.**

### (D) REFRAME — link name + control gate, in plain language

Rewrite each cluster from ATT&CK vocabulary into a defender-legible link: a **plain-language tactic name** plus the **`succeeds when` gate**. Per the §2 leakage test, the name and gate must stay at the tactic/control layer — no product names, no incident-specific tradecraft. Write your own prose; reproduce no source-report text.

### (E) BRIDGE — tag odds vs. size, **set the loss shape**, name the pivot

This is the step that makes a cascade a risk object. Rev B extends it.

**Odds vs. size (unchanged).** Each link moves **odds** (likelihood the chain completes → FAIR Loss Event Frequency) or **size** (how large the loss is → FAIR Loss Magnitude). Entry/foothold/escalation/lateral links are odds; impact links are size.

**Loss shape (new — the central Rev B addition).** The odds/size binary is too coarse for losses that accrue over *time*, and the Tesla card exposed it: cryptojacking loss is `rate × time`, so its magnitude is governed less by "how much compute was hijacked" than by "how long it ran before anyone noticed." Rather than add a third FAIR axis to every card (which would tax the many event-shaped cards to fix the few rate-shaped ones), Rev B adds **one frontmatter field**:

| `loss_shape` | Meaning | Magnitude pivot is a… | Canonical example |
|---|---|---|---|
| `event` | loss lands once, at the impact step | **state** question | ransomware — *are backups offline/immutable?* |
| `rate` | loss = rate × time; accrues while undetected | **latency** question | cryptojacking — *would you notice within a day? a quarter?* |

This field is nearly free, and it does real work:

1. It **resolves the `dwell` tag contradiction.** `dwell` is always a *magnitude modifier*; it is simply degenerate (≈ one event) for `event`-shaped cards and dominant for `rate`-shaped ones. The same tag no longer means opposite things in two cards — it means one thing, scaled by `loss_shape`.
2. It **tells the facilitator which question to push** at the impact links — a state question for event-shaped risks, a detection-latency question for rate-shaped ones.
3. It is **where the application help section earns its keep** (§9-R1): the help text guides the room on eliciting the time term for rate-shaped cards (acceptable dwell, realistic detection latency, monthly run-rate of the hijacked resource) so the magnitude estimate is grounded rather than guessed.

**Name the single pivot.** Exactly one link is the dominant magnitude lever: N5 (recovery inhibition) for Black Basta; N4 (stay unnoticed) for Tesla, *because* it is rate-shaped and dwell governs the loss.

---

## 6. Worked evidence (two crosswalks)

The full provenance crosswalks live as separate audit artifacts — one per card — because they are reviewer instruments, not card content. Each maps every source node to its disposition (named / absorbed / pruned), keeps the drop list, and runs the §10 checklist.

- **Black Basta** (`oic-ca-001-b`): 38 nodes, 12 tactics → 6 links; 4 pruned (the double-extortion / data-leak arm). The biggest absorber is N2 (foothold), which swallows the 13-node defense-evasion/C2 mass into one "stays quiet" link — the signal that defense-evasion is almost always *condition*, not *link*. `loss_shape: event`.
- **Tesla** (`oic-ca-002-a`): 9 nodes → 5 links; 3 pruned (the speculative credential→S3 arm). Demonstrates the lever-split rule on entry, the two-rationale prune, and `loss_shape: rate` with the dwell-as-pivot consequence.

The two examples deliberately bracket the method: a large flow that tests *absorption* and a small flow that tests *splitting* and *loss shape*. A future author should read both crosswalks before authoring card three.

---

## 7. The repeatable method (procedure for the next card)

Apply in order; each step has an explicit, checkable output.

1. **Declare the terminal first.** Write `terminal_impact` + `veris_terminal` before touching nodes — it is the pruning oracle. *Output: frontmatter terminal.*
2. **Set `loss_shape`.** Decide `event` vs `rate` now, because it determines what the impact links must ask. *Output: frontmatter `loss_shape`.*
3. **Walk the flow top-to-bottom; tag each node's tactic.** *Output: ordered tactic list.*
4. **PRUNE off-terminal branches**, recording for each drop *both* whether it is a terminal mismatch and whether it is unevidenced. *Output: surviving spine + justified drop list.*
5. **CLUSTER into 5–7 kill-chain phases**, splitting a tactic only where the defender's control lever differs. *Output: candidate links.*
6. **ABSORB.** Promote to a named link only techniques with a distinct control that move odds or size; fold the rest into one `succeeds when` gate. *Output: links, each with one gate.*
7. **REFRAME** into plain defender language **at the top of the pyramid** — run the leakage test on every link name and gate; push any product/port/tradecraft down into the anchor. *Output: link names + gates, leakage-clean.*
8. **BRIDGE.** Tag each link odds/size; confirm the `loss_shape`; identify the single magnitude pivot. *Output: tags + pivot + "odds vs size" paragraph.*
9. **Record adjacent terminals.** List the pruned arms as `adjacent_terminals` so the triage room sees "what else this same entry could do." *Output: frontmatter `adjacent_terminals`.*
10. **ANCHOR.** Keep the real incident, the ATT&CK provenance, and the control candidates — the traceability that distinguishes the card from generic LLM output, and the proper home for all volatile detail. *Output: anchor + "reducing this risk".*
11. **Stamp `[REVIEW]`** until verified against the source flow (§10).

**Guardrails (hard rules):**
- One card = **one terminal *and* one entry.** Multiple terminals → multiple cards. Genuine alternate *entries* (an OR at the top of the flow) → also multiple cards, never branch logic inside the chain (see §9-R4). A card's linear spine must be a claim the source actually supports.
- Target **5–7 links**, set by the number of *distinct defender levers*, not by a fixed count. >7 ⇒ under-absorbed; <5 ⇒ check for over-pruning, but accept it when the intrusion is genuinely short (Tesla's five are honest, not a symptom).
- A technique is a **named link only if it has its own control and moves odds or size** — otherwise it is a gate condition.
- **No volatile detail above the anchor.** Link names and gates stay at tactic/control level (the leakage test).
- **Never reproduce** source-report prose or tables; distilled, not dumped.
- **Keep the drop list.** A pruned branch is an auditable scoping decision, not a deletion.

---

## 8. How the compressed card is consumed (why the form matters)

The card's reduced body is treated as **authoritative, un-paraphrasable grounding**. In `ai_question_generator.py`, `_assemble_card_grounding()` wraps the frontmatter and body into the prompt under *"AUTHORITATIVE CASCADE ARCHETYPE (grounding base — do not alter)"*, entering **verbatim — no LLM, no paraphrase**. Two consequences:

1. **The card must be presentation-ready and leakage-clean at authoring time**, because nothing downstream re-summarises or re-generalises it. The form *is* the artifact the model reasons over and the room sees. A forensic dump would blow the grounding budget, bury the levers, and hand the model dozens of chances to wander.
2. **The `succeeds when` gates become the questionnaire scaffold.** Each gate is a likelihood question; the odds/size tags and `loss_shape` route the answers toward LEF vs LM (and, for rate-shaped cards, toward the duration term) for the Monte Carlo layer.

**A correlation caveat for the quant layer (new).** Gates are written as independent on/off conditions, but the underlying control failures are often *correlated* — Tesla's "dashboard is public" and "dashboard is unauthenticated" were one misconfiguration, and Black Basta's flat-network condition silently underwrites three different links. If the Monte Carlo layer multiplies correlated gate answers as independent probabilities, it will **overstate** the safety bought by a partial fix. This is a bridge-layer concern, not a card-authoring one, but it must be stated where the quant layer is specified so inputs are not naively treated as independent.

---

## 9. Sprint backlog — recommended improvements, with reasoning

These are the Rev B proposals now entering build. Each is scoped as **doc**, **schema**, or **code/app**, with its rationale and cost, so the sprint can sequence them.

**R1 — Application help section for `loss_shape` (app, small).**
*Why:* the field only pays off if the room knows how to use it. For `rate`-shaped cards the magnitude estimate needs a *time term* — acceptable dwell, realistic detection latency, run-rate of the hijacked resource — that an event-shaped card never asks for. *What:* help text that, on a rate-shaped card, prompts the facilitator to elicit detection latency and run-rate and shows the `rate × time` framing. *Cost:* copy + a conditional render on `loss_shape`.

**R2 — `loss_shape` frontmatter field + back-fill (schema, small).**
*Why:* §5-E. Resolves the `dwell` ambiguity structurally and routes the right impact question. *What:* add `loss_shape: event | rate`; back-fill the two existing cards (`001-b` = event, `002-a` = rate). *Cost:* one enum, two edits.

**R3 — `adjacent_terminals` field (schema + app, small).**
*Why:* "how would that happen here" naturally extends to "what *else* would they do from the same foothold." The pruned arms already hold that answer but are buried in reviewer scope-notes. Surfacing them is also the cheap, honest response to cross-card correlation: we don't formally model shared gates, we let the room *notice* them. *What:* `adjacent_terminals: [<card-or-terminal>, …]`, rendered as a prompt in the card view. *Cost:* one list field + a render.

**R4 — Decide branch logic = card split (doc, none — decision only).**
*Why:* the linear card cannot express the source's AND/OR structure (Tesla's miner is gated behind an AND of three nodes; the server stand-up is parallel, not sequential). Harmless there, but the first flow with two genuine alternate *entries* will force a choice. *Decision:* one card = one terminal **and** one entry; branch logic becomes multiple cards, mirroring the multi-terminal rule. *Cost:* codify the guardrail (done in §7); no schema change.

**R5 — Reviewer normative targets to absorb LLM artifacts (doc, small).**
*Why:* LLM-assisted drafts will keep producing inconsistent tags and leaked specifics; correction is the reviewer's accepted job, and a checklist beats unaided judgment. *What:* a one-page reviewer checklist extracted from §2/§5/§10 — the leakage test, the defined tag meanings, the VERIS normalisation rule (R7), the `loss_shape`/pivot consistency check. *Cost:* documentation.

**R6 — `evidence_confidence` on dropped (and named) branches (schema, small).**
*Why:* §5-A. A card built from a *confirmed* branch and one built from a *speculated* branch (a future `oic-ca-002-b` from Tesla's unevidenced arm) look identical to the grounding consumer today. *What:* a `confidence: observed | reported | speculative` marker on branches in the crosswalk, and surfaced on any card built from a non-observed branch. *Cost:* one enum + reviewer habit.

**R7 — VERIS normalisation rule (doc, tiny).**
*Why:* `exploit_misconfig` vs `Exploit misconfig` vs `exploit-misconfig` will drift across authors and across LLM drafts. *What:* state one canonical form (e.g. lower-snake of the VERIS label) in this doc and validate it. *Cost:* one sentence + an optional lint.

**R8 — Shared-gate review exercise (app/process, small).**
*Why:* the single highest-value output of a four-hour session is often *not* the per-card scores but the observation that several high-scored cards share one entry gate — one control, many cascades closed. The gate-clause format makes gates comparable across cards in a way raw flows never were; we should harvest that. *What:* a closing step/report that lists gates appearing on more than one card the room scored high. *Cost:* a simple aggregation over gate text.

**R9 — Re-review cadence / staleness (process, small).**
*Why:* §8 freezes the card as verbatim grounding, so technique drift, control evolution, and even VERIS schema additions (the `Hijacking` variety post-dates some cards) accumulate invisibly. `[REVIEW]` governs initial correctness, nothing governs continued correctness. *What:* a `last_reviewed` date and a periodic re-check; strict layering (§2) already minimises how often drift actually bites, since the durable layer ages slowly. *Cost:* one date field + a calendar.

**Sequencing suggestion:** R2 + R3 + R7 are schema and should land together early (they touch the corpus and the index). R1 follows R2. R5 + R4 are documentation and can land any time. R6, R8, R9 are higher-value-but-optional and can trail.

---

## 10. Review & audit discipline

Because the compression is judgment, the audit trail is the safeguard. A card stays `[REVIEW]` until:

- **Provenance.** Every named link traces to ≥1 real node in the source `.afb`; the crosswalk is regenerated for *this* card (not carried over from a prior draft); the drop list names every pruned branch with the terminal it served and (Rev B) its evidence confidence. Any link that traces to a non-action object (e.g. a `condition`) is flagged as a deliberate exception, not silently passed.
- **Terminal integrity.** No surviving link advances a terminal other than the declared one.
- **Absorb sanity.** No named link lacks a distinct control; no `succeeds when` gate is empty.
- **Layering / leakage (Rev B).** No link name or gate names a product, port, or one incident's tradecraft; all volatile detail sits in the anchor.
- **Odds/size + loss shape (Rev B).** Every link carries a tag; `loss_shape` is set; exactly one magnitude pivot is named and is consistent with the loss shape (dwell-pivot ⇒ rate; state-pivot ⇒ event).
- **Source-defect honesty (Rev B).** Defects in the source flow (mistagged tactics, duplicated descriptions) are *recorded* in the crosswalk, not silently corrected — otherwise "traces to source" quietly does repair work.
- **No reproduction.** Body prose is the curator's own; no copied source passages.

**Known, accepted limitations (not blockers, but stated so reviewers calibrate):**
- The compression is underdetermined — a reviewer confirms a card is *sound*, not that it is *unique*.
- LLM-assisted drafts introduce artifacts; the reviewer corrects them against the §9-R5 checklist.
- Cards rot under verbatim grounding; §9-R9 is the mitigation.

---

*Rev B freezes the use case and the pyramid rationale as the reasoning behind the method, extends the BRIDGE step and schema with `loss_shape` (and proposes `adjacent_terminals` / `evidence_confidence`), and opens a sprint backlog. It changes the schema as proposed in §9 and otherwise describes the existing, working process. Verify the two crosswalks against their source `.afb` files and lift `[REVIEW]` once §9's schema items land and the worked examples are re-validated.*
