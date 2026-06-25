# Implementation Brief — Terminal-Anchored Reachability Generation

**For:** a coding agent working in `tools/attack_flow_workbench/`
**Implements:** `OIC-DESIGN-2026-044` (terminal-anchored reachability analysis), within the GENERATION pipeline. Inherits `OIC-DESIGN-2026-043` (STIX canonical, Mermaid view, firewall) and `OIC-DESIGN-2026-042` (four entry archetypes).
**Goal:** Given an asset/terminal, generate **3–5 (configurable) candidate routes** from different entry points to that same outcome. Each generation emits **a STIX bundle (the path) + a markdown summary (the reasoning)**. Entry points with **no credible path** are captured as narrative with **flip conditions / monitored assumptions** — not as bundles. Support a **4-way model-selection matrix** (light/heavy × primary/alternate).
**Reference implementations to reuse (do not reinvent):** `afb_to_stix.py` (STIX object shapes), `stix_to_mermaid.py` (STIX→Mermaid), `attack_flow_viewer.html` (viewer). Read `OIC-DESIGN-2026-044` in full before starting — the verdict taxonomy, conditional-negative discipline, and firewall are normative.

---

## 0. Before you edit — orient

1. Read `attack_flow_generator.py`, `formatter.py`, `cli.py`, `config.py`, `corpus_grounding.py`, `web_search.py`, and `mitre_loader.py` in full.
2. Read `OIC-DESIGN-2026-044` §4 (three-verdict taxonomy), §5 (conditional-negative discipline), §6 (convergence), §7 (firewall). These are the spec for behavior.
3. Note the existing single-flow path; this brief changes it to terminal-anchored multi-route. Do not delete the grounding modules — reuse them.

---

## 1. Inputs and the generation model

The fixed anchor is the **terminal** (the asset's compromise). The generator works **backward** from the terminal, enumerating routes by entry point. Concretely the request carries:

- `asset` / `terminal` — what's being protected and the compromise outcome (the anchor).
- `industry`, `region`, `org_size` — existing grounding inputs.
- `named_entries` — entry vectors the user explicitly named or fears (e.g. "guest WiFi"). These are **always evaluated** and always get a verdict.
- `min_paths` (default 2), `target_paths` (default 3–5), `max_paths` (configurable upper bound, see §3).

The four entry archetypes from `2026-042` (phishing / remote access / physical intrusion / over-provisioned AI agent) are the default seeds for diversity.

---

## 2. The three-verdict output (per candidate entry)

For each candidate entry against the fixed terminal, produce exactly one verdict (see `2026-044` §4):

- **`credible`** → emit a STIX Attack Flow bundle (the path) + its markdown summary.
- **`different_terminal`** → narrative note: this entry doesn't reach *this* asset but threatens X; optionally seed a separate run for terminal X.
- **`no_credible_path`** → narrative only (NO bundle): the verdict plus its **monitored assumptions** and **flip conditions** (§5 of the doc, and §5 below).

**Load-bearing diversity (hard rule):** credible routes must differ through their *approach*, not just the entry node. Implement a diversity check (`R4`): compute overlap of the action/technique sequence across the credible routes; if routes collapse to a near-identical middle, regenerate or drop the duplicate. A batch of near-duplicates is a defect.

---

## 3. Path-count bounds

- **Minimum 2** credible paths whenever ≥2 credible paths exist. Rationale baked into a code comment: *there is never only one path* — emitting a single path falsely implies the terminal has one route. If only one credible path genuinely exists, still surface it, but the markdown must explicitly state that only one credible route was found under the considered entries (not that only one exists).
- **Default target 3–5.**
- **`max_paths` configurable** (config/env). If a reviewer has time/budget to evaluate a dozen scenarios, the tool must support it — do not hard-cap below the configured value.
- **Do not pad.** If fewer credible paths exist than `target_paths`, emit fewer plus honest `no_credible_path` / `different_terminal` verdicts for the rest. Padding to hit a number reintroduces fabrication (`2026-044` §9).

---

## 4. Threat-intelligence bound on *discovered* entries (anti-hallucination)

The tool may **proactively surface entries the user did not name** (affirmative blind-spots — `2026-044` §9), but to avoid burning tokens on hallucinated vectors, a **discovered** entry must clear an evidence bar before it is considered:

> A proactively-added entry point must have been **observed in a real breach or disruption event**, OR be an **active, documented research area**.

- Examples: phishing, exposed RDP/VPN, supply-chain compromise, insider misuse → observed, allowed. Quantum decryption → not observed in breaches, but an active research area; allowed **only when relevant to the terminal** (e.g. the asset's protection depends on encryption). A purely speculative, unattested vector → rejected.
- Implementation: ground discovered entries against `corpus_grounding` (DBIR patterns) and `web_search` (recent incidents / research). An entry that cannot be tied to an observed event or a named research area is **dropped, not generated**. Tag each discovered entry with its evidence basis (`observed` | `research`) and cite the source in the markdown.
- **User-named entries bypass this bar** — they are always evaluated and always get a verdict (including `no_credible_path`), because ruling out a named fear is itself valuable. The evidence bar applies only to entries the *tool* adds.
- **No proactive negatives:** the tool volunteers only *affirmative* discovered entries (credible blind-spots). It does not speculatively rule out vectors the user didn't raise (`2026-044` §9). Negatives are produced only for user-named/feared entries.

---

## 5. The markdown summary (the reasoning artifact)

Each generation produces a markdown summary alongside the bundles. This is where the narrative the diagram can't carry lives. Required sections:

- **Header:** asset/terminal, context (industry/region/size), model used, generated-at.
- **Per credible route:** the entry, a prose walk of the path, the targeted assets, confidence, and the evidence basis. The *diagram* (Mermaid, from the bundle) carries the path shape; the markdown carries the why.
- **"Monitored Assumptions" section (the high-value artifact):** for every `no_credible_path` verdict, a structured entry:
  - the entry point evaluated,
  - **why the path ends mid-way** (where the chain breaks and why it can't reach the terminal),
  - the **monitored assumptions** — the conditions assumed true to reach the negative verdict,
  - the **flip condition(s)** — the specific fact whose change would make the route credible ("if the guest network is not isolated, this becomes credible").
  - Frame these explicitly as *living risk-register entries*: documented assumptions with a built-in re-evaluation trigger, not closed verdicts.
- **Different-terminal notes:** entries that threaten something other than this asset, and what.
- **Convergence note (structural only):** where credible routes share nodes before the terminal (`2026-044` §6). State the convergence as a fact; do **not** prescribe controls.

The visual handles the entry→terminal path; the markdown handles everything too cumbersome to overlay on a diagram — especially the monitored assumptions for the ruled-out entries. A user seeing a path that ends mid-way reads the markdown to learn *why* and *what to watch for*.

---

## 6. STIX + viewer output (per `2026-043`)

- Each `credible` route → its own STIX 2.1 bundle (use `afb_to_stix.py` object shapes: extension UUID, `attack-action` with `effect_refs`/`asset_refs`, integer `confidence`, `start_refs` from roots, no nulls). Tag every bundle with the shared terminal so the set can be grouped.
- Copy `attack_flow_viewer.html` into the output directory each run; `stix_to_mermaid.py` available for headless rendering.
- **Firewall (hard rule):** bundles and markdown carry **observed shape only** — actions, assets, edges, and (for negatives) structural preconditions/flip-conditions. **No `succeeds when` control gates** anywhere in generated output; that belongs to the compression pipeline (`OIC-DESIGN-2026-002`). The monitored-assumptions are *structural preconditions for a route's existence*, written as such — not control prescriptions.

### Output directory layout (per generation run)

```
generated/attack_flows/<asset-slug>_<timestamp>/
  ├── route_01_<entry-slug>.json        # STIX bundle (credible route)
  ├── route_02_<entry-slug>.json
  ├── ...
  ├── summary.md                        # reasoning + monitored assumptions
  └── attack_flow_viewer.html           # copied in for viewing
```

---

## 7. Model-selection matrix (4 choices)

Provide a **2×2 matrix**: weight (light | heavy) × provider (primary | alternate). Default mapping (overridable):

| | primary | alternate |
|---|---|---|
| **light** | Claude Sonnet | Gemini (light tier) |
| **heavy** | Claude Opus | Gemini (heavy tier) |

Requirements:
- Selectable via **config file and/or env variables** (env overrides config). E.g. `OIC_MODEL_WEIGHT=heavy`, `OIC_MODEL_PROVIDER=primary`, with config-file fallback.
- Abstract the model call behind a small **provider interface** (e.g. `LLMProvider.generate(messages, **opts)`) with `AnthropicProvider` and `GeminiProvider` implementations, so adding a provider later is a new class, not edits scattered through the generator.
- Map the 2×2 selection to concrete model IDs in one config table (don't hardcode model strings in the generator). Keep the existing Anthropic path working as the default (light/primary or heavy/primary per config).
- Record the chosen model in the markdown summary header and in the bundle's `x_oic_context`/identity, so every artifact is traceable to the model that produced it.
- The alternate provider requires its own API key via env; if absent, fall back to primary with a logged warning rather than failing.

---

## 8. Acceptance criteria

1. A run with a terminal + named entries produces a per-run directory (§6) containing ≥`min_paths` credible-route bundles (when ≥2 credible paths exist), a `summary.md`, and the viewer.
2. Every credible bundle passes STIX validation (`stix2.parse(..., allow_custom=True)`, one `attack-flow`, no dangling refs, no nulls, integer confidence) and renders in the viewer with connected assets.
3. `summary.md` contains a **Monitored Assumptions** section for every `no_credible_path` verdict, each with: where the path breaks, the assumptions, and the flip condition(s).
4. A user-named entry that is not credible produces a `no_credible_path` verdict (never silently dropped).
5. A proactively-discovered entry with no observed/research basis is **dropped** (not generated); discovered entries that are generated cite their evidence basis.
6. `target_paths` and `max_paths` are honored; `max_paths` can be raised (e.g. to 12) via config/env and the tool generates accordingly; the tool never pads beyond genuinely credible/observed routes.
7. The 4-way model matrix is selectable via config and env; the chosen model is recorded in every artifact; missing alternate key falls back to primary with a warning.
8. No `succeeds when` / control-prescription language appears in any bundle or markdown (grep the output).
9. No unconditional "safe"/"impossible"/"cannot" language in negatives — they are conditional and flip-conditioned (eval this; see `2026-044` §5, R3).

---

## 9. Out of scope — do not do

- Do **not** add `succeeds when` control gates to generated artifacts (firewall).
- Do **not** issue unconditional negatives or proactive all-clears for un-named vectors (`2026-044` §9).
- Do **not** hand-serialize `.afb` (`2026-043`); STIX only, viewer for rendering.
- Do **not** merge generation with compression.
- Do **not** hardcode model strings in the generator; route them through the config matrix.
- Do **not** change the corpus/grounding sources or token limits beyond what the model matrix requires.

---

## 10. Verification before the PR

1. `python -m pytest tools/attack_flow_workbench/` with new tests for: verdict taxonomy, min/max path bounds, the evidence bar on discovered entries, the conditional-negative eval, and the model-matrix selection.
2. Live run: a healthcare "protect patient records" terminal with named entry "guest WiFi" → confirm guest WiFi yields a `no_credible_path` with a flip condition in `summary.md`, and ≥2 credible routes (e.g. phishing, remote access) emit as bundles that render.
3. Live run with `max_paths=8` → confirm more routes generate when credible, without padding.
4. Swap model via env (`OIC_MODEL_WEIGHT=heavy`) → confirm the summary header records the heavier model.
5. Grep output for control-prescription and unconditional-negative language → none.

---

## Why this shape (context, not a task)

The product is a **corrected, all-hazards threat picture**, not a pile of attack flows. The proving (credible routes, including unorthodox blind-spots) and the disproving (ruled-out fears, captured as monitored assumptions with flip conditions) are equally the deliverable. The visual carries the path; the markdown carries the reasoning the path can't hold — above all the monitored assumptions, which turn a path that "ends mid-way" into an actionable, watch-this risk-register entry. The evidence bar keeps discovered entries grounded so tokens aren't spent on hallucinated vectors, while user fears are always answered. And the model matrix lets the same capability run cheap-and-fast or thorough-and-deep depending on the budget for the question at hand.
