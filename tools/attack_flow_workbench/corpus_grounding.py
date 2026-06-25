"""Corpus grounding module - reuses the main app's pillar-based grounding."""

import logging
import sys
from typing import List, Dict, Optional, Any
from pathlib import Path

# Add app directory to path to reuse pillar reader
APP_DIR = Path(__file__).parent.parent.parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from corpus.pillar_reader import get_pillar_reader, SERIES_VERIZON_DBIR
from corpus.pillar_crosswalk import resolve_industry_key, normalize_industry

logger = logging.getLogger("oic.attack_flow.corpus")


class ThreatIntelGrounding:
    """Provides threat intelligence grounding from the corpus (DBIR pillars)."""

    def __init__(self):
        self._reader = None
        self._enabled = False
        self._initialize()

    def _initialize(self) -> None:
        """Initialize the pillar reader."""
        try:
            self._reader = get_pillar_reader()
            self._enabled = self._reader.has_series(SERIES_VERIZON_DBIR)
            if self._enabled:
                logger.info("Corpus grounding enabled (DBIR data loaded)")
            else:
                logger.warning("Corpus grounding unavailable - DBIR data not loaded")
        except Exception as e:
            logger.warning(f"Failed to initialize corpus grounding: {e}")
            self._enabled = False

    def get_grounding_for_industry(self, industry: str) -> Dict[str, Any]:
        """Get threat intel grounding for a specific industry."""
        if not self._enabled or not self._reader:
            return self._empty_grounding(industry)

        try:
            slice_data = self._reader.slice_likelihood(industry)
            return {
                "industry": industry,
                "industry_canonical": slice_data.get("industry_canonical", normalize_industry(industry)),
                "coverage": slice_data.get("coverage", False),
                "source": slice_data.get("source", "Verizon DBIR"),
                "provenance": slice_data.get("provenance", {}),
                "sector_data": slice_data.get("sector", {}),
                "overall_anchors": slice_data.get("overall", {}),
                "resolved_key": slice_data.get("resolved_key"),
            }
        except Exception as e:
            logger.error(f"Error getting grounding for {industry}: {e}")
            return self._empty_grounding(industry)

    def _empty_grounding(self, industry: str) -> Dict[str, Any]:
        """Return empty grounding when corpus is unavailable."""
        return {
            "industry": industry,
            "industry_canonical": normalize_industry(industry),
            "coverage": False,
            "source": None,
            "provenance": {},
            "sector_data": {},
            "overall_anchors": {},
            "resolved_key": None,
        }

    def format_grounding_for_prompt(self, grounding: Dict[str, Any]) -> str:
        """Format grounding data as a text block for LLM prompts."""
        lines = []
        lines.append("=" * 70)
        lines.append(f"THREAT INTELLIGENCE GROUNDING — {grounding['industry_canonical']}")
        source = grounding.get("source", "Unknown")
        lines.append(f"Source: {source}")
        lines.append("=" * 70)

        if grounding.get("coverage"):
            sector = grounding.get("sector_data", {})
            if sector.get("top_patterns"):
                lines.append(f"Top attack patterns: {sector['top_patterns']}")
            if sector.get("threat_actors"):
                lines.append(f"Threat actors: {sector['threat_actors']}")
            if sector.get("actor_motives"):
                lines.append(f"Actor motives: {sector['actor_motives']}")
            if sector.get("notable"):
                lines.append(f"Notable: {sector['notable']}")
            if sector.get("incidents") and sector.get("breaches"):
                lines.append(f"Counts: {sector['incidents']} incidents, {sector['breaches']} breaches")
        else:
            lines.append(f"No sector-specific DBIR data for {grounding['industry']}; using corpus-wide anchors.")

        # Add overall anchors
        overall = grounding.get("overall_anchors", {})
        anchors = []
        if overall.get("ransomware_share_of_breaches") is not None:
            anchors.append(f"ransomware share of breaches {overall['ransomware_share_of_breaches']}")
        if overall.get("smb_ransomware_share") is not None:
            anchors.append(f"SMB ransomware share {overall['smb_ransomware_share']}")
        if overall.get("median_ransom_paid_usd") is not None:
            anchors.append(f"median ransom paid ${overall['median_ransom_paid_usd']:,}")
        if overall.get("top_breach_patterns"):
            top = overall["top_breach_patterns"]
            if isinstance(top, dict) and top:
                first = list(top.items())[0]
                anchors.append(f"top breach pattern: {first[0]} ({first[1]})")

        if anchors:
            lines.append(f"Corpus anchors: {'; '.join(anchors)}")

        lines.append("=" * 70)
        lines.append("Use this threat intelligence to frame credible attack patterns.")
        lines.append("These are corpus composition figures, not annual probabilities.")
        lines.append("=" * 70)

        return "\n".join(lines)

    def get_threat_patterns(self, industry: str) -> List[str]:
        """Extract top threat patterns for the industry."""
        grounding = self.get_grounding_for_industry(industry)
        sector = grounding.get("sector_data", {})
        patterns_str = sector.get("top_patterns", "")

        # Parse patterns from the description
        patterns = []
        if patterns_str:
            # Common patterns mentioned in DBIR
            common_patterns = [
                "System Intrusion", "Social Engineering", "Miscellaneous Errors",
                "Basic Web Application Attacks", "Privilege Misuse",
                "Lost and Stolen Assets", "Denial of Service"
            ]
            for pattern in common_patterns:
                if pattern.lower() in patterns_str.lower():
                    patterns.append(pattern)

        return patterns

    def get_threat_actors(self, industry: str) -> List[str]:
        """Extract threat actor types for the industry."""
        grounding = self.get_grounding_for_industry(industry)
        sector = grounding.get("sector_data", {})
        actors_str = sector.get("threat_actors", "")

        actors = []
        if "External" in actors_str:
            actors.append("External")
        if "Internal" in actors_str:
            actors.append("Internal")
        if "Partner" in actors_str:
            actors.append("Partner")

        return actors


# Singleton instance
_grounding: Optional[ThreatIntelGrounding] = None


def get_grounding() -> ThreatIntelGrounding:
    """Get the singleton threat intel grounding instance."""
    global _grounding
    if _grounding is None:
        _grounding = ThreatIntelGrounding()
    return _grounding
