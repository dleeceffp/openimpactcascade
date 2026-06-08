"""Stage C (alternate, version '-a') - prerequisite-led cascade + grounded mitigations.

Differs from :mod:`render`:

* Each cascade step's ``*Succeeds when:*`` clause now states the **prerequisites/enabling
  conditions** (access/egress position + absent ATT&CK controls), not the first sentence
  of the technique description.
* Adds the Addendum B ``mitigations:`` frontmatter block (+ ``no_preventive_mitigation_steps``)
  and a ``### Reducing this risk`` body section split into likelihood vs impact.

Reuses v1 frontmatter helpers; does not modify the v1 pipeline.
"""

from __future__ import annotations

import json
import textwrap

from .enrich_a import ExtractA, EnrichedStepA, MitigationOption
from .render import _yaml_scalar, LEVER_GLOSS


def render_frontmatter_a(ex: ExtractA, card_id: str) -> str:
    lines = ["---"]
    lines.append(f"id: {card_id}                 # [REVIEW] new archetype or instance? (dedupe)")
    lines.append(f"label: {_yaml_scalar(ex.label)}")
    lines.append("type: cascade_archetype")
    lines.append(f"entry: {_yaml_scalar(ex.entry_phrase)}")
    lines.append(f"terminal_impact: {_yaml_scalar(ex.terminal_phrase)}")
    lines.append(f"applies_when: {_yaml_scalar(ex.applies_when)}")
    lines.append(f"sectors: {_yaml_scalar(ex.sectors)}")
    lines.append(f"dbir_pattern: {ex.dbir_pattern}")
    lines.append(f"veris_entry: {ex.veris_entry}")
    lines.append(f"veris_terminal: {ex.veris_terminal}")
    lines.append(f"anchor_incident: {_yaml_scalar(ex.anchor_incident)}")
    lines.append(f"tags: [{', '.join(ex.tags)}]")
    # Addendum B canonical, machine-readable block.
    lines.append("mitigations:")
    if ex.mitigation_options:
        for m in ex.mitigation_options:
            lines.append(f"  - id: {m.mcode}")
            lines.append(f"    name: {_yaml_scalar(m.name)}")
            lines.append(f"    effect: {m.effect}")
            lines.append(f"    covered_steps: [{', '.join(str(s) for s in m.covered_steps)}]")
            lines.append(f"    coverage_count: {m.coverage_count}")
            lines.append(f"    techniques: [{', '.join(m.techniques)}]")
    else:
        lines.append("  []")
    nps = ", ".join(str(s) for s in ex.no_preventive_mitigation_steps)
    lines.append(f"no_preventive_mitigation_steps: [{nps}]")
    lines.append("build:")
    for k, v in ex.build.items():
        lines.append(f"  {k}: {_yaml_scalar(v)}")
    lines.append("---")
    return "\n".join(lines)


def _succeeds_when_a(step: EnrichedStepA) -> str:
    return "; ".join(step.preconditions)


def render_scaffold_a(ex: ExtractA, card_id: str = "oic-ca-NNN-a") -> str:
    out: list[str] = [render_frontmatter_a(ex, card_id), ""]
    title = ex.label.replace("[REVIEW] ", "")
    out.append(f"## Scenario: {title}")
    out.append("")
    out.append(
        f"_DRAFT (LLM to rewrite as prose)._ The entry event - {ex.entry_phrase} - is "
        f"not the real problem. The damage ({ex.terminal_phrase}) requires the whole "
        f"chain below to succeed in sequence, and each link succeeds only when specific "
        f"prerequisites are met."
    )
    if ex.flow_description:
        out.append("")
        out.append(f"> Source flow summary: {ex.flow_description}")
    out.append("")
    out.append("**Recognize this scenario** when an organization combines the prerequisites "
               "of the steps below with this topology: " + (ex.applies_when or "[REVIEW]") + ".")
    out.append("")
    out.append("### The cascade — each link succeeds only when its prerequisites hold")
    out.append("")
    for s in ex.steps:
        tid = f" ({s.technique_id})" if s.technique_id else ""
        does = s.description or (s.technique_name or s.name)
        out.append(f"{s.order}. **{s.name}**{tid} — {does}")
        out.append(f"   *Succeeds when:* {_succeeds_when_a(s)}. *({s.lever} — {LEVER_GLOSS[s.lever]})*")
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
    out += _render_mitigations_section(ex)
    out.append("### Anchor (real incident)")
    out.append("")
    refs = "; ".join(r.get("source_name", "") for r in ex.external_references if r.get("source_name"))
    out.append(f"{ex.anchor_incident}. {ex.flow_description}"
               + (f" (Sources: {refs}.)" if refs else ""))
    out.append("")
    return "\n".join(out)


def _render_mitigations_section(ex: ExtractA) -> list[str]:
    out = ["### Reducing this risk", ""]
    out.append("_Grounded in ATT&CK mitigations for the techniques in this scenario. "
               "Candidate options, not effectiveness estimates — the quantification layer "
               "scores how much each helps._")
    out.append("")
    likelihood = [m for m in ex.mitigation_options if m.effect in ("likelihood", "both")]
    impact = [m for m in ex.mitigation_options if m.effect in ("impact", "both")]

    out.append("**Reduce likelihood** (lower the chance the attack reaches a loss event)")
    if likelihood:
        for m in likelihood:
            out.append(f"- **{m.name} ({m.mcode})** — covers step(s) {m.covered_steps} "
                       f"[{m.coverage_count} gate(s)].")
    else:
        out.append("- None mapped from ATT&CK for the likelihood-lever steps.")
    out.append("")
    out.append("**Reduce impact** (limit how large the loss is if it happens)")
    if impact:
        for m in impact:
            out.append(f"- **{m.name} ({m.mcode})** — covers step(s) {m.covered_steps} "
                       f"[{m.coverage_count} gate(s)].")
    else:
        out.append("- None mapped from ATT&CK for the spread/size steps.")
    out.append("")
    if ex.no_preventive_mitigation_steps:
        out.append(f"_Steps with no preventive mitigation in ATT&CK "
                   f"(steps {ex.no_preventive_mitigation_steps}): rely on detection and response._")
        out.append("")
    return out


# --------------------------------------------------------------------------- #
# LLM prompt (alternate)
# --------------------------------------------------------------------------- #
SYSTEM_PROMPT_A = textwrap.dedent(
    """\
    You are drafting an OIC grounding card from a structured attack-flow extract.
    Use ONLY the facts provided - do not add techniques, steps, actors, sectors,
    VERIS values, or mitigations that are not present.

    - Scenario / Recognize / Branching / Anchor: as in the standard card.
    - The cascade: one numbered step per action, in order. For each, write
      "*Succeeds when:* <prerequisites>" using the supplied `preconditions` only -
      these are the enabling conditions (access/egress position and the absent ATT&CK
      controls). Focus on the PREREQUISITES that let the step through, not on what the
      attacker does. Do NOT cite control framework IDs in this clause.
    - Reducing this risk: render the supplied `mitigation_options` exactly. Split into
      "Reduce likelihood" (effect=likelihood/both) and "Reduce impact" (effect=impact/both),
      ordered by coverage_count desc. You may rephrase each mitigation's description into
      plain language, but must NOT add, remove, reclassify, or reorder mitigations, and
      must keep every M-code. Note the no_preventive_mitigation_steps verbatim.
    - Insert the literal token [REVIEW] wherever the extract marked a field for review.
    Return only the card body markdown (no frontmatter)."""
)


def _payload_a(ex: ExtractA) -> dict:
    return {
        "scenario_label": ex.label,
        "anchor_incident": ex.anchor_incident,
        "flow_description": ex.flow_description,
        "applies_when": ex.applies_when,
        "entry": ex.entry_phrase,
        "terminal_impact": ex.terminal_phrase,
        "steps": [
            {
                "order": s.order, "name": s.name, "technique_id": s.technique_id,
                "technique_name": s.technique_name, "tactics": list(s.tactic_shortnames),
                "what_attacker_does": s.description,
                "preconditions": s.preconditions,
                "absent_controls": s.absent_controls,
                "no_preventive": s.no_preventive,
                "lever": s.lever,
            }
            for s in ex.steps
        ],
        "branches": ex.branches,
        "mitigation_options": [
            {
                "id": m.mcode, "name": m.name, "description": m.description,
                "effect": m.effect, "covered_steps": m.covered_steps,
                "coverage_count": m.coverage_count, "techniques": m.techniques,
            }
            for m in ex.mitigation_options
        ],
        "no_preventive_mitigation_steps": ex.no_preventive_mitigation_steps,
        "review_markers": ex.review_markers,
    }


def build_llm_prompt_a(ex: ExtractA) -> tuple[str, str]:
    user = ("Draft the card body from this extract. Frontmatter is generated separately; "
            "use these facts only.\n\n```json\n" + json.dumps(_payload_a(ex), indent=2) + "\n```")
    return SYSTEM_PROMPT_A, user
