# OIC Cascade Card Generator — Build Spec

Convert a CTID **Attack Flow** STIX JSON file into a draft **grounding card** (the
`oic-ca-*.card.md` format) that an LLM can reason on. The goal is *structurally correct,
well-typed metadata so a human review is minor* — confirm a handful of judgment fields,
not rebuild the card.

**Design emphasis:** reconstruct *how the attack could succeed* — the ordered chain of
enabling conditions — not a control-framework mapping. Cards lead with "this step succeeds
when …", not "broken by CIS x.y".

**Determinism boundary (this is what makes review minor):** parsing, graph traversal, and
all metadata/enumeration values are produced by *deterministic code* against pinned local
data. The LLM is used only to write plain-language prose, constrained to the extracted facts.
The LLM never invents a technique, a VERIS value, an actor, or a step order.

---

## 1. Local resources (download once, pin versions)

All are public Git repos / raw files. Pinning matters: enum values and technique IDs must be
reproducible, and the build report records each version (see §6).

| Resource | Why it's needed | Source |
|----------|-----------------|--------|
| Attack Flow corpus (STIX JSON) | The input flows | `github.com/center-for-threat-informed-defense/attack-flow` → `/corpus` |
| Attack Flow schema + extension-definition | Parse/validate the bundle | same repo → `/stix` (`attack-flow-schema-*.json`) |
| MITRE ATT&CK STIX data | Resolve `technique_ref` → name/tactic; pull technique description text as raw material for "succeeds when" | `github.com/mitre-attack/attack-stix-data` → `enterprise-attack-*.json` |
| VERIS schema / enumerations | Controlled vocabulary; validate `veris_*` strings so they are never hallucinated | `github.com/vz-risk/veris` |
| CTID Mappings Explorer (ATT&CK → VERIS) | Auto-populate `veris_*` from technique IDs | `github.com/center-for-threat-informed-defense/mappings-explorer` |

Yes — both your assumed downloads (VERIS schema, the Attack Flow corpus) are required. Add the
ATT&CK STIX bundle and the ATT&CK→VERIS mapping; without them the VERIS fields and technique
names degrade to guesses, which defeats the "minor edits" goal.

---

## 2. Output contract

One file per flow: `oic-ca-<NNN>-<slug>.card.md`.

### Frontmatter (every field AUTO unless marked [REVIEW])

```yaml
id: oic-ca-<NNN>                 # [REVIEW] new archetype, or instance of an existing one? (dedupe)
label: "<short scenario name>"   # [REVIEW] LLM-proposed from cascade shape; human confirms
type: cascade_archetype
entry: "<plain phrase>"          # AUTO from first action's technique
terminal_impact: "<plain phrase>"# AUTO from impact action
applies_when: "<topology precondition>"  # [REVIEW] inferred from assets/conditions; human confirms scope
sectors: "<sector or sector-agnostic>"   # AUTO from flow description, else "sector-agnostic [REVIEW]"
dbir_pattern: <pattern>          # AUTO via §5 rule
veris_entry: <action.cat.value>  # AUTO via mapping; [REVIEW] if mapping missing/ambiguous
veris_terminal: <attribute...>   # AUTO via mapping; [REVIEW] if missing/ambiguous
anchor_incident: "<name, year>"  # AUTO from flow name/description
tags: [ ... ]                    # AUTO from technique/tactic keywords
build:                           # AUTO provenance — never hand-edited
  source_flow: "<filename>"
  attack_flow_schema: "<version>"
  attack_version: "<enterprise-attack-N>"
  veris_version: "<tag>"
  mapping_version: "<tag>"
  generated: <date>
```

### Body sections (fixed order)

`## Scenario` → `**Recognize this scenario** when …` → `### The cascade` (ordered steps) →
`### Branching` → `### Odds vs. size` → `### Anchor (real incident)`.

Each cascade step:

```
N. **<step name>** — <what the attacker does>.
   *Succeeds when:* <the enabling weakness/condition that lets it through>. *(odds | spread | size)*
```

---

## 3. Pipeline

- **Stage A — Parse (code).** Load bundle, index by `id`/`type`, traverse the flow graph, emit an
  ordered step list + branch structure. No LLM.
- **Stage B — Enrich & map (code).** Resolve technique names/tactics, map techniques → VERIS,
  derive DBIR pattern, classify each step's lever. No LLM.
- **Stage C — Draft (LLM).** Turn the Stage A/B structured extract into card prose under strict
  constraints (§7).
- **Stage D — Validate (code).** Run the checklist (§8); emit a build report listing every
  `[REVIEW]` marker.

---

## 4. Stage A — parsing Attack Flow

Attack Flow is a STIX 2.1 extension. Relevant SDOs:

- `attack-flow` — top-level; read `name`, `description`, `scope`, `start_refs`, author identity.
  Exactly one per bundle; `start_refs` are the entry points.
- `attack-action` — one technique execution. Read `name`, `technique_id`, `technique_ref`,
  `tactic_id`, `description`, `asset_refs`, `effect_refs`. These are your **gates**.
- `attack-asset` — `name`, `description`, `object_ref`. Source of the topology precondition.
- `attack-operator` — `operator` (AND/OR) + `effect_refs`. Joins paths via Boolean logic.
- `attack-condition` — `on_true_refs` / `on_false_refs`. Splits a path on success/failure of an action.

**Edges to follow:** `attack-flow.start_refs` → ; `attack-action.effect_refs` → ;
`attack-operator.effect_refs` → ; `attack-condition.on_true_refs` / `on_false_refs` → .

**Algorithm:**
1. From `start_refs`, traverse the graph (topological order; the graph is a DAG of actions linked
   by operators/conditions).
2. Emit the ordered list of `attack-action` nodes = the cascade steps.
3. Record every `attack-operator` with `OR` and every `attack-condition` as a **branch marker**
   between steps → feeds the Branching section.
4. **Entry** = action(s) reachable directly from `start_refs`.
5. **Terminal** = action(s) in the Impact tactic (`TA0040`) or with no outgoing `effect_refs`
   (e.g. `T1486` encryption, `T1485` destruction, `T1490` inhibit recovery).

---

## 5. Stage B — enrichment & mapping rules

**Technique → name/tactic:** resolve `technique_ref` (or `technique_id`) against the ATT&CK STIX
bundle. Use the technique description as raw material for the "succeeds when" clause (Stage C
rewrites it; do not paste verbatim).

**Technique → VERIS:** look up each technique in the ATT&CK→VERIS mapping. The entry action's
mapped value → `veris_entry`; the terminal action's mapped attribute → `veris_terminal`. Validate
every string against the VERIS enumerations; if no mapping exists, write the value as
`[REVIEW: no mapping]`.

**DBIR pattern (decision rule, first match wins):**
1. Web-app entry (`T1190`, `T1133` on a web asset) with no deeper host intrusion → `basic_web_application_attacks`
2. Social entry that ends at the social outcome (BEC/credential phishing, no host takeover) → `social_engineering`
3. Multi-category actions (hacking + malware) with lateral movement and/or Impact → `system_intrusion`
4. Insider / entrusted-access abuse → `privilege_misuse`
5. Availability-only flood → `denial_of_service`
6. Otherwise → `[REVIEW: pattern]`

**Lever classification (per step):**
- Impact-tactic steps (`TA0040`: encryption, destruction, inhibit-recovery, extortion/theft) → **size**
- Privilege escalation, lateral movement, credential/domain steps → **spread**
- Everything earlier (initial access, execution, persistence, defense evasion, discovery, C2) → **odds**

Flag the **size** step as `[REVIEW]`: the magnitude driver is the single highest-value judgment in
the card and is worth a human glance.

---

## 6. Stage C — LLM drafting prompt (template)

Pass the Stage A/B extract as structured input. Use a system instruction along these lines:

> You are drafting an OIC grounding card from a structured attack-flow extract. Use ONLY the facts
> provided — do not add techniques, steps, actors, sectors, or VERIS values that are not present.
> Write in plain language for a non-specialist reader.
>
> - **Scenario:** 2–3 sentences. State that the single entry event is not the real problem; the
>   damage requires the whole chain to succeed.
> - **Recognize this scenario when …:** one paragraph synthesizing the enabling conditions across
>   all steps plus the topology precondition — the conditions under which an org is exposed.
> - **The cascade:** one numbered step per extracted action, in order. Each line: what the attacker
>   does, then `*Succeeds when:* <the weakness/condition that lets it through>`, then the lever tag
>   `*(odds | spread | size)*`. Focus on HOW the step succeeds. Do NOT cite control names or
>   framework IDs.
> - **Branching:** if any OR operator or condition was recorded, explain in one or two sentences that
>   alternative paths existed, so closing one weakness does not close the route.
> - **Odds vs. size:** contrast the steps tagged *odds*/*spread* (which change how likely the attack
>   is to succeed) with the step tagged *size* (which changes the magnitude of loss). Frame them as
>   different decisions.
> - **Anchor:** 2 sentences naming the real incident from the flow, for credibility.
> - Insert the literal token `[REVIEW]` wherever the extract marked a field for review, and never
>   guess a value that was marked missing.

---

## 7. Stage D — validation checklist (code)

Reject or flag any card that fails:
- Exactly one `attack-flow` SDO; `start_refs` non-empty.
- ≥ 2 ordered actions; ≥ 1 terminal/impact action identified.
- `veris_entry` and `veris_terminal` are valid VERIS enum strings **or** carry a `[REVIEW]` token.
- `dbir_pattern` ∈ allowed set (or `[REVIEW]`).
- Every cascade step has a `Succeeds when:` clause and one lever tag.
- A Branching section exists iff an operator/condition was recorded.
- `build:` provenance fully populated.
- Build report lists every `[REVIEW]` token with its field.

---

## 8. Human review checklist (the only edits expected)

If Stages A–D are correct, a reviewer touches only:
1. **`label`** — does the proposed archetype name fit?
2. **`id` / dedupe** — new archetype, or another instance of one you already have? (If an instance,
   merge the incident as an additional anchor rather than minting a new card.)
3. **`applies_when`** — is the generalization scope right, or too narrow/broad?
4. **The `size` step** — is the magnitude driver correctly identified?
5. **`sectors`** and any `[REVIEW]` VERIS/DBIR tokens the mapping couldn't resolve.

Everything else — step order, technique facts, entry/terminal, valid VERIS strings, provenance —
is correct by construction and should not need editing.

---

## 9. Worked reference

Running the 2019 Maastricht flow through this pipeline should reproduce the `oic-ca-001` card:
`start_refs` → phishing action (`entry`, `veris_entry: action.social.variety.phishing`), traversal
through the backdoor/C2/dwell/escalation/credential steps (each tagged *odds*/*spread*), terminating
at the Clop encryption + inhibit-recovery actions (`terminal_impact`,
`veris_terminal: attribute.availability.variety.destruction`, lever **size**, `[REVIEW]`). DBIR rule
→ `system_intrusion`. The reviewer then confirms the label, the flat-network/online-backup
`applies_when`, and the backup step as the size driver — minutes of work, not a rewrite.
