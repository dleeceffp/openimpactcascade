# OIC-DESIGN-2026-045: Multi-Run Attack-Flow Aggregation — convergence and technique-variant analysis

| Field | Value |
|-------|-------|
| **Status** | `[DRAFT]` — proposes a new analysis utility downstream of generation. |
| **Date** | 2026-06-21 |
| **Owner** | D. Leece |
| **Idea origin** | Observed in practice: the same prompt run across Opus / a second model / a third produced three attack flows that **all** independently chose LSASS memory dumping for credential access, but **diverged** on the domain-credential technique (DCSync vs NTDS dumping vs Kerberoasting). The convergence is signal; the divergence is coverage. This utility harvests both. |
| **Relationship** | Consumes STIX bundles produced by the generation pipeline (OIC-DESIGN-2026-042/043). Does NOT change generation. Complements 2026-044 (terminal-anchored multi-path): 2026-044 varies *entry points* deliberately; this varies *sampling* and reads what's stable vs variable across many runs. |

> **One-line thesis:** Run the same scenario many times (same model, different models, or both), then aggregate the resulting STIX bundles into a single view that shows **where the runs agree** (inflection points / chokepoints — likely-real structure) and **where they disagree** (the set of alternative techniques used to achieve the same sub-goal — coverage of the option space).

---

## 1. What this is, precisely

Two distinct outputs from N runs of the same scenario:

1. **Inflection points (convergence).** Steps that appear in most/all runs — e.g. "LSASS dumping appeared in 15/15 runs." High agreement across independent samples is evidence the step is a real structural feature of the attack, not a one-off hallucination. These are the chokepoints a defender should care about most.

2. **Technique variants (divergence at a node).** Where runs agree on the *goal* but differ on the *method* — e.g. "domain credential access was achieved via DCSync (7 runs), NTDS dumping (5 runs), Kerberoasting (3 runs)." This is an automatically-enumerated set of alternative techniques for the same objective: coverage of the attacker's option space that no single run produces.

The unit of analysis is the **(tactic/sub-goal → technique)** mapping across runs. Convergence is measured at the sub-goal level (did runs agree this step is needed?); variant analysis is measured at the technique level (which methods did they use for it?).

---

## 2. This is an established technique (not a novel bet)

Worth stating plainly so the approach is adopted with appropriate confidence and appropriate caution: **this is a domain-specific application of "self-consistency sampling" / "LLM fan-out," a well-studied method.**

- The core method — <cite index="60-1">sample multiple independently-generated reasoning paths and aggregate them, typically by majority vote, to improve reliability</cite> — is exactly what this proposes, applied to attack-flow structure instead of single answers.
- It is already used in threat modeling specifically. AWS's open-source <cite index="51-1">ThreatForest (sample-agentic-attack-tree-generator) does AI-driven attack-tree generation with MITRE ATT&CK integration</cite>, and the ASTRIDE platform uses a <cite index="52-1">consensus-based reasoning mechanism that aggregates threat predictions from multiple independent models, then synthesizes them into a unified threat model, validating, reconciling, and ranking threats</cite>. So "aggregate multiple LLM threat-model runs into one consolidated view" is a recognized pattern.
- The reliability rationale is documented: <cite index="59-1">self-consistency mitigates a class of hallucinations by sampling multiple generations and taking a majority vote; it works where a model produces correct answers more often than not</cite>, and <cite index="67-1">responses that consistently repeat over multiple samples are less likely to be hallucinated</cite>. That is precisely the inference you're making when LSASS shows up in every run.

So the convergence half of this design rests on solid ground. **The divergence half is the more original contribution**: most self-consistency work *discards* the minority answers (it only wants the winning vote), whereas this design treats the minority variants as a deliverable — the coverage of alternative techniques. The literature even notes this is usually thrown away: <cite index="61-1">standard self-consistency relies on plurality voting, which focuses on the most frequent answer while overlooking minority responses — yet those inconsistent minority views often illuminate areas of uncertainty</cite>. For threat modeling, those "areas of uncertainty" are alternative attack paths a defender still needs to cover. Keeping them is the right call here.

---

## 3. Why it makes sense for OIC specifically

- **It directly answers a question single runs cannot:** "is this step fundamental, or did the model just pick it once?" One flow can't tell you; fifteen can.
- **It turns model non-determinism from a bug into a feature.** The stochasticity that makes a single run feel arbitrary becomes the sampling mechanism that maps the option space.
- **Variant enumeration is genuine coverage.** A human analyst writing one attack flow will anchor on the technique they know best (DCSync, say) and miss NTDS/Kerberoasting. Fan-out surfaces all three without prompting for them — it counteracts the single-author anchoring bias.
- **It composes with everything already built.** Inputs are STIX bundles; the model/provider matrix (oic_llm) already lets you fan out across models trivially; the firewall is preserved (this reads observed-shape artifacts and emits observed-shape aggregates — no control logic).
- **It feeds compression.** The convergence chokepoints are exactly the candidates for the compression pipeline's cascade archetypes; this utility is a principled way to *find* which steps deserve a card.

---

## 4. The hard part: failure modes that must be designed around

This is where honesty matters most, because the technique has documented ways of being confidently wrong, and a security tool that aggregates hallucinations into apparent consensus is worse than one that doesn't aggregate at all.

### 4a. Correlated errors — the central risk
Self-consistency assumes independent errors. They often aren't. <cite index="59-1">The wrong answer can win the majority vote when a model makes the same educated guess repeatedly — a hallucination-mitigation failure — and semantic entropy can be low, so it also evades detection.</cite> Concretely: if a model has a training-data bias toward DCSync, it will output DCSync in 15/15 runs *not because DCSync is the real chokepoint but because the model is biased*, and the aggregator will report false high-confidence. **Same-model fan-out is especially vulnerable** — fifteen runs of one model share its blind spots.

**Mitigation:** prefer **heterogeneous fan-out** (multiple different models) over deep same-model sampling for the convergence claim. The literature is explicit: <cite index="59-1">heterogeneous models with different training data and architectures are less likely to share the same shortcomings or make the same educated guesses</cite>, motivating "consortium voting" across models rather than single-model voting. So convergence across *different vendors* is much stronger evidence than convergence across *re-runs of one model*. The design should record which kind of agreement it is and weight them differently.

### 4b. Consensus is not correctness
Agreement measures what the models *consistently believe*, which is a function of their shared training data, not ground truth. Fifteen models agreeing that X is the path means X is the *consensus* path — possibly because X is genuinely central, possibly because X is what's most written about on the internet. For a defender this still has value (the most-documented attack is often the most-used), but the output must never be labeled "the real attack path." It is "the path the models converge on," which is a claim about model belief, not about the adversary.

### 4c. Majority can bury the rare-but-real
A novel or rare technique that only one run surfaces gets a low count and looks like noise — but in security the rare path is often the dangerous one (the blind spot). Pure vote-counting would suppress exactly the signal 2026-044 exists to find. **This is why the divergence output must be kept and surfaced, not filtered to the winner.** A technique appearing in 1/15 runs is not "noise to discard" — it's a candidate blind spot to flag for human review. The asymmetry from 2026-044 applies: dropping a real-but-rare path is the costly error.

### 4d. Normalization is non-trivial
To say "LSASS appeared in 15/15 runs" you must decide two flows' nodes are "the same step." Technique IDs help (T1003.001 = LSASS) but: runs use different node names, different granularity (T1003 vs T1003.001 vs T1003.006 are related but distinct), and different decomposition (one run's single node = another run's two nodes). Naive string-matching will both over-merge and under-merge. The aggregator needs a principled equivalence: match on technique ID at a chosen granularity, with the ATT&CK hierarchy used to relate sub-techniques to parents. This is the main engineering risk.

### 4e. Cost and the position-bias caveat
N runs cost N× tokens. And for long flows, <cite index="64-1">self-consistency can amplify position bias and correlated errors, sometimes decreasing accuracy</cite> — so more runs is not monotonically better. There's a sensible N (literature suggests adaptive stopping once the convergence set stabilizes); 15-20 is reasonable, 100 is waste.

---

## 5. Proposed design

### Inputs
- A set of STIX bundles (≥2; useful at 10-20) from the same scenario. Each already carries `x_oic_context.llm_model` (provenance from the integration work), so the aggregator knows which runs are same-model vs cross-model.

### Process
1. **Extract** (action: technique_id, tactic, name, asset_refs, edges) from each bundle.
2. **Normalize** nodes to a canonical key — technique ID at a configurable granularity (default: sub-technique, with parent-rollup available), using the ATT&CK hierarchy to relate variants. Keep the raw technique alongside the canonical key.
3. **Cluster by sub-goal** — group nodes that achieve the same objective (e.g. "domain credential access") so technique variants for one goal are collected together. Tactic is the first-pass grouping key; refine within tactic by ATT&CK technique relationships.
4. **Compute convergence** per sub-goal: fraction of runs containing *any* technique for that sub-goal → inflection-point score. Record whether agreement is same-model or cross-model (4a).
5. **Enumerate variants** per sub-goal: the distinct techniques used and their run counts → the coverage set. Keep singletons (4c).
6. **Convergence on edges too**, not just nodes: which transitions (A→B) recur. A recurring *sequence* is stronger structural evidence than a recurring node alone.

### Outputs
- **A consensus STIX bundle** (observed-shape) representing the convergent skeleton, with each node annotated by `x_oic_support` = {run_count, total_runs, agreement_type: same_model|cross_model|mixed, variant_techniques: [...]}.
- **A markdown convergence report**: inflection points ranked by support, and for each, the technique-variant table (DCSync 7 / NTDS 5 / Kerberoasting 3). Singletons flagged in a "rare paths — review" section, NOT buried.
- **Optional Mermaid view** where node opacity/label encodes support strength (the viewer already exists; extend the label).

### Explicit non-goals (firewall)
- No `succeeds when` / control prescription — convergence is structural observation; what to do about a chokepoint is compression's job.
- No claim of ground truth — outputs are labeled "model consensus," never "the attack."
- No filtering of rare paths to the winner — divergence is a deliverable.

---

## 6. Same-model vs cross-model: the two modes, and what each is for

Your question was specifically "does it make sense to run the same question on the same model multiple times too?" The answer is **yes, but the two modes measure different things and must be labeled distinctly:**

- **Same-model fan-out (N runs, one model):** measures that model's *internal stability / option space* for the scenario. Useful for "what does Opus think the variants are," and cheap to run. But its convergence is the **weakest** evidence of real-world centrality (4a) — it can launder one model's bias into apparent certainty.
- **Cross-model fan-out (N runs across vendors):** measures *inter-model agreement*, which is much stronger evidence a step is real, because the models have different training and are less likely to share a blind spot. This is the mode to trust for the inflection-point claim.

**Recommended default: mixed.** Fan out across all available models AND take a few samples per model. Then the report can say both "LSASS appeared in all 3 models (cross-model agreement — strong)" and "within Opus, 5/5 runs used LSASS (stable)." The combination is more informative than either alone, and the agreement_type annotation keeps the two kinds of evidence from being confused.

---

## 7. Pros and cons summary

**Pros**
- Established, literature-backed technique (self-consistency / consortium voting) applied to a domain where it fits well.
- Turns model non-determinism into option-space coverage.
- Surfaces inflection points (defensive priorities) and technique variants (coverage) that no single run yields.
- Counteracts single-author anchoring bias.
- Composes with existing oic_llm matrix, STIX artifacts, viewer, and feeds the compression pipeline.
- Cross-model agreement is genuinely stronger evidence than any single flow.

**Cons / risks**
- **Consensus ≠ correctness;** measures model belief (shaped by training data / what's well-documented), not ground truth. Must be labeled as such.
- **Correlated errors** can manufacture false confidence, especially in same-model fan-out — heterogeneous models required for the strong claim.
- **Majority voting can bury rare-but-real paths** — must keep and surface divergence, not filter to the winner.
- **Node-equivalence normalization is hard** (granularity, decomposition, naming) — the main engineering risk; bad normalization corrupts both convergence and variant counts.
- **N× token cost;** more runs not monotonically better (position bias on long flows).
- Risk of **false reassurance**: a step *absent* from all runs is not proven safe — same conditional-negative discipline as 2026-044 applies (absence of a path in the sample ≠ absence of the path).

---

## 8. Recommendation

Build it, as a **post-generation analysis utility** (not part of generation), with these non-negotiables baked in from the start:
1. **Heterogeneous (cross-model) fan-out is the trusted mode**; same-model is offered but labeled as weaker-evidence stability analysis.
2. **Divergence is a first-class output** — rare/singleton techniques are surfaced in a review section, never filtered away.
3. **Every aggregate is labeled "model consensus," never ground truth**, and annotated with agreement_type and run counts.
4. **Normalization granularity is explicit and configurable**, using the ATT&CK hierarchy — and tested, since it's the main correctness risk.
5. **Firewall preserved** — observed-shape in, observed-shape out, no control logic.

It's a strong idea precisely because it does two things at once that map to the two halves of a defender's need: convergence tells them *where to concentrate* (the chokepoints many independent attempts pass through), and divergence tells them *what not to forget* (the alternative methods to the same end). The literature supports the first; keeping the second is OIC's own sensible deviation from textbook self-consistency, and it aligns with the all-hazards, don't-bury-the-rare-path philosophy already established in 2026-044.

---

*Caveat on sources: the convergence/self-consistency claims here are grounded in current literature; the threat-modeling-specific precedents (ThreatForest, ASTRIDE) should be reviewed directly before adopting their specific aggregation choices, as implementations vary and this is a fast-moving area.*
