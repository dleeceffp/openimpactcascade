# OIC Cascade Card Generator — Design & Reference

A deterministic pipeline that converts CTID **Attack Flow** files (`*.afb`) into draft OIC
grounding cards (`oic-ca-*.card.md`). It implements the build spec at
`refdocs/oic-cascade-card-generator.instructions.md` (Stages A–D) and the mitigation
addendum at `refdocs/oic-cardgen-addendum-mitigations.md` (Addendum B).

This document doubles as the design record: it explains not only *what* each module does,
but *why* the rendering of the "Succeeds when …" clause evolved through three variants
(base, `-a`, `-b`), and how the latest version (`-b`) grounds, prunes, and de-duplicates
its prose so a non-specialist can read a cascade without decoding MITRE shorthand.

---

## 1. Design principles

The generator is built around one hard rule and a few supporting ones.

- **Determinism boundary (the hard rule).** All structured facts — step order,
  technique ids and names, tactics, VERIS strings, DBIR pattern, lever classification,
  mitigations, and every value in card frontmatter — are produced by **code** against
  **pinned local data**. The optional LLM step only rewrites *body prose*; it is never
  allowed to invent a technique, VERIS value, actor, sector, mitigation, or step. This
  keeps cards reproducible and auditable: re-running the generator on the same inputs
  yields the same facts.
- **Translate, don't cite.** Where the cards must explain security controls to a lay
  reader, the pipeline translates MITRE mitigation codes into plain-language phrases from
  a static, hand-authored table — it does not emit raw `M####` identifiers into the body
  prose.
- **Flag, don't guess.** Anywhere the code makes a judgement that a human should confirm
  (archetype label, dedupe, generalization scope, the magnitude/"size" step, ambiguous
  mappings, inferred techniques, redundant weaknesses), it inserts a literal `[REVIEW]`
  token in the card and a line in the build report rather than silently committing.
- **Additive variants.** The base pipeline is never mutated to add a feature; new
  rendering styles are added as parallel `_a` / `_b` modules so older outputs remain
  reproducible and the variants can be compared side by side.

---

## 2. Pipeline architecture (Stages A–D)

| Stage | Responsibility | Modules |
|-------|----------------|---------|
| **A — Parse** (code) | Reconstruct the directed cascade graph from the native `.afb` file: ordered steps, entry/terminal nodes, branch (`OR`/condition) markers, assets. | `afb.py` |
| **B — Enrich & map** (code) | Resolve each step's technique against pinned ATT&CK; attach tactics, VERIS candidates, DBIR pattern; classify the lever; (in `-a`/`-b`) attach grounded mitigations and prerequisites. Produces an `Extract` / `ExtractA`. | `enrich.py`, `enrich_a.py`, `enrich_b.py`, `resources.py`, `mitigations.py`, `control_language.py` |
| **C — Draft** | Emit a deterministic scaffold card **and** an LLM prompt (system + user) carrying only the grounded facts. | `render.py`, `render_a.py`, `render_b.py` |
| **D — Validate** (code) | Run the spec checklist (VERIS enum membership, DBIR set membership, lever legality, provenance completeness, presence of a `size` step), returning pass/fail plus a build report enumerating every `[REVIEW]`. | `validate.py` |

Supporting modules:

- **`config.py`** — pinned resource paths, version strings (recorded in each card's
  `build:` block), and the `Resources` loader.
- **`cli.py`** — the base single/batch entry point.
- **`generate_a.py`, `generate_b.py`** — batch drivers for the `-a` and `-b` variants.
- **`__init__.py`** — public exports (`generate_card`, `build_llm_prompt`, …).

The stages are format-agnostic after Stage A: a future STIX loader that returns the same
`ParsedFlow` could feed B–D unchanged.

---

## 3. The three card variants — and why they exist

All three share Stages A and D. They differ only in Stage B/C — specifically in how the
per-step **"Succeeds when …"** clause and the mitigations content are produced. Each card
tags its lineage in `build.card_variant`.

| Variant | id suffix | Modules | "Succeeds when" prose | Mitigations content |
|---------|-----------|---------|-----------------------|---------------------|
| **base (v1)** | _none_ | `enrich.py`, `render.py` | First sentence of the ATT&CK technique description | — |
| **`-a`** | `-a` | `enrich_a.py`, `render_a.py` | Prerequisites = tactic-based access clause **+** the absent ATT&CK controls, listed as raw `M####` codes | Grounded `mitigations:` frontmatter block + a "Reducing this risk" section (Addendum B) |
| **`-b`** | `-b` | `enrich_b.py`, `render_b.py`, `control_language.py` | **Plain-language weaknesses**: the 1–3 *load-bearing* weakness phrases that gate the step, phrased "absent or weak", with no M-codes and no boilerplate; adds the `dwell` lever | Same machine-readable block; the "Reducing this risk" section uses plain control phrasing alongside the M-code |

### 3.1 Why base → `-a`

The base card answered *what the attacker does* but not *what has to be true for the step
to work*. For OIC grounding we care about prerequisites — the access/position an attacker
needs and the controls that must be missing — because that is what makes a cascade
defensible. Variant `-a` introduced grounded **mitigations** (via ATT&CK `mitigates`
relationships) and rephrased "Succeeds when" around the *absence* of those controls, plus
a tactic-derived access clause. This was correct and fully grounded, but it surfaced the
controls as raw codes, e.g.:

> *Succeeds when:* the attacker can get code to run on a host; the controls ATT&CK lists
> for this technique are not in place (M1042 Disable or Remove Feature or Program; M1049
> Antivirus/Antimalware; M1045 Code Signing; M1026 Privileged Account Management; M1038
> Execution Prevention).

### 3.2 Why `-a` → `-b` (the latest version)

Variant `-a` had five problems for a lay audience, each fixed in `-b`:

1. **It forced the reader to decode M-codes.** `-b` *translates* each mitigation into a
   plain-language weakness phrase from a static table (§4); raw codes never appear in the
   body.
2. **A boilerplate stem repeated on every step.** "The controls ATT&CK lists for this
   technique are not in place (…)" is the contrapositive of the mitigations section and
   added no signal. `-b` drops it and states the *specific* weaknesses instead.
3. **Steps weren't differentiated.** Because the access clause was keyed on the step's
   first tactic, two execution steps (e.g. *Scheduled Task* and *PowerShell*) shared an
   identical opening clause — a tell that the mechanism wasn't derived per technique.
   `-b` composes the clause from each technique's own load-bearing weaknesses, which
   differ by technique, so steps read distinctly.
4. **Every mapped mitigation was listed, flattening the signal.** A technique can map to
   five mitigations of unequal importance. `-b` prunes to the **one-to-three load-bearing**
   ones via a priority ranking (§4.2).
5. **"Missing" understated reality.** A control can be present but weak. `-b` uses the
   gloss table's "absent or weak" phrasing (e.g. *"AV or antimalware is absent or doesn't
   recognize the payload"*).

Plus a lever correction (§5) and semantic-overlap de-duplication (§6).

The same step in `-b`:

> *Succeeds when:* a risky feature or program (e.g. a scripting engine) is still present
> and abusable and unapproved code and scripts are allowed to execute.
> `[potential_mitigation overlap - review required]` *(odds — changes the odds)*

---

## 4. The mitigation gloss layer (`-b`)

### 4.1 The static asset: `refdocs/oic-mitigation-glosses.yaml`

A hand-authored, version-pinned table — one entry per ATT&CK mitigation M-code (enterprise
`M1xxx` and ICS `M0xxx`), authored against the MITRE mitigation descriptions. There are
~44 enterprise and ~52 ICS entries, so it is a small, reviewable, deterministic asset (no
LLM needed at runtime). Each entry carries:

- **`name`** — the verbatim MITRE mitigation name, used as the join key to ATT&CK
  `mitigates` relationships.
- **`control`** — plain-language control phrasing, used in the card's **mitigations
  section** (e.g. *"application control and script blocking"*).
- **`weakness_when_absent`** — the gap the gate prose names when the control is absent or
  weak, used in the **"Succeeds when"** clause (e.g. *"unapproved code and scripts are
  allowed to execute"*). One table serves both the gate (weakness framing) and the
  mitigations section (control framing).
- **`preventable: false`** — present only on the "do not / cannot mitigate" markers
  (`M1055 Do Not Mitigate`, `M1056 Pre-compromise`, ICS `M0816`). These route to a
  detection/response note instead of being listed as an option.

### 4.2 `control_language.py` — loading, prioritizing, selecting

- **Loader.** Reads the YAML once (cached) into `Gloss` records keyed by M-code. Requires
  `PyYAML`.
- **Accessors.** `weakness_phrase(mcode)` (gate prose; `None` for non-preventive markers),
  `control_phrase(mcode)` (mitigations section), `is_preventable(mcode)`.
- **Load-bearing priority.** `_PRIORITY_ORDER` is a static ranking by mitigation *name*
  (so enterprise and ICS variants of the same control share a rank). Controls that directly
  gate the abuse (disable/remove feature, execution prevention, code signing, library-load
  restriction, sandboxing, exploit protection, patching, behavior prevention, AV) rank
  highest; broad governance controls (account management, audit, OS/AD/software config,
  user training, threat intel) rank lower so they are pruned first when a technique maps to
  many mitigations.
- **`select_load_bearing(mcodes, cap=3) -> (mcodes, overlap_detected)`.** Takes the top
  `cap` preventable mitigations by priority (after exact-duplicate de-dup), then collapses
  semantically redundant weaknesses (§6). Returns the (possibly shortened) M-code list and
  a flag.

Worked example — `T1059.001 PowerShell` maps to `M1042, M1049, M1045, M1026, M1038`:

1. Priority sort → `M1042` (disable feature), `M1038` (execution prevention), `M1045`
   (code signing), `M1049` (AV), `M1026` (privileged accounts).
2. Top-3 → `M1042, M1038, M1045`. `M1026` (marginal to whether the script *runs*) is
   pruned, as intended.
3. Overlap collapse → `M1045` ("unsigned code allowed to run") is semantically redundant
   with `M1038` ("unapproved code allowed to execute"); the higher-priority `M1038` is
   kept, `M1045` dropped, and the step is flagged.
4. Result → `M1042, M1038` + overlap flag.

---

## 5. Lever classification and the `dwell` fix (`-b`)

Each step is tagged with a **lever** describing what it changes:

- **`odds`** — changes the likelihood the attack lands.
- **`dwell`** — keeps the attacker present/unseen over time (persistence, stealth).
- **`spread`** — extends reach (privilege escalation, lateral movement, credential access).
- **`size`** — drives the magnitude of loss (impact). Every card must have at least one
  `size` step; it is always flagged for human confirmation as the magnitude driver.

**The fix.** Many techniques carry multiple tactics. The base/`-a` heuristic bucketed a
step by whichever tactic it hit first, so `T1053.005 Scheduled Task` (execution +
persistence + privilege-escalation) was mis-tagged `spread`, when its *role in this flow*
is persistence. `-b` introduces role disambiguation: `DWELL_TACTICS = {persistence,
defense-evasion, stealth}` is checked **before** `spread`, so persistence/stealth steps
correctly resolve to `dwell`. `validate.py` was extended to accept `dwell` as a legal
lever (a safe, additive change — base and `-a` never emit it).

---

## 6. Semantic-overlap detection (`-b`)

Even after pruning to the top three, two surviving weaknesses can say nearly the same thing
in different words (the classic case: execution prevention vs code signing both amounting
to "untrusted code is allowed to run"). Listing both flattens the signal and pads the
sentence.

**Mechanism (deterministic, no LLM).** In `select_load_bearing`, after the top-`cap`
selection, each weakness phrase is reduced to a set of content tokens (lower-cased,
stop-words and short tokens removed). Two phrases are deemed redundant when their
**overlap coefficient** — `|A ∩ B| / min(|A|, |B|)` — is **≥ 0.5**. When that happens the
higher-priority weakness is kept, the other is dropped (shortening the clause), and an
`overlap_detected` flag is returned.

**Surfacing.** `enrich_b` sets `EnrichedStepA.mitigation_overlap = True` and records a
build-report marker; `render_b` appends the literal note
`[potential_mitigation overlap - review required]` to that step's gate clause so a reviewer
can confirm the collapse. The threshold is a single tunable constant
(`_OVERLAP_THRESHOLD`).

**Validation across the corpus.** The only collapses observed are the genuine
`M1045`↔`M1038` code-execution redundancy — no false positives against the governance,
network, or credential weakness phrasings — confirming the heuristic is precise rather than
aggressive.

---

## 7. The `-b` "Reducing this risk" section

Built from the same grounded mitigations but presented for humans:

- Mitigations are de-duplicated across the flow's steps and **classified by effect**
  (`likelihood` / `impact` / `both`) from the levers of the steps they cover, then split
  into **Reduce likelihood** and **Reduce impact** subsections (Addendum B §4–5).
- Each line shows the mitigation **name**, its **M-code** (M-codes *are* allowed here — the
  ban is only on the body cascade prose), the plain-language **control phrasing** from the
  gloss table, the **steps it covers**, and a coverage count.
- Steps with no preventive mitigation in ATT&CK are listed separately as
  "rely on detection and response".

The machine-readable `mitigations:` frontmatter block (emitted for all of `-a`/`-b`)
retains M-codes as keys, since it is a data interface, not prose.

---

## 8. Pinned grounding data (`refdocs/`)

| Resource | File |
|----------|------|
| Attack Flow corpus | `flowcorpus/*.afb` |
| Attack Flow schema | `flowschema/attack-flow-schema-2.0.0.json` |
| ATT&CK STIX | `matrices/enterprise-attack-19.1.json`, `matrices/ics-attack-19.1.json` |
| VERIS enums | `veris/verisc-enum.json` |
| ATT&CK→VERIS mapping | `ctidmapping/veris-1.4.0_attack-16.1-*.json` |
| Mitigation glosses (`-b`) | `oic-mitigation-glosses.yaml` |

Versions are recorded in each card's `build:` block. Paths live in `config.py`.

---

## 9. Usage

Base pipeline (single flow, batch, programmatic):

```powershell
# One flow, print card + report to stdout
python -m tools.cascade_cards.cli "refdocs/flowcorpus/Maastricht University Ransomware.afb" --report

# Assign an id, write card + build-report + LLM prompt to a folder
python -m tools.cascade_cards.cli "refdocs/flowcorpus/Maastricht University Ransomware.afb" `
    --id oic-ca-001 --out app/generated --emit-prompt

# Batch the whole corpus
python -m tools.cascade_cards.cli --all --out app/generated
```

Variant drivers (write to `app/generated`, sharing one id sequence so files line up for
side-by-side comparison):

```powershell
python -m tools.cascade_cards.generate_a --out app/generated   # writes base + -a cards
python -m tools.cascade_cards.generate_b --out app/generated   # writes -b cards
python -m tools.cascade_cards.generate_b "refdocs/flowcorpus/Cobalt Kitty Campaign.afb" --seq 6 --out app/generated --emit-prompt
```

Programmatic:

```python
from tools.cascade_cards import generate_card, build_llm_prompt
card_md, report_md, result, extract = generate_card("refdocs/flowcorpus/REvil.afb", card_id="oic-ca-002")
system, user = build_llm_prompt(extract)  # hand to your LLM to polish prose
```

**Requirements.** Python 3.10+. The base and `-a` variants use only the standard library;
the `-b` variant additionally requires **`PyYAML`** (to read the gloss table).

---

## 10. Format & version notes

1. **Native `.afb`, not STIX.** The spec is written for the STIX serialization
   (`start_refs`/`effect_refs`); the shipped corpus is Attack Flow Builder's native
   `attack_flow_v2` format (node + `dynamic_line` edge graph connected via anchors/latches).
   `afb.py` reconstructs the directed graph from those primitives. Downstream stages are
   format-agnostic, so a STIX loader returning the same `ParsedFlow` can be added later.
2. **ATT&CK 19.1 vs mapping 16.1.** Techniques are resolved against ATT&CK 19.1, but the
   ATT&CK→VERIS mapping is pinned at attack-16.1 (VERIS 1.4.0). Techniques present in 19.1
   but absent from the 16.1 mapping emit `[REVIEW: no mapping]`. Techniques **revoked** in
   19.1 (e.g. `T1562.001`) are still resolved for name/tactic but flagged for review.
3. **Mitigations from both domains.** `MitigationIndex` reads enterprise *and* ICS bundles,
   keeps only modern **M-code** course-of-action objects (legacy per-technique "T-code"
   mitigations are excluded), drops deprecated/revoked objects, and walks `mitigates`
   relationships with a parent-technique fallback for sub-techniques.
4. **VERIS casing.** VERIS strings use the enum's canonical casing
   (e.g. `action.social.variety.Phishing`) so they validate against `verisc-enum.json`.
5. **Ambiguous mappings.** When a technique maps to multiple VERIS values, the code picks
   deterministically (attribute.* for terminal, action.* for entry, preferring `variety`
   leaves) and appends `# [REVIEW: ambiguous]` with all candidates in the build report.
6. **Name-inferred techniques (`-b`).** When a flow step carries no technique id/ref, `-b`
   attempts a name match against ATT&CK and flags the inference for review rather than
   leaving the step ungrounded.

---

## 11. Human review (the only edits expected, spec §8)

Everything else is correct by construction. A reviewer should confirm:

- `label`, `id` / dedupe against existing cards, `applies_when` generalization scope.
- The `size` (magnitude-driver) step.
- `sectors` and any `[REVIEW]` VERIS/DBIR tokens.
- Any `[potential_mitigation overlap - review required]` note (`-b`) — confirm the dropped
  weakness was genuinely redundant.
- Any name-inferred technique flagged in the build report (`-b`).

---

## 12. Known limitations & future work

- **Priority ranking is a heuristic.** The load-bearing ordering is a curated global rank,
  not a per-technique judgement; ATT&CK provides no per-technique mitigation weighting. It
  matches the worked examples and is sensible in aggregate, but edge cases should be spot
  checked (hence the `[REVIEW]` discipline).
- **Overlap detection is lexical.** The overlap coefficient catches paraphrase via shared
  content words; it would miss redundancy expressed with entirely different vocabulary.
  The Stage-C LLM prompt provides a second, semantic pass when prose is polished.
- **Mitigation effect classification is lever-derived.** "Reduce likelihood/impact"
  buckets follow the covered steps' levers; ATT&CK mitigations skew preventive, so the
  impact bucket can be broad (documented in Addendum B).
- **Variant consolidation.** `-a` and `-b` are intentionally parallel for comparison. Once
  a house style is chosen, the winning variant can be folded into the mainline and the
  others retired.
