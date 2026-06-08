"""OIC Cascade Card Generator.

Convert CTID Attack Flow files into draft OIC grounding cards
(``oic-ca-*.card.md``) via a deterministic pipeline (build spec stages A-D).

Public entry points:
    from tools.cascade_cards import generate_card
"""

from __future__ import annotations

from pathlib import Path

from .config import load_resources
from .resources import GroundingIndex
from .afb import parse, ParsedFlow
from .enrich import enrich, Extract
from .render import render_scaffold, build_llm_prompt, render_frontmatter
from .validate import validate, build_report, ValidationResult

__all__ = [
    "generate_card", "GroundingIndex", "load_resources", "parse", "enrich",
    "render_scaffold", "build_llm_prompt", "validate", "build_report",
    "ParsedFlow", "Extract", "ValidationResult",
]


def generate_card(flow_path: str | Path, index: GroundingIndex | None = None,
                  card_id: str = "oic-ca-NNN") -> tuple[str, str, ValidationResult, Extract]:
    """Run Stages A-D for one flow.

    Returns ``(card_markdown, build_report_markdown, validation_result, extract)``.
    The card is the deterministic scaffold; pass ``extract`` to an LLM via
    :func:`build_llm_prompt` to polish the prose.
    """
    if index is None:
        index = GroundingIndex.build(load_resources())
    flow = parse(flow_path)
    extract = enrich(flow, index)
    result = validate(extract, index)
    card = render_scaffold(extract, card_id=card_id)
    report = build_report(extract, result)
    return card, report, result, extract
