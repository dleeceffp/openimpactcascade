# Implementation Brief — STIX-native Attack Flow output + bundled Mermaid viewer

**For:** a coding agent working in `tools/attack_flow_workbench/`
**Goal:** Make the generator emit **STIX 2.1 Attack Flow** as its canonical artifact, and ship a **self-contained Mermaid viewer** into the output directory so generated flows can be viewed with no extra tooling. This replaces the hand-built `.afb` rendering path, which is abandoned as a maintained capability (see `OIC-DESIGN-2026-043`).
**Reference implementations (already written and validated — port these, don't reinvent):** `afb_to_stix.py`, `stix_to_mermaid.py`, `attack_flow_viewer.html`. Treat them as the spec.

---

## 0. Before you edit — orient

1. Read `attack_flow_generator.py`, `formatter.py`, `cli.py`, and `config.py` in full.
2. `grep -rn "afb\|attack_flow_v2\|anchors\|dynamic_line\|horizontal_anchor" tools/attack_flow_workbench/` to find every place that builds or assumes the `.afb` visual format. Those are the code paths being replaced.
3. Read the three reference files listed above. `afb_to_stix.py` defines the STIX object shapes; `stix_to_mermaid.py` defines the STIX→Mermaid mapping; `attack_flow_viewer.html` is the viewer to copy. **Do not redesign these — port their logic.**
4. Do not start editing until you have the consumer list from step 2.

---

## Context: why STIX, not `.afb`

`.afb` is the Builder's internal editor state — no published schema, undocumented loader invariants (e.g. a `flow` object must NOT carry `anchors`), and semantics coupled to pixel geometry. STIX 2.1 Attack Flow is the formal, schema-validated exchange format with no geometry. The decision (`OIC-DESIGN-2026-043`) is: **STIX is the artifact, Mermaid is the view, `.afb` is at most an optional template-transplant export — never hand-serialized.** This brief implements that.

---

## Change 1 — Emit STIX 2.1 Attack Flow as the canonical format

Add a STIX serializer to the workbench (new module `stix_serializer.py`, ported from `afb_to_stix.py`'s `convert()` logic but driven by the generator's in-memory flow object, not by reading an `.afb`). It must produce a `bundle` containing:

- One **`extension-definition`** object with id `extension-definition--fb9c968a-745b-4ade-9b25-c324172197f4`, `extension_types: ["new-sdo"]`.
- One **`identity`** (producer) — `name` from config (e.g. "OIC Attack Flow Workbench"), `identity_class: "system"`.
- One **`attack-flow`** SDO: required `type`, `spec_version: "2.1"`, `name`, `start_refs`, `scope`; plus `description`, `created_by_ref`, and `extensions: { <ext-uuid>: { extension_type: "new-sdo" } }`. `start_refs` = the action ids with no incoming edge.
- **`attack-action`** objects: required `type`/`spec_version`/`name`; plus `tactic_id`, `technique_id`, `description`, `confidence` (see Change 2), `effect_refs` (edges → successor ids), `asset_refs` (→ asset ids this action compromises), and the `extensions` block.
- **`attack-asset`** objects: `type`/`spec_version`/`name` + `extensions`.
- (If the generator produces them) **`attack-condition`** / **`attack-operator`** objects for branch logic.

Hard rules (these are the validity-critical ones discovered in prototyping):
- **No `null` property values** — omit the key instead. The schema rejects nulls in several places.
- **`confidence` is an integer 0–100**, never a word (Change 2).
- Every `effect_refs` / `asset_refs` / `start_refs` id must resolve to an object in the bundle (no dangling refs).
- Exactly one `attack-flow` SDO per bundle.

## Change 2 — Confidence: map generator vocabulary → STIX integer

The generator's internal vocabulary (`observed`/`reported`/`speculative`, from the de-linearization work) is NOT valid STIX. Map it on serialization:

```
observed | confirmed -> 100
reported              -> 75
speculative           -> 0
# named scale terms, if ever used directly:
certain 100, very-probable 90, probable 75, even-odds 50, doubtful 30, very-doubtful 10, speculative 0
```

Keep the word form in the generator's own JSON/markdown output if useful internally; the mapping happens only at the STIX boundary.

## Change 3 — Emit `effect_refs` (edges) and `asset_refs` (asset links)

This depends on the de-linearization change (generator output carrying `depends_on` per action). Wire it through to STIX:
- `depends_on` (predecessor ids in the generator model) → invert into **`effect_refs`** on the predecessor (STIX edges point forward, predecessor → successor).
- **`asset_refs`**: each action lists the asset ids it compromises. **The generator must emit which named assets each action targets** — add this to the generator's output schema and prompt. One line of prompt guidance: *"For each action, list in `asset_refs` the names of the targeted assets it directly compromises (from the flow's asset list)."* Without this, assets render disconnected (the known gap); with it, the viewer draws `targets` edges automatically.

If the generator cannot yet emit `asset_refs`, ship Change 3's serializer support anyway (it's a no-op when absent) and leave a `# TODO: generator asset_refs` — but the prompt change is small and should be done in this same PR.

## Change 4 — Update the formatter / CLI output

- `formatter.py`: replace the `.afb` writer with the STIX serializer as the default `json` output. Keep the markdown summary writer (it's useful and format-independent).
- Add a `--format` option value `stix` (and make it the default for json). Retain `md`/`both`. **Remove or quarantine the `.afb` writer** — if kept at all, gate it behind an explicit `--format afb-template` flag that uses template-transplant (out of scope for this PR; just don't let plain runs emit hand-built `.afb`).
- Default output filename: `<base>.json` (STIX bundle) alongside the existing `<base>.md`.

## Change 5 — Bundle the Mermaid viewer into the output directory

- Copy `attack_flow_viewer.html` and `stix_to_mermaid.py` into the workbench package, and have the CLI **copy `attack_flow_viewer.html` into the output directory** (e.g. `generated/attack_flows/`) on each run if not already present, so every batch of flows sits next to a viewer.
- Print a line on success: `View: open attack_flow_viewer.html and load <base>.json`.
- The viewer is self-contained (loads Mermaid from CDN). Note in the README that for fully-offline use, `mermaid.min.js` can be downloaded and the one `<script src>` repointed.
- Also expose `stix_to_mermaid.py` as an optional CLI path for headless rendering (`python stix_to_mermaid.py <bundle> --md`).

## Change 6 — Validation in CI

Add a test that, for a generated bundle:
1. parses with `stix2.parse(bundle, allow_custom=True)` without error;
2. contains exactly one `attack-flow`;
3. has zero dangling `effect_refs`/`asset_refs`/`start_refs`;
4. has zero `null` property values;
5. every `attack-action` confidence is an int in 0–100;
6. (when `asset_refs` are emitted) zero orphan assets — every asset is referenced by at least one action.

---

## Acceptance criteria

1. `python cli.py -i energy -r Canada -s 2500` produces a `.json` STIX bundle that passes all Change 6 checks.
2. `grep -rn "attack_flow_v2\|horizontal_anchor\|dynamic_line\|\"anchors\"" tools/attack_flow_workbench/` returns nothing in the active output path (only, at most, inside a quarantined template-transplant module).
3. The output directory contains `attack_flow_viewer.html` after a run; opening it and loading the bundle renders the flow with action nodes, branches, and (if `asset_refs` present) connected assets — no orphan-asset warning.
4. `python stix_to_mermaid.py <bundle>` emits valid Mermaid (header `flowchart TD`, unique node ids, all edge endpoints defined).
5. Confidence values in the bundle are integers; no `"reported"`/`"speculative"` strings survive into STIX.
6. The markdown summary still generates.

---

## Out of scope — do not do

- Do **not** build or maintain a from-scratch `.afb` serializer. The only sanctioned `.afb` route is template-transplant, and it is not part of this PR.
- Do **not** add `succeeds when` / control-gate content to any generated artifact. Control logic belongs to the *compression* pipeline (`OIC-DESIGN-2026-002`), on the far side of the `.afb`/STIX seam, added by a human curator. The generator emits observed shape only (actions, assets, edges) — never defender controls.
- Do **not** change the corpus/grounding modules, the model name, or token limits.
- Do **not** merge generation with compression.

---

## Verification before opening the PR

1. `python -m pytest tools/attack_flow_workbench/` (add the Change 6 tests).
2. Run a live generation; confirm the `.json` validates and the bundled viewer renders it (paste a screenshot or the Mermaid into the PR).
3. Confirm a second run reuses/overwrites the viewer in the output dir correctly.
4. In the PR description, note that `.afb` hand-serialization is retired per `OIC-DESIGN-2026-043` and link this brief.

---

## Why this is the right cut (context, not a task)

The value is the *semantics* — grounded, branched, asset-aware scenarios — which are format-independent. STIX has a published schema, so building on it is engineering and validatable in CI; `.afb` has none, so hand-building it is perpetual reverse-engineering. Mermaid renders the branch structure better than the hand-laid `.afb` spine did, with zero Builder dependency. Keep the generator emitting observed shape only; let the compression pipeline own control logic on the other side of the seam.
