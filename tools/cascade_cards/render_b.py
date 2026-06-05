"""Stage C (alternate, version '-b') - plain-language prerequisites in the prose.

The cascade's "Succeeds when ..." clause is written from the lay enabling-condition
phrases produced by :mod:`enrich_b` (no M-codes). The machine-readable ``mitigations:``
frontmatter block and the "Reducing this risk" section still carry the M-codes - reused
verbatim from :mod:`render_a`.
"""

from __future__ import annotations

import json
import textwrap

from .enrich_a import ExtractA, EnrichedStepA, MitigationOption
from .control_language import control_phrase, _OVERLAP_NOTE
from .render import LEVER_GLOSS as _BASE_LEVER_GLOSS
from .render_a import render_frontmatter_a

# Add the 'dwell' lever used by '-b' for persistence / stealth steps.
LEVER_GLOSS = dict(_BASE_LEVER_GLOSS)
LEVER_GLOSS["dwell"] = "keeps the attacker present and unseen over time"

_NO_PREVENTIVE_SENTINEL = "ATT&CK lists no preventive control"
_NO_PREVENTIVE_PROSE = ("ATT&CK lists no preventive control here, so this link is caught "
                        "only by detection and response.")


def _join_clauses(clauses: list[str]) -> str:
    clauses = [c for c in clauses if c]
    if not clauses:
        return ""
    if len(clauses) == 1:
        return clauses[0]
    if len(clauses) == 2:
        return f"{clauses[0]} and {clauses[1]}"
    return ", ".join(clauses[:-1]) + f", and {clauses[-1]}"


def _succeeds_when_b(step: EnrichedStepA) -> str:
    """Compose the gate clause from the load-bearing weakness phrases (no boilerplate)."""
    weaknesses = [p for p in step.preconditions if not p.startswith(_NO_PREVENTIVE_SENTINEL)]
    no_prev = step.no_preventive or any(
        p.startswith(_NO_PREVENTIVE_SENTINEL) for p in step.preconditions)
    text = ""
    if weaknesses:
        joined = _join_clauses(weaknesses)
        text = joined[0].upper() + joined[1:]
        text = text.rstrip(".") + "."
    if no_prev:
        text = (text + " " + _NO_PREVENTIVE_PROSE).strip()
    text = text or "[REVIEW: no grounded weakness available]"
    if step.mitigation_overlap:
        text = f"{text} {_OVERLAP_NOTE}"
    return text


def render_scaffold_b(ex: ExtractA, card_id: str = "oic-ca-NNN-b") -> str:
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
        out.append(f"   *Succeeds when:* {_succeeds_when_b(s)} *({s.lever} — {LEVER_GLOSS[s.lever]})*")
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
    odds = [s.order for s in ex.steps if s.lever in ("odds", "spread", "dwell")]
    size = [s.order for s in ex.steps if s.lever == "size"]
    out.append(
        f"Steps {odds} change *how likely* the attack is to succeed (odds/spread/dwell). "
        f"Step(s) {size or '[REVIEW: size step]'} change the *size* of the loss "
        f"(magnitude driver — {ex.veris_terminal}). These are different decisions."
    )
    out.append("")
    out += _render_mitigations_section_b(ex)
    out.append("### Anchor (real incident)")
    out.append("")
    refs = "; ".join(r.get("source_name", "") for r in ex.external_references if r.get("source_name"))
    out.append(f"{ex.anchor_incident}. {ex.flow_description}"
               + (f" (Sources: {refs}.)" if refs else ""))
    out.append("")
    return "\n".join(out)


def _mit_line(m: MitigationOption) -> str:
    control = control_phrase(m.mcode) or m.name
    return (f"- **{m.name}** ({m.mcode}) — {control}. "
            f"Covers step(s) {m.covered_steps} [{m.coverage_count} gate(s)].")


def _render_mitigations_section_b(ex: ExtractA) -> list[str]:
    out = ["### Reducing this risk", ""]
    out.append("_Grounded in ATT&CK mitigations for the techniques in this scenario. "
               "Candidate options, not effectiveness estimates — the quantification layer "
               "scores how much each helps._")
    out.append("")
    likelihood = [m for m in ex.mitigation_options if m.effect in ("likelihood", "both")]
    impact = [m for m in ex.mitigation_options if m.effect in ("impact", "both")]

    out.append("**Reduce likelihood** (lower the chance the attack reaches a loss event)")
    if likelihood:
        out += [_mit_line(m) for m in likelihood]
    else:
        out.append("- None mapped from ATT&CK for the likelihood-lever steps.")
    out.append("")
    out.append("**Reduce impact** (limit how large the loss is if it happens)")
    if impact:
        out += [_mit_line(m) for m in impact]
    else:
        out.append("- None mapped from ATT&CK for the spread/size steps.")
    out.append("")
    if ex.no_preventive_mitigation_steps:
        out.append(f"_Steps with no preventive mitigation in ATT&CK "
                   f"(steps {ex.no_preventive_mitigation_steps}): rely on detection and response._")
        out.append("")
    return out


# --------------------------------------------------------------------------- #
# LLM prompt (alternate, version '-b')
# --------------------------------------------------------------------------- #
SYSTEM_PROMPT_B = textwrap.dedent(
    """\
    You are drafting an OIC grounding card from a structured attack-flow extract, for a
    NON-SPECIALIST reader. Use ONLY the facts provided - do not add techniques, steps,
    actors, sectors, VERIS values, or mitigations that are not present.

    - The cascade: one numbered step per action, in order. For each, write
      "*Succeeds when:* <one-sentence mechanism, then the load-bearing weaknesses>".
      Open with what THIS technique specifically requires (derive it from the step's name
      and `what_attacker_does` + `access_context` so two steps never share an identical
      opening clause), then state the weaknesses from `weaknesses` that let it through.
      Use only the supplied `weaknesses`; phrase them as "absent or weak", not merely
      "missing". Do NOT mention M-codes, ATT&CK, or any framework identifiers in this
      clause. End with the lever tag in parentheses (odds | dwell | spread | size).
    - Reducing this risk: render the supplied `mitigation_options` exactly, split into
      "Reduce likelihood" (effect=likelihood/both) and "Reduce impact" (effect=impact/both),
      ordered by coverage_count desc. Here you MAY show the M-code alongside the name. Do
      not add, remove, reclassify, or reorder mitigations. Note no_preventive_mitigation_steps.
    - Scenario / Recognize / Branching / Odds-vs-size / Anchor: as usual, plain language.
    - Insert the literal token [REVIEW] wherever the extract marked a field for review.
    Return only the card body markdown (no frontmatter)."""
)


def _payload_b(ex: ExtractA) -> dict:
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
                "access_context": s.access_precondition,
                "weaknesses": [p for p in s.preconditions
                               if not p.startswith(_NO_PREVENTIVE_SENTINEL)],
                "no_preventive": s.no_preventive,
                "mitigation_overlap": s.mitigation_overlap,
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


def build_llm_prompt_b(ex: ExtractA) -> tuple[str, str]:
    user = ("Draft the card body from this extract. Frontmatter is generated separately; "
            "use these facts only.\n\n```json\n" + json.dumps(_payload_b(ex), indent=2) + "\n```")
    return SYSTEM_PROMPT_B, user
