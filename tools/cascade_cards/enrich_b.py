"""Stage B (alternate, version '-b') - plain-language prerequisites.

Same grounding as '-a' (tactic-based access precondition + the *absence* of the
technique's ATT&CK mitigations), but the mitigation references are translated into
lay enabling-condition phrases via :mod:`control_language`, so no M-codes appear in
the cascade prose. The machine-readable ``mitigations:`` block keeps the M-codes.

Also introduces the ``dwell`` lever for persistence steps (the attacker staying
present across reboots), which the addendum's lever taxonomy includes under
"likelihood". Reuses the '-a' dataclasses and aggregation.
"""

from __future__ import annotations

import datetime as _dt
from typing import Optional

from .afb import ParsedFlow
from .config import VERSIONS
from .resources import GroundingIndex, IMPACT_TACTIC_ID
from .mitigations import MitigationIndex
from .control_language import weakness_phrase, select_load_bearing, is_preventable
from .enrich import (
    REVIEW, SPREAD_TACTICS,
    _plain_phrase, _pick_veris, _dbir_pattern,
    _derive_tags, _derive_sectors, _applies_when, _anchor_incident, _step_order,
)
from .enrich_a import (
    EnrichedStepA, MitigationOption, ExtractA, TACTIC_PRECONDITION, _aggregate_mitigations,
)


# Tactics whose role is "stay present / stay unseen" -> dwell. Checked before spread so a
# multi-tactic technique (e.g. Scheduled Task: execution + persistence + priv-esc) is bucketed
# by its persistence/stealth role rather than whichever tactic the heuristic hits first.
DWELL_TACTICS = {"persistence", "defense-evasion", "stealth"}


def _classify_lever_b(tactics: tuple[str, ...], is_impact: bool) -> str:
    if is_impact:
        return "size"
    if any(t in DWELL_TACTICS for t in tactics):
        return "dwell"
    if any(t in SPREAD_TACTICS for t in tactics):
        return "spread"
    return "odds"


def enrich_b(flow: ParsedFlow, index: GroundingIndex, mitigations: MitigationIndex) -> ExtractA:
    entry_set = set(flow.entry_steps)
    terminal_set = set(flow.terminal_steps)
    review_markers: list[str] = []

    enriched: list[EnrichedStepA] = []
    for step in flow.steps:
        info = index.attack.resolve(step.technique_id, step.technique_ref)
        name_matched = False
        if info is None and not step.technique_id and not step.technique_ref:
            info = index.attack.by_name(step.name)
            name_matched = info is not None
        eff_tid = step.technique_id or (info.technique_id if info else None)
        tactics = info.tactic_shortnames if info else ()
        ta_ids = info.tactic_ids if info else ()
        is_impact = IMPACT_TACTIC_ID in ta_ids or (eff_tid in {"T1486", "T1485", "T1490", "T1489", "T1491"})
        is_terminal = step.instance in terminal_set or is_impact
        lever = _classify_lever_b(tactics, is_impact)
        veris_caps = index.ctid.veris_for(eff_tid)

        step_mits = mitigations.for_technique(eff_tid)
        no_prev = mitigations.is_no_preventive(eff_tid)

        # Access context kept only as a hint for the Stage-C LLM mechanism lead; it is NOT
        # rendered as a boilerplate stem in the scaffold (that repeated on every step).
        access = TACTIC_PRECONDITION.get(tactics[0], "") if tactics else ""
        all_mcodes = [m.mcode for m in step_mits]
        raw_absent = [f"{m.mcode} {m.name}" for m in step_mits]  # traceability for the report
        if any(not is_preventable(mc) for mc in all_mcodes):
            no_prev = True
        # Prune to the one-to-three load-bearing weaknesses; translate to plain phrases.
        load_bearing, overlap = select_load_bearing(all_mcodes, cap=3)
        weaknesses = [w for w in (weakness_phrase(mc) for mc in load_bearing) if w]
        preconditions = _build_preconditions_b(weaknesses, no_prev)

        notes: list[str] = []
        if step.technique_id and not info:
            notes.append(f"technique {step.technique_id} not found in pinned ATT&CK")
            review_markers.append(f"step {step.order}: unknown technique {step.technique_id}")
        elif info and info.revoked:
            notes.append(f"technique {step.technique_id} is revoked in pinned ATT&CK 19.1")
            review_markers.append(f"step {step.order}: {step.technique_id} revoked in ATT&CK 19.1 - confirm current id")
        if not access and tactics:
            review_markers.append(f"step {step.order}: no precondition template for tactic {tactics[0]}")
        if not weaknesses and not no_prev:
            notes.append("no ATT&CK mitigation mapped for this technique")
        if overlap:
            notes.append("load-bearing weaknesses collapsed for semantic overlap - review")
            review_markers.append(f"step {step.order}: potential_mitigation overlap - review the gate weaknesses")
        if name_matched:
            notes.append(f"technique inferred from step name -> {eff_tid}; confirm")
            review_markers.append(f"step {step.order}: technique inferred from name -> {eff_tid}")

        enriched.append(EnrichedStepA(
            order=step.order, instance=step.instance,
            name=step.name or (info.name if info else "Unnamed step"),
            technique_id=eff_tid,
            technique_name=info.name if info else None,
            tactic_shortnames=tactics, tactic_ids=ta_ids,
            description=step.description,
            technique_description=info.description if info else "",
            veris_candidates=veris_caps, lever=lever,
            is_entry=step.instance in entry_set, is_terminal=is_terminal, is_impact=is_impact,
            asset_names=step.asset_names,
            access_precondition=access, absent_controls=raw_absent,
            preconditions=preconditions, mitigations=step_mits, no_preventive=no_prev,
            review_notes=notes, mitigation_overlap=overlap,
        ))

    for es in enriched:
        if es.lever == "size":
            es.review_notes.append("size step = magnitude driver; confirm (human review)")

    entry_steps = [s for s in enriched if s.is_entry] or enriched[:1]
    impact_steps = [s for s in enriched if s.is_impact]
    terminal_steps = impact_steps or [s for s in enriched if s.is_terminal] or enriched[-1:]

    entry_phrase = _plain_phrase(entry_steps[0]) if entry_steps else "[REVIEW: entry]"
    terminal_phrase = _plain_phrase(terminal_steps[0]) if terminal_steps else "[REVIEW: terminal]"
    veris_entry = _pick_veris(entry_steps[0], index, False, review_markers, "veris_entry") if entry_steps else "[REVIEW: no mapping]"
    veris_terminal = _pick_veris(terminal_steps[0], index, True, review_markers, "veris_terminal") if terminal_steps else "[REVIEW: no mapping]"

    dbir_pattern = _dbir_pattern(enriched, entry_steps, index)
    if dbir_pattern.startswith("[REVIEW"):
        review_markers.append("dbir_pattern: no rule matched")

    tags = _derive_tags(enriched)
    sectors = _derive_sectors(flow)
    if sectors.endswith(REVIEW):
        review_markers.append("sectors: could not infer from flow text")
    applies_when = _applies_when(flow, enriched)
    review_markers.append("applies_when: confirm generalization scope (human review)")
    label = f"[REVIEW] {flow.name}"
    review_markers.append("label: confirm archetype name / dedupe against existing cards")

    options, no_prev_steps = _aggregate_mitigations(enriched)

    build = {
        "source_flow": flow.source_file,
        "attack_flow_schema": VERSIONS["attack_flow_schema"],
        "attack_version": VERSIONS["attack_version"],
        "veris_version": VERSIONS["veris_version"],
        "mapping_version": VERSIONS["mapping_version"],
        "card_variant": "b (plain-language prerequisites; M-codes only in mitigations block)",
        "generated": _dt.date.today().isoformat(),
    }
    branches = [
        {"kind": b.kind, "description": b.description, "after_step": _step_order(enriched, b.after_step)}
        for b in flow.branches
    ]

    return ExtractA(
        source_file=flow.source_file, flow_name=flow.name, flow_description=flow.description,
        scope=flow.scope, author=flow.author, created=flow.created,
        anchor_incident=_anchor_incident(flow), external_references=flow.external_references,
        steps=enriched, branches=branches, assets=flow.assets,
        entry_phrase=entry_phrase, terminal_phrase=terminal_phrase,
        veris_entry=veris_entry, veris_terminal=veris_terminal,
        dbir_pattern=dbir_pattern, tags=tags, sectors=sectors,
        applies_when=applies_when, label=label,
        mitigation_options=options, no_preventive_mitigation_steps=no_prev_steps,
        review_markers=review_markers, build=build,
    )


_NO_PREVENTIVE_NOTE = ("ATT&CK lists no preventive control for this step - it is stopped "
                       "only by detection and response")


def _build_preconditions_b(weaknesses: list[str], no_preventive: bool) -> list[str]:
    """The one-to-three load-bearing weakness phrases that gate this step (no boilerplate)."""
    pre: list[str] = list(weaknesses)
    if no_preventive:
        pre.append(_NO_PREVENTIVE_NOTE)
    if not pre:
        pre.append("[REVIEW: no grounded weakness available]")
    return pre
