"""Indexers over the pinned grounding data.

Three lookups power Stage B enrichment (build spec §5):

* :class:`AttackIndex`  - technique id/ref -> name, tactic shortnames, TA ids, description.
* :class:`CtidMapping`  - technique id -> VERIS capability strings (ATT&CK -> VERIS).
* :class:`VerisEnum`    - validate that a ``a.b.c.value`` path is a real VERIS enum value.

Everything here is deterministic. Nothing is invented: if a technique has no VERIS
mapping the caller is told so and emits a ``[REVIEW: no mapping]`` token (§5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .config import Resources

# ATT&CK kill-chain phase shortname -> tactic id. Built from the matrices' own
# x-mitre-tactic objects so it tracks the pinned version (incl. 19.1 renames such
# as defense-evasion -> stealth and the new defense-impairment tactic).
IMPACT_TACTIC_ID = "TA0040"


@dataclass(frozen=True)
class TechniqueInfo:
    technique_id: str
    name: str
    tactic_shortnames: tuple[str, ...]
    tactic_ids: tuple[str, ...]
    description: str
    is_subtechnique: bool
    domain: str  # "enterprise" | "ics"
    revoked: bool = False


class AttackIndex:
    """Resolve ATT&CK technique id / STIX ref -> :class:`TechniqueInfo`."""

    def __init__(self, resources: Resources):
        self._by_tid: dict[str, TechniqueInfo] = {}
        self._by_ref: dict[str, TechniqueInfo] = {}
        self._by_name: dict[str, TechniqueInfo] = {}
        self._shortname_to_ta: dict[str, str] = {}
        self._build(resources.attack_enterprise, "enterprise")
        self._build(resources.attack_ics, "ics")

    def _build(self, bundle: dict, domain: str) -> None:
        objects = bundle.get("objects", [])
        # tactic shortname -> TA id
        for obj in objects:
            if obj.get("type") == "x-mitre-tactic":
                short = obj.get("x_mitre_shortname")
                ta = _external_id(obj)
                if short and ta:
                    self._shortname_to_ta[short] = ta
        for obj in objects:
            # Keep revoked techniques (flows may reference older ids and the object
            # still carries name/tactic) but drop fully deprecated/removed ones.
            if obj.get("type") != "attack-pattern" or obj.get("x_mitre_deprecated"):
                continue
            tid = _external_id(obj)
            if not tid:
                continue
            shortnames = tuple(
                ph.get("phase_name")
                for ph in obj.get("kill_chain_phases", [])
                if ph.get("kill_chain_name") == "mitre-attack"
            )
            ta_ids = tuple(
                self._shortname_to_ta[s] for s in shortnames if s in self._shortname_to_ta
            )
            info = TechniqueInfo(
                technique_id=tid,
                name=obj.get("name", ""),
                tactic_shortnames=shortnames,
                tactic_ids=ta_ids,
                description=(obj.get("description") or "").strip(),
                is_subtechnique=bool(obj.get("x_mitre_is_subtechnique")),
                domain=domain,
                revoked=bool(obj.get("revoked")),
            )
            # Prefer a non-revoked, enterprise definition on shared ids.
            existing = self._by_tid.get(tid)
            if existing is None or (existing.revoked and not info.revoked):
                self._by_tid[tid] = info
            self._by_ref.setdefault(obj.get("id", ""), info)
            key = info.name.strip().lower()
            ex_name = self._by_name.get(key)
            # Prefer non-revoked and parent technique over sub-technique on name ties.
            if ex_name is None or (ex_name.revoked and not info.revoked) or \
               (ex_name.is_subtechnique and not info.is_subtechnique and not info.revoked):
                self._by_name[key] = info

    def by_technique_id(self, tid: Optional[str]) -> Optional[TechniqueInfo]:
        if not tid:
            return None
        info = self._by_tid.get(tid)
        if info is None and "." in tid:  # fall back to parent technique
            info = self._by_tid.get(tid.split(".")[0])
        return info

    def by_ref(self, ref: Optional[str]) -> Optional[TechniqueInfo]:
        return self._by_ref.get(ref) if ref else None

    def by_name(self, name: Optional[str]) -> Optional[TechniqueInfo]:
        """Exact (case-insensitive) technique-name fallback for name-only flows."""
        return self._by_name.get(name.strip().lower()) if name else None

    def resolve(self, technique_id: Optional[str], technique_ref: Optional[str]) -> Optional[TechniqueInfo]:
        return self.by_ref(technique_ref) or self.by_technique_id(technique_id)


class CtidMapping:
    """ATT&CK technique id -> list of VERIS capability strings (the mapping corpus)."""

    def __init__(self, resources: Resources):
        self._by_tid: dict[str, list[str]] = {}
        for res in (resources.ctid_enterprise, resources.ctid_ics):
            for m in res.get("mapping_objects", []):
                tid = m.get("attack_object_id")
                cap = m.get("capability_id")
                if not tid or not cap:
                    continue
                self._by_tid.setdefault(tid, [])
                if cap not in self._by_tid[tid]:
                    self._by_tid[tid].append(cap)

    def veris_for(self, technique_id: Optional[str]) -> list[str]:
        """All VERIS capability strings mapped to ``technique_id`` (parent fallback)."""
        if not technique_id:
            return []
        caps = self._by_tid.get(technique_id, [])
        if not caps and "." in technique_id:
            caps = self._by_tid.get(technique_id.split(".")[0], [])
        return list(caps)


class VerisEnum:
    """Validate dotted VERIS paths (e.g. ``action.social.variety.Phishing``)."""

    def __init__(self, resources: Resources):
        self._enum = resources.veris_enum

    def is_valid(self, path: Optional[str]) -> bool:
        if not path:
            return False
        parts = path.split(".")
        if len(parts) < 2:
            return False
        *container_path, leaf = parts
        node = self._enum
        for key in container_path:
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                return False
        if isinstance(node, list):
            return leaf in node
        if isinstance(node, dict):  # e.g. ...variety could resolve to a sub-object
            return leaf in node
        return False


@dataclass
class GroundingIndex:
    """Bundle of all three indices, built once per run."""

    attack: AttackIndex
    ctid: CtidMapping
    veris: VerisEnum

    @classmethod
    def build(cls, resources: Resources) -> "GroundingIndex":
        return cls(
            attack=AttackIndex(resources),
            ctid=CtidMapping(resources),
            veris=VerisEnum(resources),
        )


def _external_id(obj: dict) -> Optional[str]:
    for ref in obj.get("external_references", []):
        if ref.get("source_name") == "mitre-attack":
            return ref.get("external_id")
    return None
