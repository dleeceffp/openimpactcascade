"""MITRE ATT&CK matrix loader for technique ID lookups."""

import json
import logging
from typing import Dict, Optional, List, Any
from pathlib import Path

from config import ENTERPRISE_ATTACK_FILE, ICS_ATTACK_FILE

logger = logging.getLogger("oic.attack_flow.mitre_loader")


class MitreTechniqueLookup:
    """Loads and indexes MITRE ATT&CK techniques for quick lookup."""

    def __init__(self):
        self._techniques: Dict[str, Dict[str, Any]] = {}  # technique_id -> technique data
        self._tactics: Dict[str, Dict[str, Any]] = {}  # tactic_id -> tactic data
        self._loaded = False

    def load(self) -> None:
        """Load MITRE ATT&CK matrices (Enterprise and ICS)."""
        if self._loaded:
            return

        # Load Enterprise ATT&CK
        if ENTERPRISE_ATTACK_FILE.exists():
            self._load_matrix(ENTERPRISE_ATTACK_FILE)
        else:
            logger.warning(f"Enterprise ATT&CK file not found: {ENTERPRISE_ATTACK_FILE}")

        # Load ICS ATT&CK
        if ICS_ATTACK_FILE.exists():
            self._load_matrix(ICS_ATTACK_FILE)
        else:
            logger.warning(f"ICS ATT&CK file not found: {ICS_ATTACK_FILE}")

        self._loaded = True
        logger.info(f"Loaded {len(self._techniques)} techniques and {len(self._tactics)} tactics")

    def _load_matrix(self, filepath: Path) -> None:
        """Load a single MITRE ATT&CK matrix JSON file."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            objects = data.get("objects", [])
            for obj in objects:
                obj_type = obj.get("type")

                if obj_type == "attack-pattern":
                    # This is a technique
                    technique_id = obj.get("external_references", [{}])[0].get("external_id")
                    if technique_id and technique_id.startswith("T"):
                        self._techniques[technique_id] = {
                            "id": technique_id,
                            "name": obj.get("name", ""),
                            "description": obj.get("description", ""),
                            "kill_chain_phases": obj.get("kill_chain_phases", []),
                            "platforms": obj.get("x_mitre_platforms", []),
                            "data_sources": obj.get("x_mitre_data_sources", []),
                            "detection": obj.get("x_mitre_detection", ""),
                            "stix_id": obj.get("id", ""),
                        }

                elif obj_type == "x-mitre-tactic":
                    # This is a tactic
                    tactic_id = obj.get("external_references", [{}])[0].get("external_id")
                    if tactic_id and tactic_id.startswith("TA"):
                        self._tactics[tactic_id] = {
                            "id": tactic_id,
                            "name": obj.get("name", ""),
                            "description": obj.get("description", ""),
                            "shortname": obj.get("x_mitre_shortname", ""),
                            "stix_id": obj.get("id", ""),
                        }

            logger.debug(f"Loaded {len(objects)} objects from {filepath.name}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {filepath}: {e}")
        except Exception as e:
            logger.error(f"Error loading {filepath}: {e}")

    def get_technique(self, technique_id: str) -> Optional[Dict[str, Any]]:
        """Get technique data by MITRE technique ID (e.g., 'T1566.001')."""
        if not self._loaded:
            self.load()
        return self._techniques.get(technique_id.upper())

    def get_tactic(self, tactic_id: str) -> Optional[Dict[str, Any]]:
        """Get tactic data by MITRE tactic ID (e.g., 'TA0001')."""
        if not self._loaded:
            self.load()
        return self._tactics.get(tactic_id.upper())

    def find_techniques_by_tactic(self, tactic_shortname: str) -> List[Dict[str, Any]]:
        """Find all techniques for a given tactic shortname (e.g., 'initial-access')."""
        if not self._loaded:
            self.load()

        results = []
        for technique in self._techniques.values():
            for phase in technique.get("kill_chain_phases", []):
                if phase.get("phase_name") == tactic_shortname:
                    results.append(technique)
                    break
        return results

    def search_techniques(self, keyword: str) -> List[Dict[str, Any]]:
        """Search techniques by keyword in name or description."""
        if not self._loaded:
            self.load()

        keyword_lower = keyword.lower()
        results = []
        for technique in self._techniques.values():
            if (keyword_lower in technique["name"].lower() or
                keyword_lower in technique["description"].lower()):
                results.append(technique)
        return results

    def get_tactic_for_technique(self, technique_id: str) -> Optional[Dict[str, Any]]:
        """Get the primary tactic for a technique."""
        technique = self.get_technique(technique_id)
        if not technique:
            return None

        phases = technique.get("kill_chain_phases", [])
        if phases:
            tactic_shortname = phases[0].get("phase_name")
            # Find tactic by shortname
            for tactic in self._tactics.values():
                if tactic.get("shortname") == tactic_shortname:
                    return tactic
        return None

    def list_all_techniques(self) -> List[Dict[str, Any]]:
        """Return all loaded techniques."""
        if not self._loaded:
            self.load()
        return list(self._techniques.values())


# Singleton instance
_mitre_lookup: Optional[MitreTechniqueLookup] = None


def get_mitre_lookup() -> MitreTechniqueLookup:
    """Get the singleton MITRE technique lookup instance."""
    global _mitre_lookup
    if _mitre_lookup is None:
        _mitre_lookup = MitreTechniqueLookup()
        _mitre_lookup.load()
    return _mitre_lookup
