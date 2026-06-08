"""Plain-language mitigation glosses (version '-b').

Loads the pinned, hand-authored gloss table at ``refdocs/oic-mitigation-glosses.yaml``
and exposes, per ATT&CK mitigation M-code:

* ``control``   - plain control phrasing (used in the card's mitigations section), and
* ``weakness``  - the gap its absence/weakness creates (used in the gate "Succeeds when"
  prose), phrased as "absent or weak", not merely "missing".
* ``preventable`` - ``False`` for the "do not / cannot mitigate" markers, which route to a
  detection/response note instead of a listed weakness.

Translate, don't cite: the generator composes the "Succeeds when ..." sentence from the
``weakness`` phrases and never emits a raw M-code into the body. ``select_load_bearing``
keeps only the one-to-three most gating weaknesses per step (a static priority asset), so
broad/marginal mitigations don't flatten the signal.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import yaml

from .config import MITIGATION_GLOSSES


@dataclass(frozen=True)
class Gloss:
    mcode: str
    name: str
    control: str
    weakness: str
    preventable: bool


@lru_cache(maxsize=1)
def _glosses() -> dict[str, Gloss]:
    with open(MITIGATION_GLOSSES, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    out: dict[str, Gloss] = {}
    for domain in ("enterprise", "ics"):
        for mcode, e in (data.get(domain) or {}).items():
            out[mcode] = Gloss(
                mcode=mcode,
                name=(e.get("name") or "").strip(),
                control=(e.get("control") or "").strip(),
                weakness=(e.get("weakness_when_absent") or "").strip(),
                preventable=bool(e.get("preventable", True)),
            )
    return out


# Load-bearing priority, by mitigation name (enterprise M1xxx and ICS M0xxx share names).
# Lower index = more directly gates the abuse; broad governance controls rank lower so they
# get pruned first when a technique maps to many mitigations.
_PRIORITY_ORDER = [
    "disable or remove feature or program",
    "execution prevention",
    "code signing",
    "restrict library loading",
    "application isolation and sandboxing",
    "exploit protection",
    "update software",
    "behavior prevention on endpoint",
    "antivirus/antimalware",
    "user account control",
    "privileged process integrity",
    "credential access protection",
    "multi-factor authentication",
    "password policies",
    "restrict registry permissions",
    "restrict file and directory permissions",
    "environment variable permissions",
    "network segmentation",
    "network intrusion prevention",
    "filter network traffic",
    "limit access to resource over network",
    "restrict web-based content",
    "ssl/tls inspection",
    "data loss prevention",
    "encrypt sensitive information",
    "encrypt network traffic",
    "privileged account management",
    "user account management",
    "audit",
    "account use policies",
    "active directory configuration",
    "operating system configuration",
    "software configuration",
    "limit software installation",
    "limit hardware installation",
    "vulnerability scanning",
    "user training",
    "threat intelligence program",
    "remote data storage",
    "data backup",
    "boot integrity",
    "pre-compromise",
    # ICS-specific controls (rank after the shared set; relative order is best-effort)
    "authorization enforcement", "access management", "communication authenticity",
    "human user authentication", "software process and device authentication",
    "network allowlists", "static network configuration", "validate program inputs",
    "supply chain management", "safety instrumented systems", "mechanical protection layers",
    "watchdog timers", "redundancy of service", "out-of-band communications channel",
    "minimize wireless signal propagation", "operational information confidentiality",
]
_RANK = {name: i for i, name in enumerate(_PRIORITY_ORDER)}
_DEFAULT_RANK = len(_PRIORITY_ORDER) + 1


def gloss(mcode: str) -> Optional[Gloss]:
    return _glosses().get(mcode)


def is_preventable(mcode: str) -> bool:
    g = _glosses().get(mcode)
    return g.preventable if g else True


def weakness_phrase(mcode: str) -> Optional[str]:
    """The gate-prose weakness phrase, or ``None`` for non-preventive markers."""
    g = _glosses().get(mcode)
    if g is None or not g.preventable:
        return None
    return g.weakness or None


def control_phrase(mcode: str) -> Optional[str]:
    """The mitigations-section control phrase."""
    g = _glosses().get(mcode)
    return (g.control or g.name) if g else None


# Words ignored when comparing two weakness phrases for semantic overlap.
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "is", "are", "be", "so",
    "it", "its", "that", "this", "they", "their", "them", "with", "for", "from", "by",
    "as", "at", "into", "than", "more", "no", "not", "isn't", "aren't", "can", "can't",
    "without", "over", "out", "up", "left", "still", "goes", "runs", "run", "where",
    "when", "who", "have", "has", "need", "needs", "what", "which", "e.g", "g",
}
_OVERLAP_THRESHOLD = 0.5
_OVERLAP_NOTE = "[potential_mitigation overlap - review required]"


def _content_tokens(phrase: str) -> frozenset[str]:
    toks = "".join(c.lower() if (c.isalnum() or c == "'") else " " for c in phrase).split()
    return frozenset(t for t in toks if len(t) > 2 and t not in _STOPWORDS)


def _overlap_coeff(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def select_load_bearing(mcodes: list[str], cap: int = 3) -> tuple[list[str], bool]:
    """Return ``(mcodes, overlap_detected)`` ordered by gating priority.

    Takes the top ``cap`` preventable mitigations by priority (exact-deduped), then
    collapses any that are *semantically* near-identical (e.g. "unapproved code is allowed
    to execute" vs "unsigned code is allowed to run"), keeping the higher-priority one and
    shortening the list. ``overlap_detected`` signals the caller to emit a review note.
    """
    gl = _glosses()
    cands = [gl[m] for m in mcodes if m in gl and gl[m].preventable and gl[m].weakness]
    cands.sort(key=lambda g: _RANK.get(g.name.lower(), _DEFAULT_RANK))

    top: list[Gloss] = []
    seen_exact: set[str] = set()
    for g in cands:
        if g.weakness in seen_exact:
            continue
        seen_exact.add(g.weakness)
        top.append(g)
        if len(top) >= cap:
            break

    kept: list[str] = []
    kept_tokens: list[frozenset[str]] = []
    overlap = False
    for g in top:
        toks = _content_tokens(g.weakness)
        if any(_overlap_coeff(toks, kt) >= _OVERLAP_THRESHOLD for kt in kept_tokens):
            overlap = True
            continue
        kept.append(g.mcode)
        kept_tokens.append(toks)
    return kept, overlap
