"""Stage B - enrichment & mapping (build spec §5), producing the structured Extract.

Resolves technique names/tactics, maps techniques -> VERIS, derives the DBIR pattern,
and classifies each step's lever (odds / spread / size). All deterministic. Wherever a
value cannot be resolved from pinned data, a ``[REVIEW: ...]`` token is emitted - the
code never invents a technique, VERIS value, tactic, or pattern.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Optional

from .afb import ParsedFlow, Step
from .config import VERSIONS
from .resources import GroundingIndex, IMPACT_TACTIC_ID, TechniqueInfo

# Lever classification by tactic (§5).
SPREAD_TACTICS = {"privilege-escalation", "lateral-movement", "credential-access"}
DBIR_PATTERNS = {
    "basic_web_application_attacks", "social_engineering", "system_intrusion",
    "privilege_misuse", "denial_of_service", "miscellaneous_errors",
    "lost_and_stolen_assets", "everything_else",
}
WEB_ENTRY_TECHNIQUES = {"T1190", "T1133"}
REVIEW = "[REVIEW]"


@dataclass
class EnrichedStep:
    order: int
    instance: str
    name: str
    technique_id: Optional[str]
    technique_name: Optional[str]
    tactic_shortnames: tuple[str, ...]
    tactic_ids: tuple[str, ...]
    description: str
    technique_description: str       # ATT&CK text = raw material for "succeeds when"
    veris_candidates: list[str]
    lever: str                       # "odds" | "spread" | "size"
    is_entry: bool
    is_terminal: bool
    is_impact: bool
    asset_names: list[str]
    review_notes: list[str] = field(default_factory=list)


@dataclass
class Extract:
    """The full Stage A+B structured extract handed to Stage C / Stage D."""

    # provenance / identity
    source_file: str
    flow_name: str
    flow_description: str
    scope: Optional[str]
    author: Optional[str]
    created: Optional[str]
    anchor_incident: str
    external_references: list[dict]
    # cascade
    steps: list[EnrichedStep]
    branches: list[dict]
    assets: dict[str, str]
    # derived metadata (frontmatter)
    entry_phrase: str
    terminal_phrase: str
    veris_entry: str
    veris_terminal: str
    dbir_pattern: str
    tags: list[str]
    sectors: str
    applies_when: str
    label: str
    review_markers: list[str] = field(default_factory=list)
    build: dict = field(default_factory=dict)


def enrich(flow: ParsedFlow, index: GroundingIndex) -> Extract:
    entry_set = set(flow.entry_steps)
    terminal_set = set(flow.terminal_steps)
    review_markers: list[str] = []

    enriched: list[EnrichedStep] = []
    for step in flow.steps:
        info = index.attack.resolve(step.technique_id, step.technique_ref)
        tactics = info.tactic_shortnames if info else ()
        ta_ids = info.tactic_ids if info else ()
        is_impact = IMPACT_TACTIC_ID in ta_ids or (step.technique_id in {"T1486", "T1485", "T1490", "T1489", "T1491"})
        is_terminal = step.instance in terminal_set or is_impact
        lever = _classify_lever(tactics, is_impact)

        veris_caps = index.ctid.veris_for(step.technique_id)
        notes: list[str] = []
        if step.technique_id and not info:
            notes.append(f"technique {step.technique_id} not found in pinned ATT&CK")
            review_markers.append(f"step {step.order}: unknown technique {step.technique_id}")
        elif info and info.revoked:
            notes.append(f"technique {step.technique_id} is revoked in pinned ATT&CK 19.1")
            review_markers.append(f"step {step.order}: {step.technique_id} revoked in ATT&CK 19.1 — confirm current id")

        es = EnrichedStep(
            order=step.order,
            instance=step.instance,
            name=step.name or (info.name if info else "Unnamed step"),
            technique_id=step.technique_id,
            technique_name=info.name if info else None,
            tactic_shortnames=tactics,
            tactic_ids=ta_ids,
            description=step.description,
            technique_description=info.description if info else "",
            veris_candidates=veris_caps,
            lever=lever,
            is_entry=step.instance in entry_set,
            is_terminal=is_terminal,
            is_impact=is_impact,
            asset_names=step.asset_names,
            review_notes=notes,
        )
        enriched.append(es)

    # Re-derive terminal/size: the highest-value magnitude step is [REVIEW] (§5).
    for es in enriched:
        if es.lever == "size":
            es.review_notes.append("size step = magnitude driver; confirm (human review)")

    entry_steps = [s for s in enriched if s.is_entry] or enriched[:1]
    impact_steps = [s for s in enriched if s.is_impact]
    terminal_steps = impact_steps or [s for s in enriched if s.is_terminal] or enriched[-1:]

    entry_phrase = _plain_phrase(entry_steps[0]) if entry_steps else "[REVIEW: entry]"
    terminal_phrase = _plain_phrase(terminal_steps[0]) if terminal_steps else "[REVIEW: terminal]"

    veris_entry = _pick_veris(entry_steps[0], index, prefer_attribute=False, review=review_markers, role="veris_entry") if entry_steps else "[REVIEW: no mapping]"
    veris_terminal = _pick_veris(terminal_steps[0], index, prefer_attribute=True, review=review_markers, role="veris_terminal") if terminal_steps else "[REVIEW: no mapping]"

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

    anchor = _anchor_incident(flow)

    build = {
        "source_flow": flow.source_file,
        "attack_flow_schema": VERSIONS["attack_flow_schema"],
        "attack_version": VERSIONS["attack_version"],
        "veris_version": VERSIONS["veris_version"],
        "mapping_version": VERSIONS["mapping_version"],
        "generated": _dt.date.today().isoformat(),
    }

    branches = [
        {"kind": b.kind, "description": b.description, "after_step": _step_order(enriched, b.after_step)}
        for b in flow.branches
    ]

    return Extract(
        source_file=flow.source_file,
        flow_name=flow.name,
        flow_description=flow.description,
        scope=flow.scope,
        author=flow.author,
        created=flow.created,
        anchor_incident=anchor,
        external_references=flow.external_references,
        steps=enriched,
        branches=branches,
        assets=flow.assets,
        entry_phrase=entry_phrase,
        terminal_phrase=terminal_phrase,
        veris_entry=veris_entry,
        veris_terminal=veris_terminal,
        dbir_pattern=dbir_pattern,
        tags=tags,
        sectors=sectors,
        applies_when=applies_when,
        label=label,
        review_markers=review_markers,
        build=build,
    )


def _classify_lever(tactics: tuple[str, ...], is_impact: bool) -> str:
    if is_impact:
        return "size"
    if any(t in SPREAD_TACTICS for t in tactics):
        return "spread"
    return "odds"


def _plain_phrase(step: EnrichedStep) -> str:
    base = step.technique_name or step.name
    return base.strip() if base else "[REVIEW: phrase]"


def _pick_veris(step: EnrichedStep, index: GroundingIndex, prefer_attribute: bool,
                review: list[str], role: str) -> str:
    """Choose a single VERIS string for the entry/terminal action (§5)."""
    caps = [c for c in step.veris_candidates if index.veris.is_valid(c)]
    if not caps:
        review.append(f"{role}: no VERIS mapping for {step.technique_id or step.name}")
        return "[REVIEW: no mapping]"

    def score(cap: str) -> tuple:
        is_attr = cap.startswith("attribute.")
        is_variety = ".variety." in cap
        # prefer attribute.* for terminal, action.* for entry; prefer variety leaves
        primary = (is_attr == prefer_attribute)
        return (primary, is_variety, -len(cap))

    ranked = sorted(set(caps), key=score, reverse=True)
    chosen = ranked[0]
    if len(set(caps)) > 1:
        review.append(f"{role}: ambiguous mapping for {step.technique_id}; "
                      f"chose {chosen} from {sorted(set(caps))}")
        return f"{chosen}  # [REVIEW: ambiguous]"
    return chosen


def _dbir_pattern(steps: list[EnrichedStep], entry_steps: list[EnrichedStep],
                  index: GroundingIndex) -> str:
    cats = set()
    for s in steps:
        for cap in s.veris_candidates:
            cats.add(cap.split(".")[1] if cap.startswith("action.") and "." in cap else cap.split(".")[0])
    has_hacking = "hacking" in cats
    has_malware = "malware" in cats
    has_social = "social" in cats
    has_misuse = "misuse" in cats
    tactics = {t for s in steps for t in s.tactic_shortnames}
    has_lateral = "lateral-movement" in tactics
    has_impact = any(s.is_impact for s in steps)
    entry_tids = {s.technique_id for s in entry_steps}
    deeper = any(t in tactics for t in ("lateral-movement", "privilege-escalation", "credential-access"))

    # Rule 1: web-app entry, no deeper host intrusion.
    if entry_tids & WEB_ENTRY_TECHNIQUES and not deeper and not has_impact:
        return "basic_web_application_attacks"
    # Rule 2: social entry ending at the social outcome (no host takeover).
    if has_social and not (has_hacking or has_malware or has_lateral or has_impact):
        return "social_engineering"
    # Rule 3: multi-category with lateral movement and/or impact.
    if (has_hacking and has_malware) and (has_lateral or has_impact):
        return "system_intrusion"
    if has_impact and (has_hacking or has_malware):
        return "system_intrusion"
    # Rule 4: insider / entrusted-access abuse.
    if has_misuse and not has_malware:
        return "privilege_misuse"
    # Rule 5: availability-only flood.
    avail_only = has_impact and not (has_hacking or has_malware or has_social)
    if avail_only and "endpoint-denial-of-service" in tactics:
        return "denial_of_service"
    return "[REVIEW: pattern]"


def _derive_tags(steps: list[EnrichedStep]) -> list[str]:
    tags: list[str] = []
    for s in steps:
        for t in s.tactic_shortnames:
            tag = t.replace("-", "_")
            if tag not in tags:
                tags.append(tag)
    return tags[:10]


def _derive_sectors(flow: ParsedFlow) -> str:
    text = f"{flow.name} {flow.description}".lower()
    sectors = {
        "healthcare": ["hospital", "health", "patient", "clinic"],
        "finance": ["bank", "swift", "financial", "payment", "credit"],
        "education": ["university", "school", "education", "academic"],
        "government": ["government", "federal", "agency", "municipal"],
        "energy": ["energy", "utility", "power grid", "ics", "scada"],
        "retail": ["retail", "point of sale", "pos ", "store"],
        "manufacturing": ["manufactur", "industrial", "factory"],
    }
    for name, kws in sectors.items():
        if any(kw in text for kw in kws):
            return name
    return f"sector-agnostic {REVIEW}"


def _applies_when(flow: ParsedFlow, steps: list[EnrichedStep]) -> str:
    asset_bits = [name for name in flow.assets][:3]
    if asset_bits:
        return " · ".join(asset_bits) + f"  {REVIEW}"
    return f"[REVIEW: topology precondition]"


def _anchor_incident(flow: ParsedFlow) -> str:
    import re
    year = None
    m = re.search(r"\b(19|20)\d{2}\b", flow.description) or re.search(r"\b(19|20)\d{2}\b", flow.name)
    if m:
        year = m.group(0)
    name = flow.name
    return f"{name}, {year}" if year else name


def _step_order(steps: list[EnrichedStep], instance: Optional[str]) -> Optional[int]:
    for s in steps:
        if s.instance == instance:
            return s.order
    return None
