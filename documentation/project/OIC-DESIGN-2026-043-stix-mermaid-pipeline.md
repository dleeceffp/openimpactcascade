# OIC-DESIGN-2026-043: Attack-Flow Artifact Pipeline — STIX as canonical, Mermaid for viewing

| Field | Value |
|-------|-------|
| **Status** | `[ACCEPTED]` — supersedes the `.afb`-first rendering approach explored during prototyping. |
| **Date** | 2026-06-18 |
| **Owner** | D. Leece |
| **Decision** | The generator emits **STIX 2.1 Attack Flow** as its canonical artifact. Visualization is done with **Mermaid** (and optionally GraphViz). Builder-native `.afb` is treated as an *optional* export, produced only by template-transplant or MITRE's own tooling — never hand-serialized from scratch as a maintained capability. |
| **Companion docs** | `OIC-DESIGN-2026-042` (Custom Attack Path Analysis — generation); `OIC-DESIGN-2026-002 Rev B` (compression). |
| **Artifacts shipped with this doc** | `afb_to_stix.py`, `stix_to_mermaid.py`, `attack_flow_viewer.html` |

---

## 1. The question this answers

Is hand-built MITRE Attack Flow artifact generation a *practical* basis for custom development, or a maintenance trap? The prototyping established a clear answer with three layers.

**The semantic generation is practical and is where the value lives.** Producing grounded, industry-specific attack content — techniques, tactics, a plausible chain, confidence-typed nodes — worked early and is genuinely useful as a starting point for "how would that happen here." Nothing in the rendering work undermined it.

**STIX 2.1 as the canonical output is practical.** It is the *formal, published, schema-validated* Attack Flow exchange format. The generated bundle validated against MITRE's `attack-flow-schema-2.0.0.json`, parsed cleanly with the official `stix2` library, and has no visual geometry to get wrong. Building on STIX is *engineering*, because there is a spec.

**Hand-authoring `.afb` from scratch is NOT practical as a maintained capability.** The `.afb` format is the Builder's internal editor state. It has no published schema, encodes undocumented loader invariants (discovered the hard way: *a `flow` object must not carry an `anchors` block* — nothing tells you that, and no validator flags it), couples semantics to pixel geometry that depends on rendered text size, and there is deliberately **no STIX→AFB converter** because synthesizing layout is unsolved in general. The Builder has already moved v2→v3; a hand-rolled serializer is a standing bet against invariants you cannot see, whose failure mode is a structurally-plausible file that silently does not render.

### Decision

> Anchor the pipeline on STIX. Let the format choice follow the spec: STIX has one, so build on it; `.afb` does not, so do not hand-build it. The value — grounded, branched, asset-aware scenarios — lives in the *semantics*, which are format-independent.

---

## 2. The pipeline

```
  generator (LLM, grounded)                    ← OIC-DESIGN-2026-042
        │
        ▼  emits semantics: {nodes, edges (depends_on), asset_refs, confidence}
   STIX 2.1 Attack Flow bundle  (CANONICAL ARTIFACT)
        │           │                    │
        │           │                    └──► compression pipeline (OIC-DESIGN-2026-002)
        │           │                          [.afb/STIX seam → archetype cards]
        │           │
        │           └──► .afb  (OPTIONAL, only via template-transplant or MITRE CLI)
        │                       for editing in the Builder UI
        ▼
   Mermaid  (VIEWING)
   - stix_to_mermaid.py  → paste into mermaid.live / Markdown
   - attack_flow_viewer.html → open the bundle directly, render + export SVG
```

Three properties make this durable: STIX is validatable (catch errors in CI), Mermaid needs no Builder dependency (renders anywhere), and the canonical artifact never carries geometry (the whole class of layout bugs cannot occur).

---

## 3. How to create the STIX bundle

`afb_to_stix.py` converts the workbench's current `.afb` output to a STIX 2.1 Attack Flow bundle. (Longer term, the generator should emit STIX directly — §6 — but this converter is the bridge today and documents the exact object shapes.)

```bash
python afb_to_stix.py  attack_flow_energy_canada.afb  attack_flow.json
```

What it emits, and the rules that make it valid:

- A **`bundle`** containing exactly one **`attack-flow`** SDO, plus an **`identity`** (producer) and the **`extension-definition`** object with the canonical Attack Flow UUID `extension-definition--fb9c968a-745b-4ade-9b25-c324172197f4`. Every Attack Flow SDO carries `extensions: { <that-uuid>: { extension_type: "new-sdo" } }`.
- **`attack-action`** objects (required: `type`, `spec_version`, `name`) with `tactic_id`, `technique_id`, `description`, and edges as **`effect_refs`** (a list of the SDO ids this action leads to). Branches and joins are just multiple/shared `effect_refs` — no geometry needed.
- **`confidence`** is a STIX **integer 0–100**, not a word. The converter maps the generator's vocabulary onto the scale: `observed/confirmed → 100`, `reported → 75`, `speculative → 0` (and the named scale terms map to their midpoints). This is the single most common validity error when authoring by hand.
- **`start_refs`** on the flow = the action(s) with no incoming edge (the entry points).
- No `null` property values (drop the key instead) — the schema rejects nulls in several places.

Validate before trusting it:

```bash
pip install stix2 jsonschema
python - <<'PY'
import json, stix2
b = json.load(open("attack_flow.json"))
stix2.parse(b, allow_custom=True)          # structural STIX 2.1 check
print("objects:", len(b["objects"]),
      "| flows:", sum(o["type"]=="attack-flow" for o in b["objects"]))
PY
```

For schema-level validation, fetch `attack-flow-schema-2.0.0.json` from the MITRE CTID repo and validate each `attack-action` / `attack-asset` / `attack-flow` against the matching `$defs` entry. (The prototyping run passed all objects.)

---

## 4. How to view it with Mermaid

Two routes, same converter logic.

### 4a. Quick / scriptable — `stix_to_mermaid.py`

```bash
# print Mermaid to stdout
python stix_to_mermaid.py attack_flow.json

# write a .mmd file
python stix_to_mermaid.py attack_flow.json -o flow.mmd

# wrap in a ```mermaid fence for pasting into Markdown
python stix_to_mermaid.py attack_flow.json --md
```

Then render the output by pasting into:
- **https://mermaid.live** — instant render, exports PNG/SVG.
- **Any Markdown that supports Mermaid** — GitHub READMEs/issues, Obsidian, MkDocs, GitLab. Paste the fenced block straight in.

The converter maps `attack-action → rounded box` (with technique id + confidence term), `attack-asset → parallelogram`, `attack-condition → diamond`, `attack-operator → circle (AND/OR)`, and draws `effect_refs`/`asset_refs`/condition branches as edges. It emits a `warning:` to stderr listing any assets not linked to an action (the current generator gap — §6).

### 4b. Self-contained viewer — `attack_flow_viewer.html`

Open the file in any browser, click **Open STIX bundle**, pick `attack_flow.json`. It renders inline, shows flow metadata, flags orphan assets, and has **Copy Mermaid** and **Download SVG** buttons. No install, no server, no VS Code extension. (It loads Mermaid from a CDN; for fully-offline use, download `mermaid.min.js` and repoint the one `<script src>`.)

This is the answer to "can I build a basic Mermaid viewer" — yes, and a single static HTML file is the whole thing. It is more reliable than the VS Code Mermaid extensions, which expect a fenced `.md`/`.mmd` and don't speak STIX; this viewer reads the bundle natively and does the STIX→Mermaid step for you.

---

## 5. Why not just keep fixing the `.afb` serializer?

It *does* render now, after fixing: the flow-has-no-anchors invariant, edge direction (bottom→top, anchor offset `270→90`), full `layout` coverage for nodes **and** latches **and** handles, the confidence enum, and `author.name`. But that working file is correct against *this* Builder version, for *this* flow shape, and took two reference files plus a transplant experiment to debug a single invisible key. That is reverse-engineering a closed format in perpetuity. If you ever need an editable `.afb`, the **only** approach proven robust is **template-transplant**: keep a few known-good, Builder-authored `.afb` skeletons and reshape them to hold generated content, so the template carries the invariants for free. Do not invest in the from-scratch serializer as a product surface.

---

## 6. The generator gap this exposed (fix regardless of format)

The current generator emits actions and a flat list of assets but **no graph structure**: no explicit edges and no action→asset links. Symptoms seen in the Builder — actions in a straight line, assets floating disconnected — are *not* rendering bugs; they are missing data, and they would be missing in STIX and Mermaid too. The fix lives in the generator's output schema (already scoped in the de-linearization brief) and should add, per action:

- **`depends_on`** — predecessor action ids, so branches/joins are explicit (maps to STIX `effect_refs`).
- **`asset_refs`** — which assets this action compromises (maps to STIX `asset_refs`; lets the viewer draw asset edges instead of orphaning them).

Both `stix_to_mermaid.py` and `attack_flow_viewer.html` already read `asset_refs` and condition/operator branches — so the moment the generator emits them, the diagrams gain connected assets and visible branching with no viewer change.

---

## 7. Build-sprint actions

1. **Make the generator emit STIX directly** (use `afb_to_stix.py` as the serializer spec: extension UUID, `effect_refs` edges, integer confidence, `start_refs` from roots). *Removes the `.afb` geometry problem from the hot path.*
2. **Add `depends_on` + `asset_refs` to the generator output** (§6). *Fixes branching and asset linkage at the source.*
3. **Add STIX schema validation to CI** (§3). *Catch malformed artifacts before they ship.*
4. **Adopt `stix_to_mermaid.py` / `attack_flow_viewer.html` as the standard view path.** *Drop the VS Code dependency.*
5. **If Builder editing is needed:** template-transplant only (§5). Do not build a from-scratch `.afb` serializer.

---

*Decision in one line: STIX is the artifact, Mermaid is the view, `.afb` is an optional convenience — because the spec exists for the first two and not the third, and the value was always in the semantics, not the geometry.*
