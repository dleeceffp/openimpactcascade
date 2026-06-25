# =============================================================================
# OIC PillarReader â€” Load/Cache + slice_likelihood
# Status: proposed (OIC-authored)
#
# In-memory owner of the curated pillar corpus. On startup globs the pillar
# directory, parses each YAML once, and indexes by comparable_series and edition.
#
# Step 2 of N: implements slice_likelihood(industry) for DBIR only.
# No NetDiligence, no IBM, no band resolution, no prompt rendering yet.
#
# Depends on: pillar_crosswalk.py (step 1, complete)
# =============================================================================

import glob
import logging
import os
import threading
from typing import Dict, List, Optional, Any, Union

import yaml

from oic_corpus.pillar_crosswalk import (
    resolve_industry_key,
    normalize_industry,
    SERIES_VERIZON_DBIR,
)

logger = logging.getLogger("oic.pillar_reader")


class PillarReader:
    """In-memory owner of the curated pillar corpus.

    Loads pillar YAML files on startup, indexes by comparable_series and edition,
    and provides slice methods for retrieving industry-specific grounding data.
    """

    def __init__(self, pillars_dir: str, enabled: bool = True):
        self.pillars_dir = pillars_dir
        self.enabled = enabled
        self._index: Dict[str, Dict[str, dict]] = {}  # {series: {edition: parsed_yaml}}
        self._loaded = False
        self._lock = threading.Lock()

    def load(self, force: bool = False) -> None:
        """Glob pillar directory, parse YAML files, index by series and edition.

        Thread-safe; called automatically on first slice if not eager-loaded.
        One bad file logs and skips â€” never breaks startup.
        """
        with self._lock:
            if self._loaded and not force:
                return
            if not self.enabled:
                logger.info("PillarReader disabled (OIC_PILLARS_ENABLED=0); skipping load.")
                self._loaded = True
                return

            self._index = {}
            # Glob both .yaml and .yml recursively
            yaml_files = []
            for pattern in [os.path.join(self.pillars_dir, "**", "*.yaml"),
                          os.path.join(self.pillars_dir, "**", "*.yml")]:
                yaml_files.extend(glob.glob(pattern, recursive=True))

            for filepath in sorted(yaml_files):
                self._load_file(filepath)

            self._loaded = True
            logger.info(f"PillarReader loaded {len(yaml_files)} files, "
                       f"indexed {len(self._index)} series")

    def _load_file(self, filepath: str) -> None:
        """Load a single YAML file into the index."""
        try:
            with open(filepath, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
        except yaml.YAMLError as e:
            logger.warning(f"Skipping unparsable YAML {filepath}: {e}")
            return
        except OSError as e:
            logger.warning(f"Skipping unreadable file {filepath}: {e}")
            return

        if not isinstance(data, dict):
            logger.warning(f"Skipping non-dict YAML root in {filepath}")
            return

        series = data.get("comparable_series")
        edition = data.get("edition")

        if not series or not edition:
            logger.warning(f"Skipping {filepath}: missing comparable_series or edition")
            return

        # Normalize edition for indexing
        edition_key = str(edition)

        if series not in self._index:
            self._index[series] = {}

        if edition_key in self._index[series]:
            logger.warning(f"Duplicate series+edition {series}/{edition_key}: "
                        f"{filepath} overwrites previous")

        self._index[series][edition_key] = data

    def _latest(self, series: str) -> Optional[dict]:
        """Return the latest edition data for a series, or None."""
        editions = self._index.get(series, {})
        if not editions:
            return None

        # Try numeric edition comparison first
        def edition_key(ed: str) -> tuple:
            try:
                return (0, int(ed))  # numeric sorts before string
            except ValueError:
                return (1, ed)  # non-numeric sorts after

        latest_ed = max(editions.keys(), key=edition_key)
        return editions[latest_ed]

    def slice_likelihood(self, industry: str) -> dict:
        """Return the latest-DBIR likelihood slice for one industry.

        Resolution: resolve_industry_key(industry, SERIES_VERIZON_DBIR) -> [keys].
        First-hit semantics: use the first resolved key that exists in the latest
        DBIR file's `figures`. If a key is resolved but absent in this edition, try
        the next; log DEBUG on fallback. If none resolve/exist, coverage is False
        but the corpus-wide `overall` anchors are STILL returned.

        Never raises. Never derives a probability (see spec Â§8).

        Returns audit-faithful dict with pillar, coverage, provenance, sector, overall.
        """
        # Ensure loaded (lazy load safety net)
        if not self._loaded:
            self.load()

        # Default response structure
        result: Dict[str, Any] = {
            "pillar": "likelihood",
            "coverage": False,
            "industry_canonical": normalize_industry(industry),
            "resolved_key": None,
            "source": None,
            "provenance": {},
            "sector": None,
            "overall": None,
        }

        # Get latest DBIR edition
        latest_dbir = self._latest(SERIES_VERIZON_DBIR)
        if not latest_dbir:
            logger.debug(f"No DBIR data loaded for series {SERIES_VERIZON_DBIR}")
            return result

        # Populate source and provenance from latest DBIR
        result["source"] = f"Verizon DBIR {latest_dbir.get('edition', 'Unknown')}"
        result["provenance"] = {
            "publisher": latest_dbir.get("publisher", "Verizon Data Breach Investigations Report (DBIR)"),
            "edition": latest_dbir.get("edition", ""),
            "comparable_series": latest_dbir.get("comparable_series", SERIES_VERIZON_DBIR),
            "citation_url": latest_dbir.get("citation_url", "https://www.verizon.com/business/resources/reports/dbir/"),
            "evidence_type": latest_dbir.get("evidence_type", "incident_corpus"),
            "review_status": latest_dbir.get("review_status", "[REVIEW]"),
        }

        # Copy overall anchors (always present when DBIR loaded)
        # Use 'or {}' to guard against figures: null (YAML null is parsed as None)
        overall = latest_dbir.get("overall") or {}
        if overall:
            result["overall"] = {
                "top_breach_patterns": overall.get("top_breach_patterns", {}),
                "leading_initial_vectors": overall.get("leading_initial_vectors", {}),
                "ransomware_share_of_breaches": overall.get("ransomware_share_of_breaches"),
                "third_party_involvement": overall.get("third_party_involvement"),
                "espionage_motive_share": overall.get("espionage_motive_share"),
                "smb_ransomware_share": overall.get("smb_ransomware_share"),
                "median_ransom_paid_usd": overall.get("median_ransom_paid_usd"),
            }

        # Resolve industry to DBIR key(s)
        resolved_keys = resolve_industry_key(industry, SERIES_VERIZON_DBIR)
        if not resolved_keys:
            logger.debug(f"No crosswalk resolution for industry {industry!r}")
            return result

        # Get figures section from latest DBIR
        # Use 'or {}' to guard against figures: null (YAML null is parsed as None)
        figures = latest_dbir.get("figures") or {}

        # First-hit: try each resolved key in order
        for key in resolved_keys:
            sector_data = figures.get(key)
            if sector_data:
                result["coverage"] = True
                result["resolved_key"] = key
                # Pass-through: copy fields verbatim, no transformation
                result["sector"] = {
                    "top_patterns": sector_data.get("top_patterns"),
                    "threat_actors": sector_data.get("threat_actors"),
                    "actor_motives": sector_data.get("actor_motives"),
                    "data_compromised": sector_data.get("data_compromised"),
                    "notable": sector_data.get("notable"),
                    "incidents": sector_data.get("incidents"),
                    "breaches": sector_data.get("breaches"),
                }
                # Include size splits if present (verbatim, not selected on)
                for size_key in ["incidents_small", "incidents_large",
                               "breaches_small", "breaches_large"]:
                    if size_key in sector_data:
                        result["sector"][size_key] = sector_data[size_key]
                logger.debug(f"Resolved {industry!r} -> {key} in DBIR {result['provenance']['edition']}")
                return result
            else:
                logger.debug(f"Resolved key {key!r} not in DBIR {result['provenance']['edition']} figures; trying next")

        # No resolved key found in this edition
        logger.debug(f"All resolved keys {resolved_keys!r} absent from DBIR {result['provenance']['edition']}")
        return result

    def coverage_report(self) -> Dict[str, dict]:
        """Report coverage for every canonical industry against latest DBIR.

        Returns: {canonical_industry: {"resolved_key": str|None, "in_latest": bool}}

        This is the end-to-end integrity check that catches a crosswalk key
        that doesn't match a real DBIR figures key. No runtime cost unless called.
        """
        from oic_corpus.pillar_crosswalk import canonical_industries

        if not self._loaded:
            self.load()

        report: Dict[str, dict] = {}
        latest_dbir = self._latest(SERIES_VERIZON_DBIR)
        # Use 'or {}' to guard against figures: null (YAML null is parsed as None)
        figures = (latest_dbir.get("figures") or {}) if latest_dbir else {}

        for canonical in canonical_industries():
            resolved = resolve_industry_key(canonical, SERIES_VERIZON_DBIR)
            first_key = resolved[0] if resolved else None
            report[canonical] = {
                "resolved_key": first_key,
                "in_latest": first_key in figures if first_key else False,
            }
        return report

    def has_series(self, series: str) -> bool:
        """Return True if the reader has loaded data for the given series.

        This is the UI/template gate: it returns False when OIC_PILLARS_ENABLED=0
        (reader loads nothing) or when the series files are absent.
        """
        if not self._loaded:
            self.load()
        return self._latest(series) is not None

    def latest_edition(self, series: str) -> str:
        """Return the edition string for the latest data of a series, or ''.

        Used in templates to show "Verizon DBIR 2025" â€” returns empty string
        when series is unavailable so templates can conditional-render.
        """
        if not self._loaded:
            self.load()
        latest = self._latest(series)
        return latest.get("edition", "") if latest else ""


# Singleton instance (mirrors CardLibrary pattern)
_reader: Optional[PillarReader] = None
_reader_lock = threading.Lock()


def get_pillar_reader(pillars_dir: Optional[str] = None, enabled: Optional[bool] = None) -> PillarReader:
    """Return the process-wide pillar reader, constructing it on first use.

    FIRST-CALL-WINS SEMANTICS: Arguments are only honored on the first call.
    Subsequent calls return the existing singleton regardless of arguments passed.
    This matches the CardLibrary pattern used elsewhere in the codebase.

    Args:
        pillars_dir: Directory to load from. First call only; ignored thereafter.
        enabled: Whether to enable loading. First call only; ignored thereafter.

    Returns:
        The singleton PillarReader instance.

    Warns:
        If a subsequent call passes args that differ from the live instance,
        logs a WARNING to help catch the "silent wrong reader" bug class.

    Thread-safe singleton factory.
    """
    global _reader
    with _reader_lock:
        if _reader is not None:
            # Defensive: warn if caller thinks they're getting a different reader
            if pillars_dir is not None and pillars_dir != _reader.pillars_dir:
                logger.warning(
                    f"get_pillar_reader() called with pillars_dir={pillars_dir!r} "
                    f"but singleton already initialized with {_reader.pillars_dir!r}. "
                    f"Returning existing reader. Use PillarReader() directly for test isolation."
                )
            if enabled is not None and enabled != _reader.enabled:
                logger.warning(
                    f"get_pillar_reader() called with enabled={enabled} "
                    f"but singleton already initialized with enabled={_reader.enabled}. "
                    f"Returning existing reader. Use PillarReader() directly for test isolation."
                )
            return _reader

        # First call: construct the singleton
        try:
            from config import OIC_PILLARS_DIR, OIC_PILLARS_ENABLED
        except ImportError:
            # Fallback defaults if config not importable (tests)
            OIC_PILLARS_DIR = "corpus/ref_pillars"
            OIC_PILLARS_ENABLED = True

        actual_dir = pillars_dir if pillars_dir is not None else OIC_PILLARS_DIR
        actual_enabled = enabled if enabled is not None else OIC_PILLARS_ENABLED
        _reader = PillarReader(pillars_dir=actual_dir, enabled=actual_enabled)
        return _reader
