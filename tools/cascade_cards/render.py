"""Stage C - drafting (build spec §6).

Two outputs:

* :func:`build_llm_prompt` - the (system, user) messages handing the deterministic
  extract to an LLM, constrained to write prose from ONLY the supplied facts.
* :func:`render_scaffold` - a deterministic, no-LLM draft card. Every metadata field
  is already correct by construction; the prose sections are populated with the
  extracted facts (technique descriptions become the "succeeds when" raw material).
  This makes the pipeline runnable end-to-end and gives the LLM a faithful skeleton.

The frontmatter is identical in both paths - the LLM only rewrites body prose.
"""

from __future__ import annotations

import json
import textwrap
from dataclasses import asdict

from .enrich import Extract, EnrichedStep

LEVER_GLOSS = {
    "odds": "changes the odds",
    "spread": "limits how far it spreads",
    "size": "this sets the SIZE of the loss",
}


# --------------------------------------------------------------------------- #
# Frontmatter (shared)
# --------------------------------------------------------------------------- #
def _yaml_scalar(value) -> str:
    if value is None:
        return '""'
    s = str(value)
    if any(c in s for c in ':#"') or s != s.strip():
        return '"' + s.replace('"', '\\"') + '"'
    return s


def render_frontmatter(ex: Extract, card_id: str = "oic-ca-NNN") -> str:
    lines = ["---"]
    lines.append(f"id: {card_id}                 # [REVIEW] new archetype or instance? (dedupe)")
    lines.append(f'label: {_yaml_scalar(ex.label)}')
    lines.append("type: cascade_archetype")
    lines.append(f'entry: {_yaml_scalar(ex.entry_phrase)}')
    lines.append(f'terminal_impact: {_yaml_scalar(ex.terminal_phrase)}')
    lines.append(f'applies_when: {_yaml_scalar(ex.applies_when)}')
    lines.append(f'sectors: {_yaml_scalar(ex.sectors)}')
    lines.append(f"dbir_pattern: {ex.dbir_pattern}")
    lines.append(f"veris_entry: {ex.veris_entry}")
    lines.append(f"veris_terminal: {ex.veris_terminal}")
    lines.append(f'anchor_incident: {_yaml_scalar(ex.anchor_incident)}')
    lines.append(f"tags: [{', '.join(ex.tags)}]")
    lines.append("build:")
    for k, v in ex.build.items():
        lines.append(f'  {k}: {_yaml_scalar(v)}')
    lines.append("---")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Stage C-a: LLM prompt
# --------------------------------------------------------------------------- #
SYSTEM_PROMPT = textwrap.dedent(
    """\
    You are drafting an OIC grounding card from a structured attack-flow extract.
    Use ONLY the facts provided - do not add techniques, steps, actors, sectors, or
    VERIS values that are not present. Write in plain language for a non-specialist.

    - Scenario: 2-3 sentences. State that the single entry event is not the real
      problem; the damage requires the whole chain to succeed.
    - "Recognize this scenario when ...": one paragraph synthesizing the enabling
      conditions across all steps plus the topology precondition.
    - The cascade: one numbered step per extracted action, in order. Each line: what
      the attacker does, then "*Succeeds when:* <weakness/condition that lets it
      through>", then the lever tag *(odds | spread | size)*. Focus on HOW the step
      succeeds. Do NOT cite control names or framework IDs.
    - Branching: if any OR operator or condition was recorded, explain in 1-2
      sentences that alternative paths existed.
    - Odds vs. size: contrast the odds/spread steps (likelihood) with the size step
      (magnitude). Frame as different decisions.
    - Anchor: 2 sentences naming the real incident, for credibility.
    - Insert the literal token [REVIEW] wherever the extract marked a field for review,
      and never guess a value that was marked missing.
    Return only the card body markdown (no frontmatter)."""
)


def _extract_payload(ex: Extract) -> dict:
    return {
        "scenario_label": ex.label,
        "anchor_incident": ex.anchor_incident,
        "flow_description": ex.flow_description,
        "applies_when": ex.applies_when,
        "sectors": ex.sectors,
        "topology_assets": ex.assets,
        "entry": ex.entry_phrase,
        "terminal_impact": ex.terminal_phrase,
        "steps": [
            {
                "order": s.order,
                "name": s.name,
                "technique_id": s.technique_id,
                "technique_name": s.technique_name,
                "tactics": list(s.tactic_shortnames),
                "what_attacker_does": s.description,
                "succeeds_when_raw_material": s.technique_description,
                "lever": s.lever,
                "is_entry": s.is_entry,
                "is_terminal": s.is_terminal,
                "review_notes": s.review_notes,
            }
            for s in ex.steps
        ],
        "branches": ex.branches,
        "review_markers": ex.review_markers,
    }


def build_llm_prompt(ex: Extract) -> tuple[str, str]:
    """Return (system_prompt, user_message) for the Stage C LLM call."""
    user = (
        "Draft the card body from this extract. Frontmatter is generated separately; "
        "use these facts only.\n\n```json\n"
        + json.dumps(_extract_payload(ex), indent=2)
        + "\n```"
    )
    return SYSTEM_PROMPT, user


# --------------------------------------------------------------------------- #
# Stage C-b: deterministic scaffold (no LLM)
# --------------------------------------------------------------------------- #
def _succeeds_when(step: EnrichedStep) -> str:
    raw = step.technique_description or step.description
    if not raw:
        return "[REVIEW: enabling condition not in source]"
    # First sentence of the ATT&CK description as raw material; the LLM rewrites it.
    sentence = raw.split(". ")[0].strip().rstrip(".")
    return sentence[:240]


def render_scaffold(ex: Extract, card_id: str = "oic-ca-NNN") -> str:
    out: list[str] = [render_frontmatter(ex, card_id), ""]
    title = ex.label.replace("[REVIEW] ", "")
    out.append(f"## Scenario: {title}")
    out.append("")
    out.append(
        f"_DRAFT (LLM to rewrite as prose)._ The entry event - {ex.entry_phrase} - is "
        f"not the real problem. The damage ({ex.terminal_phrase}) requires the whole "
        f"chain below to succeed in sequence."
    )
    if ex.flow_description:
        out.append("")
        out.append(f"> Source flow summary: {ex.flow_description}")
    out.append("")
    out.append("**Recognize this scenario** when an organization combines the enabling "
               "conditions of the steps below with this topology: "
               + (ex.applies_when or "[REVIEW]") + ".")
    out.append("")
    out.append("### The cascade — each link must fail for the next to be reached")
    out.append("")
    for s in ex.steps:
        tid = f" ({s.technique_id})" if s.technique_id else ""
        does = s.description or (s.technique_name or s.name)
        out.append(f"{s.order}. **{s.name}**{tid} — {does}")
        out.append(f"   *Succeeds when:* {_succeeds_when(s)}. *({s.lever} — {LEVER_GLOSS[s.lever]})*")
    out.append("")
    out.append("### Branching")
    out.append("")
    if ex.branches:
        for b in ex.branches:
            where = f" (after step {b['after_step']})" if b.get("after_step") else ""
            desc = b["description"] or ("alternative path" if b["kind"] == "OR" else "conditional split")
            out.append(f"- **{b['kind']}**{where}: {desc}. Closing one weakness does not close the route.")
    else:
        out.append("- No OR operators or conditions were recorded in the source flow.")
    out.append("")
    out.append("### Odds vs. size")
    out.append("")
    odds = [s.order for s in ex.steps if s.lever in ("odds", "spread")]
    size = [s.order for s in ex.steps if s.lever == "size"]
    out.append(
        f"Steps {odds} change *how likely* the attack is to succeed (odds/spread). "
        f"Step(s) {size or '[REVIEW: size step]'} change the *size* of the loss "
        f"(magnitude driver — {ex.veris_terminal}). These are different decisions."
    )
    out.append("")
    out.append("### Anchor (real incident)")
    out.append("")
    refs = "; ".join(r.get("source_name", "") for r in ex.external_references if r.get("source_name"))
    out.append(f"{ex.anchor_incident}. {ex.flow_description}"
               + (f" (Sources: {refs}.)" if refs else ""))
    out.append("")
    return "\n".join(out)
