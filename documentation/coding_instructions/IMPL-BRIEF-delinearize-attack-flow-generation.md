# Implementation Brief — De-linearize Attack Flow Generation

**For:** a coding agent working in `tools/attack_flow_workbench/`
**Target file (primary):** `attack_flow_generator.py`
**Also touches:** `formatter.py`, and any other module that reads `attack_actions` / `order`
**Goal:** Stop the generator from forcing every attack into a straight 14-tactic march. Let it model branches, joins, skipped tactics, and repeated tactics, grounded in observed threat-actor behaviour. Tactics become a *labelling vocabulary*, not a *sequence to complete*.

---

## 0. Before you edit — orient

1. Read `attack_flow_generator.py` in full. The relevant regions are roughly: the user-prompt builder (~L145–183), the system-prompt builder (`_build_system_prompt`, ~L216–234), and the fallback (`_generate_fallback_flow`, ~L236+). **Line numbers may have shifted — match on the quoted content, not the line number.**
2. Read `formatter.py` in full. Find every place that consumes `attack_actions`, `order`, `entry_points`, or `assets`. The schema change in Change 4 will break anything that sorts by `order`.
3. `grep -rn "order" tools/attack_flow_workbench/` and `grep -rn "attack_actions" tools/attack_flow_workbench/` so you have the complete list of consumers before changing the contract.
4. Do **not** start editing until you have that consumer list. The schema change is the risky part; the prompt edits are cosmetic by comparison.

---

## Change 1 — System prompt: tactics are a vocabulary, not a sequence

In `_build_system_prompt()`, **replace** requirement 3:

> **OLD:**
> `3. Follow ATT&CK's 14 tactics in logical order: Initial Access → Execution → Persistence → Privilege Escalation → Defense Evasion → Credential Access → Discovery → Lateral Movement → Collection → Command and Control → Exfiltration → Impact`

> **NEW:**
> ```
> 3. Treat the 14 ATT&CK tactics as a LABELLING VOCABULARY, not a sequence to complete.
>    Real intrusions skip tactics, repeat them, and run steps in parallel: a smash-and-grab
>    may go straight from initial access to impact; an attacker holding valid credentials may
>    never escalate privilege; discovery and lateral movement often interleave and repeat.
>    Build the flow from WHAT THIS THREAT ACTOR ACTUALLY DOES to reach its objective — based
>    on the supplied threat intelligence and forensic patterns — then label each node with
>    whichever tactic fits. Include only the steps this actor needs, in the structure the
>    evidence supports. Do NOT add a node merely to "complete" a tactic chain.
> ```

## Change 2 — System prompt: make grounding the source of truth, add confidence

In the same requirements list, **add** a new requirement (renumber as needed):

> ```
> 6. Anchor every node in observed behaviour. Prefer techniques attested in the supplied DBIR
>    patterns, web intelligence, or known actor MO for this industry/region. Tag each node:
>      - "observed"    : directly supported by the supplied grounding
>      - "reported"    : consistent with public reporting on this actor/pattern
>      - "speculative" : plausible but not evidenced — use sparingly, never as padding
>    An unevidenced node added only for completeness is a defect, not a feature.
> ```

## Change 3 — User prompt: replace the linear progression line

In the user-prompt f-string (the `Generate a realistic, industry-specific attack flow that:` block), **replace** item 2:

> **OLD:**
> `2. Follows the logical progression of a real attack (Initial Access → Execution → Persistence → etc.)`

> **NEW:**
> `2. Reconstructs how THIS SPECIFIC actor reaches its objective against this target — branching, skipping, or repeating tactics as the real pattern requires, rather than marching through every ATT&CK phase. A flow with 4 well-evidenced steps is better than 12 padded ones.`

---

## Change 4 — Output schema: replace flat `order` with dependency edges (the important one)

The current schema is a flat list keyed by integer `order`. **A flat ordered list can only express a straight line** — it has no way to represent a fork, a join, or an AND/OR precondition. This is the structural root of the linearity, independent of prompt wording. Replace it with node IDs + dependency edges + an optional logic-gate array.

In the user prompt, **replace** the `Return ONLY a JSON object with this structure:` block with:

```json
{
    "name": "Attack flow name",
    "description": "Description of the attack scenario",
    "scope": "incident",
    "attack_actions": [
        {
            "id": "n1",
            "name": "Technique name",
            "technique_id": "TXXXX.XXX",
            "tactic": "Tactic name (e.g., Initial Access)",
            "description": "How this technique is used in the attack",
            "depends_on": [],
            "confidence": "observed | reported | speculative"
        }
    ],
    "logic": [
        {"type": "AND", "inputs": ["n2", "n3"], "output": "n4"}
    ],
    "entry_points": ["n1"],
    "assets": ["asset_name"],
    "threat_actor": "Threat actor type"
}
```

Add this guidance immediately under the schema block in the prompt:

```
- "depends_on" lists the id(s) of node(s) that must occur before this node. It REPLACES "order".
  * Two nodes sharing one predecessor = a fork (the attacker had two options/paths from there).
  * One node listing several predecessors = a join (it needed all of them).
  * Entry nodes have "depends_on": [] and must appear in "entry_points".
- Use "logic" ONLY when a node genuinely requires a combination of predecessors:
  AND = all inputs needed; OR = any one input suffices. Omit "logic" (use []) for simple chains.
- Model a repeated tactic as DISTINCT nodes (e.g. "Discovery", later "Discovery (round 2)"),
  never as a back-edge. The dependency graph must be acyclic.
- Do not emit an "order" field.
```

## Change 5 — Formatter: order by dependencies, reject cycles, carry gates + confidence

`formatter.py` currently assumes `order`. Update it:

1. **Topological sort.** Replace any `sorted(actions, key=lambda a: a["order"])` with a topological sort over `depends_on`. Suggested helper:
   ```python
   def _topo_order(actions, logic):
       # actions: list of dicts with "id" and "depends_on"
       # returns ids in a valid execution order; raises ValueError on a cycle
       import collections
       deps = {a["id"]: set(a.get("depends_on", [])) for a in actions}
       # logic gates add edges input -> output
       for g in (logic or []):
           for inp in g.get("inputs", []):
               deps.setdefault(g["output"], set()).add(inp)
       order, ready = [], [i for i, d in deps.items() if not d]
       seen = set()
       while ready:
           n = ready.pop(0); order.append(n); seen.add(n)
           for i, d in deps.items():
               if i not in seen and d <= seen and i not in ready:
                   ready.append(i)
       if len(order) != len(deps):
           raise ValueError("attack flow dependency graph contains a cycle")
       return order
   ```
2. **Cycle handling.** On `ValueError` from the sort, log it and fall back gracefully (do not crash the run). A cycle is a model error; surface it in the markdown summary as a warning rather than silently linearizing.
3. **Render the graph, not a list.** In the markdown summary, show `depends_on` (e.g. "← after: n2, n3") and any AND/OR gates, so a human refining the flow can see the branch structure. Do not flatten branches into a single numbered list as if sequential.
4. **Confidence.** Surface each node's `confidence` in both JSON and markdown output. Speculative nodes must be visibly marked so a human curator knows what is evidence-backed vs. inferred.
5. **STIX/`.afb` export (if present).** If the formatter emits MITRE Attack Flow bundle objects, map `depends_on` to `attack-action` → `effect_refs`/relationships (or the `.afb` edge objects), and map `logic` entries to `AND`/`OR` operator nodes. If the current exporter only chains actions linearly, update it to emit the edges; otherwise the branch structure is lost on export.

## Change 6 — Fallback flow: mark it unmistakably as a stub

`_generate_fallback_flow()` returns a hardcoded phishing→execution→persistence→impact chain on any parse/LLM failure — i.e. it silently produces the most linear, generic artifact possible, which a human could mistake for a grounded result. Update it to:

1. Set `"scope": "stub"` (not `"incident"`).
2. Set every node's `"confidence": "speculative"`.
3. Convert it to the new schema (`id` + `depends_on`, no `order`).
4. Add a top-level `"generation_status": "fallback_stub"` field and have the formatter print a clear `⚠ FALLBACK STUB — generation failed, not grounded` banner in the summary.

## Change 7 (optional, do only if parse failures rise after Change 4) — robust JSON extraction

The current extraction takes the substring from first `{` to last `}` and `json.loads` it. With the new nested `logic` array this stays workable but is brittle. If you observe parse failures after the schema change, harden it — prefer the SDK's structured-output / tool-use path over substring slicing. Treat this as a follow-up, not part of the core change.

---

## Acceptance criteria

The change is correct when all of the following hold:

1. **No linear scaffolding remains.** `grep -n "in logical order"`, `grep -n "Initial Access → Execution → Persistence"`, and `grep -n '"order"'` in `attack_flow_generator.py` and `formatter.py` all return nothing (except inside the new prompt text where tactics are explicitly described as non-mandatory).
2. **Schema round-trips.** A generated flow parses, topologically sorts without error, and re-serializes. `entry_points` contains exactly the nodes with empty `depends_on`.
3. **Branching is representable AND produced.** Add a test that requests a scenario with a known fork (e.g. `--threat "credential theft with both data exfiltration and ransomware outcomes"`) and assert the result contains at least one node referenced as a predecessor by ≥2 nodes, OR a `logic` gate. (Structure must be *possible*; this test proves it's also *exercised*.)
4. **Tactic-skipping is allowed.** Add a test requesting a smash-and-grab (`--threat "smash and grab data theft, no persistence"`) and assert the flow does NOT contain all 14 tactics — specifically that it can omit Persistence/Privilege Escalation without error.
5. **Cycles are rejected, not linearized.** Feed the formatter a hand-crafted cyclic graph fixture and assert it raises/warns rather than silently dropping an edge.
6. **Confidence is visible.** Generated JSON and markdown both show per-node confidence; the fallback stub is visibly banner-marked.
7. **No consumer left behind.** Every reader of `order`/`attack_actions` found in step 0.3 is updated. Nothing references `order` anymore.

---

## Out of scope — do not change

- Do **not** alter `cli.py`'s argument interface, `config.py`, `mitre_loader.py`'s technique lookups, or the corpus/web-search grounding modules. This change is about *structure and instructions*, not inputs or grounding sources.
- Do **not** change the model name, token limits, or the corpus paths.
- Do **not** merge this generator with the compression pipeline. Output remains a candidate `.afb`/flow for human refinement before it becomes a cascade archetype.
- Do **not** add new external dependencies.

---

## Verification before opening the PR

1. `python -m pytest tools/attack_flow_workbench/` (add the tests in Acceptance #3–#5 if absent).
2. Run two live generations and eyeball the output:
   - `python cli.py -i healthcare -r "United States" -s "500-1000" --threat "smash and grab data theft, no persistence" -f both` → confirm tactics are skipped, no error.
   - `python cli.py -i financial -r Canada -s SME --threat "BEC leading to both wire fraud and data theft" -f both` → confirm a fork or AND/OR gate appears.
3. Confirm both runs produce valid JSON that imports into the MITRE Attack Flow Builder (per README's integration note), with branches visible — not a single straight chain.
4. In the PR description, paste the before/after of one generated flow's structure so a reviewer can see the branching now renders.

---

## Why this works (context for the agent, not a task)

The model produced straight lines because *both* the instructions and the data structure only knew how to describe straight lines. Changes 1–3 remove the verbal scaffolding; Change 4 is the load-bearing fix — giving nodes `depends_on` edges means a tree is now the natural shape to fill, so non-linearity stops being a plea and becomes the path of least resistance. Changes 5–6 stop the linear bias from re-entering through the formatter's sort and the failure-mode stub. Keep tactics as labels on evidence-driven nodes, and the flow shape follows the threat actor's real MO instead of a canonical checklist.
