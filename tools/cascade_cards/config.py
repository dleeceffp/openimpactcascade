"""Pinned resource locations and version provenance for the cascade-card generator.

All grounding data lives under ``refdocs/``. Versions are pinned and recorded in
every card's ``build:`` block so output is reproducible (see the build spec, §1/§6).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# refdocs/ sits at the repo root; this file is tools/cascade_cards/config.py
REPO_ROOT = Path(__file__).resolve().parents[2]
REFDOCS = REPO_ROOT / "refdocs"

FLOW_CORPUS_DIR = REFDOCS / "flowcorpus"
FLOW_SCHEMA_DIR = REFDOCS / "flowschema"
MATRICES_DIR = REFDOCS / "matrices"
VERIS_DIR = REFDOCS / "veris"
CTID_MAPPING_DIR = REFDOCS / "ctidmapping"

# Pinned files (as present in this workspace).
ATTACK_ENTERPRISE = MATRICES_DIR / "enterprise-attack-19.1.json"
ATTACK_ICS = MATRICES_DIR / "ics-attack-19.1.json"
VERIS_ENUM = VERIS_DIR / "verisc-enum.json"
CTID_ENTERPRISE = CTID_MAPPING_DIR / "veris-1.4.0_attack-16.1-enterprise.json"
CTID_ICS = CTID_MAPPING_DIR / "veris-1.4.0_attack-16.1-ics.json"
ATTACK_FLOW_SCHEMA = FLOW_SCHEMA_DIR / "attack-flow-schema-2.0.0.json"
# Plain-language mitigation glosses (version '-b'): M-code -> control / weakness phrasing.
MITIGATION_GLOSSES = REFDOCS / "oic-mitigation-glosses.yaml"

# Pinned version strings recorded in card provenance.
VERSIONS = {
    "attack_flow_schema": "2.0.0 (afb native attack_flow_v2)",
    "attack_version": "enterprise-attack-19.1 / ics-attack-19.1",
    "veris_version": "verisc-enum 1.4.x",
    "mapping_version": "ctid mappings-explorer veris-1.4.0_attack-16.1",
}


@dataclass(frozen=True)
class Resources:
    """Resolved, parsed grounding resources, loaded once and reused."""

    attack_enterprise: dict
    attack_ics: dict
    veris_enum: dict
    ctid_enterprise: dict
    ctid_ics: dict


def _load(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"Required grounding resource missing: {path}. "
            "See tools/cascade_cards/cascade_card_readme.md for the expected refdocs/ layout."
        )
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def load_resources() -> Resources:
    """Load and parse all pinned grounding resources from ``refdocs/``."""
    return Resources(
        attack_enterprise=_load(ATTACK_ENTERPRISE),
        attack_ics=_load(ATTACK_ICS),
        veris_enum=_load(VERIS_ENUM),
        ctid_enterprise=_load(CTID_ENTERPRISE),
        ctid_ics=_load(CTID_ICS),
    )
