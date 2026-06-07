# =============================================================================
# PillarReader Acceptance Tests
#
# Run against real fixtures in tests/fixtures/pillars/
# These tests validate the step-1 crosswalk judgment calls against actual
# DBIR file keys — the end-to-end integrity check.
# =============================================================================

import pytest
import sys
from pathlib import Path

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from corpus.pillar_reader import PillarReader


@pytest.fixture
def reader():
    """PillarReader pointed at test fixtures."""
    fixtures_dir = Path(__file__).parent / "fixtures" / "pillars"
    r = PillarReader(pillars_dir=str(fixtures_dir), enabled=True)
    r.load()
    return r


# -----------------------------------------------------------------------------
# Core acceptance tests from the spec
# -----------------------------------------------------------------------------

def test_latest_edition_selected(reader):
    """Verify 2025 is selected as latest (not 2024 if present)."""
    s = reader.slice_likelihood("Healthcare")
    assert s["provenance"]["edition"] == "2025"
    assert s["provenance"]["comparable_series"] == "dbir-by-industry"


def test_healthcare_round_trip(reader):
    """Healthcare resolves to healthcare key with correct counts."""
    s = reader.slice_likelihood("Healthcare")
    assert s["coverage"] is True
    assert s["resolved_key"] == "healthcare"
    assert s["sector"]["incidents"] == 1710
    assert s["sector"]["breaches"] == 1542
    assert "External 73%" in s["sector"]["threat_actors"]


def test_real_estate_uses_dedicated_dbir_row(reader):
    """
    CRITICAL: Validates the step-1 crosswalk judgment end-to-end.
    Real estate should resolve to its own DBIR row, NOT construction.
    """
    s = reader.slice_likelihood("Real Estate")
    assert s["coverage"] is True
    assert s["resolved_key"] == "real_estate"
    # DBIR 2025 real_estate row has high breach ratio and BEC note
    notable = s["sector"]["notable"].lower()
    assert "bec" in notable or "wire" in notable or "breach" in notable


def test_technology_resolves_to_information(reader):
    """
    CRITICAL: Many-canonical -> one DBIR key (information covers tech/media/telecom).
    Validates that Technology maps to the shared 'information' DBIR row.
    """
    s = reader.slice_likelihood("Technology")
    assert s["resolved_key"] == "information"
    assert s["coverage"] is True
    # Information row has elevated espionage motive (36%)
    assert "36%" in s["sector"]["actor_motives"] or "Espionage" in s["sector"]["actor_motives"]


def test_overall_anchors_always_present(reader):
    """Overall anchors exist even when sector coverage is False."""
    s = reader.slice_likelihood("Healthcare")
    assert s["overall"]["ransomware_share_of_breaches"] == 0.44
    assert s["overall"]["median_ransom_paid_usd"] == 115000


def test_uncovered_industry_keeps_anchors_no_raise(reader):
    """Pharmaceuticals has no DBIR column — should return coverage=False but no exception."""
    s = reader.slice_likelihood("Pharmaceuticals")
    assert s["coverage"] is False
    assert s["resolved_key"] is None
    assert "overall" in s
    assert s["overall"]["ransomware_share_of_breaches"] == 0.44


def test_unknown_industry_no_raise(reader):
    """Bogus industry should not crash — graceful degradation."""
    s = reader.slice_likelihood("underwater basket weaving")
    assert s["coverage"] is False
    assert s["resolved_key"] is None


def test_no_derived_probability_anywhere(reader):
    """Honesty guard: no computed annual_probability, incidence_rate, etc."""
    s = reader.slice_likelihood("Healthcare")
    blob = repr(s).lower()
    forbidden = ("annual_probability", "incidence_rate", "breach_likelihood")
    for f in forbidden:
        assert f not in blob, f"Found forbidden key: {f}"


def test_pass_through_not_transformed(reader):
    """Values copied verbatim from YAML, not recomputed."""
    s = reader.slice_likelihood("Healthcare")
    assert s["sector"]["breaches"] == 1542


def test_missing_dir_is_graceful():
    """Missing directory should not crash — empty index, coverage=False."""
    r = PillarReader(pillars_dir="tests/fixtures/does_not_exist", enabled=True)
    r.load()
    s = r.slice_likelihood("Healthcare")
    assert s["coverage"] is False


def test_disabled_flag_no_ops():
    """When disabled, reader no-ops and returns coverage=False."""
    fixtures_dir = Path(__file__).parent / "fixtures" / "pillars"
    r = PillarReader(pillars_dir=str(fixtures_dir), enabled=False)
    r.load()
    s = r.slice_likelihood("Healthcare")
    assert s["coverage"] is False


# -----------------------------------------------------------------------------
# Coverage Report Test — THE KEY INTEGRITY CHECK
# -----------------------------------------------------------------------------

def test_coverage_report_all_canonicals(reader, caplog):
    """
    HIGHEST VALUE CHECK: Run coverage_report() against real DBIR file.
    
    For all ~18 canonical industries, reports which resolve to a DBIR figures
    key that actually exists. Any row showing "in_latest": False that shouldn't
    (i.e., anything except pharmaceuticals) is a crosswalk bug to fix NOW.
    
    This answers: "Is the crosswalk actually complete against this edition?"
    """
    import logging
    
    # Ensure we see WARNINGs
    with caplog.at_level(logging.WARNING):
        report = reader.coverage_report()
    
    # Print full report for human review (pytest -s to see)
    print("\n" + "="*70)
    print("COVERAGE REPORT: Canonical Industry -> DBIR Key Resolution")
    print("="*70)
    
    false_positives = []
    expected_misses = []  # pharmaceuticals correctly has no DBIR column
    
    for canonical, info in sorted(report.items()):
        resolved = info["resolved_key"]
        in_latest = info["in_latest"]
        status = "OK" if in_latest else "MISS"
        print(f"{status:4s} {canonical:30s} -> {resolved!r:25s} (in_latest={in_latest})")
        
        if not in_latest:
            if canonical == "pharmaceuticals":
                expected_misses.append(canonical)
            else:
                false_positives.append(canonical)
    
    print("="*70)
    print(f"Total industries: {len(report)}")
    print(f"Expected misses (no DBIR column): {len(expected_misses)} ({expected_misses})")
    print(f"UNEXPECTED misses (crosswalk bug): {len(false_positives)} ({false_positives})")
    print("="*70)
    
    # Hard assert: only pharmaceuticals should be missing
    assert false_positives == [], f"Crosswalk keys not in DBIR: {false_positives}"
    
    # Verify pharmaceuticals is correctly absent (validates the test logic)
    assert "pharmaceuticals" in expected_misses, "pharmaceuticals should be the only expected miss"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
