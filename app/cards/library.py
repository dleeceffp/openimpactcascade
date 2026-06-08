"""
Cascade-archetype card library (additive, flag-gated).

Loads the compressed cascade-archetype cards (``oic-ca-*.md``) that live under
``OIC_CARDS_DIR``. Each card has a YAML-style frontmatter block followed by a
markdown body. Parsing is deterministic and contains NO LLM calls: card facts
enter the prompt verbatim, assembled by code.

The loader is intentionally dependency-free (no PyYAML) so it adds nothing to
the deployment surface. The frontmatter we author only uses simple
``key: value`` and ``key: [a, b, c]`` forms.
"""

import os
import glob
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
        return value[1:-1].strip()
    return value


def _parse_scalar_or_list(raw: str):
    """Parse a frontmatter value into a string or a list of strings.

    Strips inline ``# ...`` comments that some cards use for annotation.
    """
    raw = raw.strip()
    # Drop trailing inline comments (e.g. "system_intrusion  # [note] ...").
    # Only do this when the value is not quoted, to avoid eating '#' in text.
    if raw and raw[0] not in "\"'[" and "#" in raw:
        raw = raw.split("#", 1)[0].strip()

    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [_strip_quotes(part) for part in inner.split(",") if part.strip()]

    return _strip_quotes(raw)


def _parse_frontmatter(text: str):
    """Split a card into (frontmatter_dict, body_markdown).

    Returns ({}, text) when no frontmatter delimiter is present.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    fm: Dict[str, object] = {}
    body_start = len(lines)
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            body_start = i + 1
            break
        line = lines[i]
        if not line.strip() or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        if not key:
            continue
        fm[key] = _parse_scalar_or_list(value)

    body = "\n".join(lines[body_start:]).strip()
    return fm, body


@dataclass
class Card:
    """A single compressed cascade-archetype card."""

    id: str
    path: str
    frontmatter: Dict[str, object] = field(default_factory=dict)
    body: str = ""

    # --- convenience accessors over frontmatter ---
    @property
    def label(self) -> str:
        return str(self.frontmatter.get("label") or self.id)

    @property
    def domain(self) -> str:
        return str(self.frontmatter.get("domain") or "").lower()

    @property
    def entry(self) -> str:
        return str(self.frontmatter.get("entry") or "")

    @property
    def terminal_impact(self) -> str:
        return str(self.frontmatter.get("terminal_impact") or "")

    @property
    def dbir_pattern(self) -> str:
        return str(self.frontmatter.get("dbir_pattern") or "")

    @property
    def anchor_incident(self) -> str:
        return str(self.frontmatter.get("anchor_incident") or "")

    @property
    def tags(self) -> List[str]:
        val = self.frontmatter.get("tags")
        if isinstance(val, list):
            return [str(t) for t in val]
        if val:
            return [str(val)]
        return []

    @property
    def industry_relevance(self):
        """Curated applicability. Falls back to the legacy ``sectors`` field."""
        val = self.frontmatter.get("industry_relevance")
        if val is None:
            val = self.frontmatter.get("sectors")
        return val

    @property
    def scenario_line(self) -> str:
        """A one-line scenario summary for the selection dropdown."""
        entry = self.entry
        impact = self.terminal_impact
        if entry and impact:
            return f"{entry} -> {impact}"
        return entry or impact or self.label

    def is_cross_industry(self) -> bool:
        rel = self.industry_relevance
        if isinstance(rel, str):
            r = rel.lower()
            return "cross-industry" in r or "sector-agnostic" in r or "agnostic" in r
        if isinstance(rel, list):
            return any("cross-industry" in str(x).lower() for x in rel)
        return False

    def matches_industry(self, industry: str) -> bool:
        if not industry:
            return False
        rel = self.industry_relevance
        ind = industry.lower()
        if isinstance(rel, str):
            return ind in rel.lower()
        if isinstance(rel, list):
            return any(ind in str(x).lower() for x in rel)
        return False


class CardLibrary:
    """Cached singleton-style loader for cascade-archetype cards."""

    def __init__(self, cards_dir: str):
        self.cards_dir = cards_dir
        self._cards: Dict[str, Card] = {}
        self._loaded = False
        self._lock = threading.Lock()

    def load(self, force: bool = False) -> None:
        with self._lock:
            if self._loaded and not force:
                return
            self._cards = {}
            pattern = os.path.join(self.cards_dir, "oic-ca-*.md")
            for filepath in sorted(glob.glob(pattern)):
                try:
                    with open(filepath, "r", encoding="utf-8") as fh:
                        text = fh.read()
                except OSError:
                    continue
                fm, body = _parse_frontmatter(text)
                card_id = str(fm.get("id") or os.path.splitext(os.path.basename(filepath))[0])
                self._cards[card_id] = Card(
                    id=card_id, path=filepath, frontmatter=fm, body=body
                )
            self._loaded = True

    def all(self) -> List[Card]:
        self.load()
        return list(self._cards.values())

    def get(self, card_id: str) -> Optional[Card]:
        self.load()
        return self._cards.get(card_id)

    def archetypes_for(self, industry: str, org_size: Optional[str], limit: int) -> List[Card]:
        """Deterministic Path A selection from curated metadata (no LLM).

        Demo behavior with the three shipped cards:
          - cross-industry / sector-agnostic cards are always surfaced,
          - sector-specific cards are surfaced when ``industry`` matches their
            relevance (and, for the demo, are kept as candidates regardless so
            an OT presenter can pick them).
        Ranked: cross-industry first, then stable id order. Truncated to ``limit``.
        """
        self.load()
        cards = list(self._cards.values())

        def rank(card: Card):
            # Lower sorts first: cross-industry, then industry-matched, then rest.
            if card.is_cross_industry():
                return (0, card.id)
            if card.matches_industry(industry):
                return (1, card.id)
            return (2, card.id)

        cards.sort(key=rank)
        return cards[: max(0, limit)]


_library: Optional[CardLibrary] = None
_library_lock = threading.Lock()


def get_card_library(cards_dir: Optional[str] = None) -> CardLibrary:
    """Return the process-wide card library, constructing it on first use."""
    global _library
    with _library_lock:
        if _library is None:
            from config import OIC_CARDS_DIR
            _library = CardLibrary(cards_dir or OIC_CARDS_DIR)
        return _library
