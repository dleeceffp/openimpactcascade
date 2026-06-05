"""Stage B (alternate, version '-a') - prerequisite-grounded enrichment + mitigations.

Two changes over :mod:`enrich`:

1. **Grounded preconditions per step.** Instead of leaning on the first sentence of the
   technique description (what the attacker *does*), each step now carries explicit
   *enabling conditions* - the prerequisites a step needs to succeed:
     * an access/position precondition derived from the step's ATT&CK tactic
       (e.g. outbound egress for C2, network reachability + valid creds for lateral
       movement, a local flaw to abuse for privilege escalation), and
     * the *absence* of the protective controls ATT&CK itself lists for the technique
       (the inverse of its mitigations) - "succeeds when none of these are in place".
   Both are sourced from pinned data; nothing is invented.

2. **Grounded mitigations block** (Addendum B): a deduplicated, lever-classified list of
   ATT&CK M-code mitigations for the techniques present in this flow, plus the steps
   ATT&CK marks as not preventable (M1056 Pre-compromise).

This module does not modify the v1 pipeline; it reuses v1 helper functions.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Optional

from .afb import ParsedFlow
from .config import VERSIONS
from .resources import GroundingIndex, IMPACT_TACTIC_ID
from .mitigations import Mitigation, MitigationIndex
from .enrich import (
    REVIEW, SPREAD_TACTICS,
    _classify_lever, _plain_phrase, _pick_veris, _dbir_pattern,
    _derive_tags, _derive_sectors, _applies_when, _anchor_incident, _step_order,
)

# Access / position precondition by ATT&CK tactic (deterministic, grounded in the
# step's tactic placement). These describe what the attacker must already have for
# the step to be reachable - the prerequisite, not the action.
TACTIC_PRECONDITION = {
    "reconnaissance": "no prior access is needed - the attacker works from outside, against information the target exposes",
    "resource-development": "the attacker can stand up or acquire infrastructure/tooling beforehand, off the victim's network",
    "initial-access": "a delivery path into the environment is open (a user reachable by email/web, or an internet-exposed service)",
    "execution": "the attacker can get code to actually run on a host (a user opens the payload, or a service executes it)",
    "persistence": "the attacker can write to a location that survives reboot/logon (autostart keys, services, scheduled tasks)",
    "privilege-escalation": "a local flaw or misconfiguration exists to abuse for higher privileges",
    "defense-evasion": "the attacker already has enough rights to alter or hide from defenses, and those defenses are tamperable",
    "stealth": "the attacker already has enough rights to alter or hide from defenses, and those defenses are tamperable",
    "defense-impairment": "the attacker holds rights sufficient to disable or degrade security tooling",
    "credential-access": "the attacker can reach credential stores or memory (often requiring local admin on the host)",
    "discovery": "the attacker has a foothold from which to enumerate hosts, accounts, and services",
    "lateral-movement": "other hosts are network-reachable and valid credentials (or a trust path) exist to reach them",
    "collection": "the attacker can reach the target data at rest or in transit",
    "command-and-control": "outbound network egress to the internet is permitted, so the host can reach the attacker's C2",
    "exfiltration": "an outbound path to the internet exists to move data out",
    "impact": "the attacker already has broad access to the target assets (servers, shares, or backups)",
}


@dataclass
class EnrichedStepA:
    order: int
    instance: str
    name: str
    technique_id: Optional[str]
    technique_name: Optional[str]
    tactic_shortnames: tuple[str, ...]
    tactic_ids: tuple[str, ...]
    description: str
    technique_description: str
    veris_candidates: list[str]
    lever: str
    is_entry: bool
    is_terminal: bool
    is_impact: bool
    asset_names: list[str]
    # alternate additions
    access_precondition: str
    absent_controls: list[str]        # "M1017 User Training", ... (grounded raw material)
    preconditions: list[str]          # assembled, human/LLM-facing enabling conditions
    mitigations: list[Mitigation]
    no_preventive: bool
    review_notes: list[str] = field(default_factory=list)
    mitigation_overlap: bool = False  # '-b': two load-bearing weaknesses collapsed as semantically redundant


@dataclass
class MitigationOption:
    """A de-duplicated, lever-classified mitigation candidate (Addendum B §4-5)."""

    mcode: str
    name: str
    description: str
    effect: str                       # likelihood | impact | both
    covered_steps: list[int]
    coverage_count: int
    techniques: list[str]
    levers_touched: list[str]


@dataclass
class ExtractA:
    source_file: str
    flow_name: str
    flow_description: str
    scope: Optional[str]
    author: Optional[str]
    created: Optional[str]
    anchor_incident: str
    external_references: list[dict]
    steps: list[EnrichedStepA]
    branches: list[dict]
    assets: dict[str, str]
    entry_phrase: str
    terminal_phrase: str
    veris_entry: str
    veris_terminal: str
    dbir_pattern: str
    tags: list[str]
    sectors: str
    applies_when: str
    label: str
    # alternate additions
    mitigation_options: list[MitigationOption]
    no_preventive_mitigation_steps: list[int]
    review_markers: list[str] = field(default_factory=list)
    build: dict = field(default_factory=dict)


# lever -> FAIR-aligned remediation bucket (Addendum B §4.3)
_LIKELIHOOD_LEVERS = {"odds", "dwell"}
_IMPACT_LEVERS = {"spread", "size"}


def _effect_from_levers(levers: set[str]) -> str:
    has_l = bool(levers & _LIKELIHOOD_LEVERS)
    has_i = bool(levers & _IMPACT_LEVERS)
    if has_l and has_i:
        return "both"
    if has_i:
        return "impact"
    return "likelihood"


def _build_preconditions(access: str, absent: list[str], no_preventive: bool) -> list[str]:
    pre: list[str] = []
    if access:
        pre.append(access)
    if absent:
        names = "; ".join(absent)
        pre.append(f"the controls ATT&CK lists for this technique are not in place ({names})")
    if no_preventive:
        pre.append("ATT&CK lists no preventive control for this step - it is stopped only by detection and response")
    if not pre:
        pre.append("[REVIEW: no grounded precondition available]")
    return pre


def enrich_a(flow: ParsedFlow, index: GroundingIndex, mitigations: MitigationIndex) -> ExtractA:
    entry_set = set(flow.entry_steps)
    terminal_set = set(flow.terminal_steps)
    review_markers: list[str] = []

    enriched: list[EnrichedStepA] = []
    for step in flow.steps:
        info = index.attack.resolve(step.technique_id, step.technique_ref)
        name_matched = False
        if info is None and not step.technique_id and not step.technique_ref:
            info = index.attack.by_name(step.name)  # name-only flow fallback
            name_matched = info is not None
        # Effective technique id for downstream lookups (prefer the resolved one).
        eff_tid = step.technique_id or (info.technique_id if info else None)
        tactics = info.tactic_shortnames if info else ()
        ta_ids = info.tactic_ids if info else ()
        is_impact = IMPACT_TACTIC_ID in ta_ids or (eff_tid in {"T1486", "T1485", "T1490", "T1489", "T1491"})
        is_terminal = step.instance in terminal_set or is_impact
        lever = _classify_lever(tactics, is_impact)
        veris_caps = index.ctid.veris_for(eff_tid)

        step_mits = mitigations.for_technique(eff_tid)
        no_prev = mitigations.is_no_preventive(eff_tid)
        access = TACTIC_PRECONDITION.get(tactics[0], "") if tactics else ""
        absent = [f"{m.mcode} {m.name}" for m in step_mits]
        preconditions = _build_preconditions(access, absent, no_prev)

        notes: list[str] = []
        if step.technique_id and not info:
            notes.append(f"technique {step.technique_id} not found in pinned ATT&CK")
            review_markers.append(f"step {step.order}: unknown technique {step.technique_id}")
        elif info and info.revoked:
            notes.append(f"technique {step.technique_id} is revoked in pinned ATT&CK 19.1")
            review_markers.append(f"step {step.order}: {step.technique_id} revoked in ATT&CK 19.1 - confirm current id")
        if not access and tactics:
            review_markers.append(f"step {step.order}: no precondition template for tactic {tactics[0]}")
        if not step_mits and not no_prev:
            notes.append("no ATT&CK mitigation mapped for this technique")
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
            access_precondition=access, absent_controls=absent,
            preconditions=preconditions, mitigations=step_mits, no_preventive=no_prev,
            review_notes=notes,
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
        "card_variant": "a (prerequisite + grounded mitigations)",
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


def _aggregate_mitigations(steps: list[EnrichedStepA]) -> tuple[list[MitigationOption], list[int]]:
    agg: dict[str, dict] = {}
    for s in steps:
        for m in s.mitigations:
            entry = agg.setdefault(m.mcode, {
                "name": m.name, "description": m.description,
                "steps": [], "techniques": [], "levers": set(),
            })
            if s.order not in entry["steps"]:
                entry["steps"].append(s.order)
            if s.technique_id and s.technique_id not in entry["techniques"]:
                entry["techniques"].append(s.technique_id)
            entry["levers"].add(s.lever)

    options = [
        MitigationOption(
            mcode=mc, name=d["name"], description=d["description"],
            effect=_effect_from_levers(d["levers"]),
            covered_steps=sorted(d["steps"]), coverage_count=len(d["steps"]),
            techniques=d["techniques"], levers_touched=sorted(d["levers"]),
        )
        for mc, d in agg.items()
    ]
    # Higher coverage first (prioritization hint, §4.4), then stable by M-code.
    options.sort(key=lambda o: (-o.coverage_count, o.mcode))
    no_prev_steps = sorted(s.order for s in steps if s.no_preventive)
    return options, no_prev_steps
