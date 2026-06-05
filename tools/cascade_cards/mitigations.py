"""ATT&CK mitigation index (Addendum B source layer).

Builds, from the pinned ATT&CK STIX bundles, a technique -> mitigations map using the
``mitigates`` relationships (``course-of-action`` --mitigates--> ``attack-pattern``).

Only modern **M-code** mitigations are kept; the deprecated legacy per-technique
"<Technique> Mitigation" course-of-action objects (external_id starting with ``T``)
are excluded. ATT&CK's ``M1056 Pre-compromise`` course-of-action is treated as the
"cannot be mitigated with preventive controls" marker (Addendum B §2): it is never
listed as a mitigation; a technique that maps to it is flagged ``no_preventive``.

This module is additive and does not modify the v1 pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .config import Resources

NO_PREVENTIVE_MCODE = "M1056"  # ATT&CK "Pre-compromise"


@dataclass(frozen=True)
class Mitigation:
    mcode: str
    name: str
    description: str


class MitigationIndex:
    """technique id -> ordered, de-duplicated list of :class:`Mitigation`."""

    def __init__(self, resources: Resources):
        self._coa: dict[str, Mitigation] = {}          # course-of-action STIX id -> Mitigation
        self._by_tid: dict[str, list[str]] = {}         # technique id -> [mcode,...]
        self._no_preventive: set[str] = set()           # technique ids mapped to M1056
        self._build(resources.attack_enterprise)
        self._build(resources.attack_ics)

    def _build(self, bundle: dict) -> None:
        objects = bundle.get("objects", [])
        by_id = {o.get("id"): o for o in objects}

        # 1. Index M-code course-of-action objects.
        for obj in objects:
            if obj.get("type") != "course-of-action" or obj.get("x_mitre_deprecated") or obj.get("revoked"):
                continue
            mcode = _external_id(obj)
            if not mcode or not mcode.startswith("M"):
                continue  # skip legacy T-code mitigations
            self._coa[obj["id"]] = Mitigation(
                mcode=mcode,
                name=obj.get("name", "").strip(),
                description=(obj.get("description") or "").strip(),
            )

        # 2. Walk mitigates relationships.
        for rel in objects:
            if rel.get("type") != "relationship" or rel.get("relationship_type") != "mitigates":
                continue
            if rel.get("x_mitre_deprecated") or rel.get("revoked"):
                continue
            mit = self._coa.get(rel.get("source_ref"))
            tgt = by_id.get(rel.get("target_ref"))
            if not mit or not tgt or tgt.get("type") != "attack-pattern":
                continue
            tid = _external_id(tgt)
            if not tid:
                continue
            if mit.mcode == NO_PREVENTIVE_MCODE:
                self._no_preventive.add(tid)
                continue
            self._by_tid.setdefault(tid, [])
            if mit.mcode not in self._by_tid[tid]:
                self._by_tid[tid].append(mit.mcode)

        self._by_mcode = {m.mcode: m for m in self._coa.values()}

    def for_technique(self, tid: Optional[str]) -> list[Mitigation]:
        if not tid:
            return []
        codes = self._by_tid.get(tid)
        if codes is None and "." in tid:  # parent technique fallback
            codes = self._by_tid.get(tid.split(".")[0], [])
        return [self._by_mcode[c] for c in (codes or []) if c in self._by_mcode]

    def is_no_preventive(self, tid: Optional[str]) -> bool:
        if not tid:
            return False
        if tid in self._no_preventive:
            return True
        return "." in tid and tid.split(".")[0] in self._no_preventive

    def mitigation(self, mcode: str) -> Optional[Mitigation]:
        return self._by_mcode.get(mcode)


def _external_id(obj: dict) -> Optional[str]:
    for ref in obj.get("external_references", []):
        if ref.get("source_name") == "mitre-attack":
            return ref.get("external_id")
    return None
