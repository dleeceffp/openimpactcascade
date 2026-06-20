"""
oic_corpus — shared threat-intelligence corpus package.

Provides the PillarReader (DBIR / IBM / NetDiligence grounding), pillar
crosswalk (industry taxonomy bridge), and retrieval helpers.

Used by:
  - app/            Flask web application
  - tools/attack_flow_workbench/   CLI workbench (corpus_grounding.py)

The reference YAML data lives at:
  app/corpus/ref_pillars/    (current; will move to data/corpus/ in a future pass)

Configure the data path via the OIC_PILLARS_DIR environment variable or pass
the path explicitly to PillarReader().
"""

from .pillar_reader import PillarReader
from .pillar_crosswalk import resolve_industry_key, normalize_industry

__all__ = ["PillarReader", "resolve_industry_key", "normalize_industry"]
