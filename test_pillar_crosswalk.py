# =============================================================================
# Acceptance tests for pillar_crosswalk.py (step 1 of the pillar-grounding layer)
# Run from project root:  python -m pytest test_pillar_crosswalk.py -v
# No files required; no network; no Flask app context.
# =============================================================================

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app", "corpus"))

from pillar_crosswalk import (
    resolve_industry_key,
    normalize_industry,
    canonical_industries,
    known_series,
    SERIES_VERIZON_DBIR,
    SERIES_IBM_BREACH,
    SERIES_NETDILIGENCE,
    ALIASES,
    CANONICAL_INDUSTRY_MAP,
)


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def test_normalize_strips_and_lowercases():
    assert normalize_industry("  Healthcare  ") == "healthcare"

def test_normalize_underscores_to_spaces():
    assert normalize_industry("Professional_Services") == "professional services"

def test_normalize_hyphens_to_spaces():
    # hyphens become spaces -> "energy utilities" -> alias fires -> "energy"
    assert normalize_industry("Energy-Utilities") == "energy"

def test_normalize_collapses_whitespace():
    assert normalize_industry("Financial   Services") == "financial services"

def test_normalize_slash_no_spaces():
    assert normalize_industry("Energy/Utilities") == "energy"

def test_normalize_slash_with_spaces():
    assert normalize_industry("Energy / Utilities") == "energy"

def test_normalize_slash_lowercase_no_spaces():
    assert normalize_industry("energy/utilities") == "energy"

def test_normalize_slash_produces_space_before_alias():
    # Verify intermediate normalized form before alias (slash → space → alias lookup)
    assert normalize_industry("Technology/Software") == "technology"
    assert normalize_industry("Hospitality / Tourism") == "hospitality"
    assert normalize_industry("Transportation / Logistics") == "transportation"
    assert normalize_industry("Government / Public Sector") == "government"
    assert normalize_industry("Manufacturing / Industrial") == "manufacturing"
    assert normalize_industry("Construction / Real Estate") == "construction"

def test_normalize_alias_financial():
    assert normalize_industry("Financial") == "financial services"
    assert normalize_industry("finance") == "financial services"

def test_normalize_alias_government():
    assert normalize_industry("Government") == "government"
    assert normalize_industry("public sector") == "government"
    assert normalize_industry("public administration") == "government"
    assert normalize_industry("Government / Public Sector") == "government"

def test_normalize_alias_manufacturing():
    assert normalize_industry("Manufacturing / Industrial") == "manufacturing"
    assert normalize_industry("Manufacturing/Industrial") == "manufacturing"

def test_normalize_alias_construction_real_estate():
    assert normalize_industry("Construction / Real Estate") == "construction"
    assert normalize_industry("Construction/Real Estate") == "construction"

def test_normalize_unknown_passes_through():
    result = normalize_industry("Underwater Basket Weaving")
    assert result == "underwater basket weaving"


# ---------------------------------------------------------------------------
# Spec acceptance tests (from oic-pillar-crosswalk-spec.md §8)
# ---------------------------------------------------------------------------

def test_aligned_industry_all_three():
    assert resolve_industry_key("Healthcare", SERIES_VERIZON_DBIR) == ["healthcare"]
    assert resolve_industry_key("Healthcare", SERIES_IBM_BREACH)   == ["healthcare"]
    assert resolve_industry_key("Healthcare", SERIES_NETDILIGENCE)  == ["healthcare"]

def test_financial_diverges_per_publisher():
    assert resolve_industry_key("financial services", SERIES_VERIZON_DBIR) == ["financial_insurance"]
    assert resolve_industry_key("financial services", SERIES_IBM_BREACH)   == ["financial"]
    assert resolve_industry_key("financial services", SERIES_NETDILIGENCE)  == ["financial_services"]

def test_manufacturing_ibm_is_industrial():
    assert resolve_industry_key("manufacturing", SERIES_IBM_BREACH) == ["industrial"]

def test_dbir_information_shared_by_three_canonicals():
    assert resolve_industry_key("technology",      SERIES_VERIZON_DBIR) == ["information"]
    assert resolve_industry_key("media",           SERIES_VERIZON_DBIR) == ["information"]
    assert resolve_industry_key("telecommunications", SERIES_VERIZON_DBIR) == ["information"]

def test_alias_resolves_financial():
    assert resolve_industry_key("financial", SERIES_IBM_BREACH) == ["financial"]

def test_alias_resolves_government():
    assert resolve_industry_key("government", SERIES_VERIZON_DBIR) == ["public_administration"]

def test_normalization_underscores_and_case():
    assert normalize_industry("Professional_Services") == "professional services"
    assert resolve_industry_key("Professional_Services", SERIES_NETDILIGENCE) == ["professional_services"]

def test_partial_coverage_pharmaceuticals():
    assert resolve_industry_key("pharmaceuticals", SERIES_IBM_BREACH)    == ["pharmaceuticals"]
    assert resolve_industry_key("pharmaceuticals", SERIES_VERIZON_DBIR)  == []
    assert resolve_industry_key("pharmaceuticals", SERIES_NETDILIGENCE)   == []

def test_unknown_series_returns_empty():
    assert resolve_industry_key("healthcare", "ibm-cost-by-region") == []

def test_unknown_industry_returns_empty():
    assert resolve_industry_key("underwater basket weaving", SERIES_VERIZON_DBIR) == []

def test_helpers_canonical_industries():
    industries = canonical_industries()
    assert "healthcare" in industries
    assert "financial services" in industries
    assert "manufacturing" in industries
    assert "construction" in industries
    assert industries == sorted(industries)   # must be sorted

def test_helpers_known_series():
    series = set(known_series())
    assert SERIES_VERIZON_DBIR in series
    assert SERIES_IBM_BREACH in series
    assert SERIES_NETDILIGENCE in series


# ---------------------------------------------------------------------------
# Real estate — its own canonical row
# ---------------------------------------------------------------------------

def test_real_estate_dbir_dedicated_row():
    assert resolve_industry_key("real estate", SERIES_VERIZON_DBIR) == ["real_estate"]

def test_real_estate_nd_folds_into_professional_services():
    # OIC judgment: ND prof_services note explicitly includes real estate
    assert resolve_industry_key("real estate", SERIES_NETDILIGENCE) == ["professional_services"]

def test_real_estate_ibm_absent():
    assert resolve_industry_key("real estate", SERIES_IBM_BREACH) == []

def test_real_estate_dropdown_value():
    # Exact new UI value from generate.html
    assert resolve_industry_key("Real Estate", SERIES_VERIZON_DBIR) == ["real_estate"]

def test_real_estate_not_routed_through_construction():
    # real estate must NOT resolve to construction's DBIR key
    assert resolve_industry_key("real estate", SERIES_VERIZON_DBIR) != ["construction"]


# ---------------------------------------------------------------------------
# Extended: construction partial coverage
# ---------------------------------------------------------------------------

def test_construction_has_dbir_coverage():
    assert resolve_industry_key("construction", SERIES_VERIZON_DBIR) == ["construction"]

def test_construction_ibm_routes_to_industrial():
    assert resolve_industry_key("construction", SERIES_IBM_BREACH) == ["industrial"]

def test_construction_no_netdiligence_coverage():
    assert resolve_industry_key("construction", SERIES_NETDILIGENCE) == []

def test_construction_dropdown_value():
    # Direct dropdown value (no alias needed)
    assert resolve_industry_key("Construction", SERIES_VERIZON_DBIR) == ["construction"]

def test_construction_legacy_combined_alias_routes_to_construction():
    # Legacy combined option routes to construction (not real estate)
    assert resolve_industry_key("Construction / Real Estate", SERIES_VERIZON_DBIR) == ["construction"]


# ---------------------------------------------------------------------------
# Extended: energy / utilities — all paths to the "energy" canonical
# ---------------------------------------------------------------------------

def test_energy_dbir_routes_to_energy_utilities():
    assert resolve_industry_key("energy", SERIES_VERIZON_DBIR) == ["energy_utilities"]

def test_energy_ibm_and_nd():
    assert resolve_industry_key("energy", SERIES_IBM_BREACH)  == ["energy"]
    assert resolve_industry_key("energy", SERIES_NETDILIGENCE) == ["energy"]

def test_energy_aliases_all_resolve():
    # All slash variants collapse to "energy utilities" via normalization, then alias -> "energy"
    for alias in ("Energy/Utilities", "energy/utilities", "Energy / Utilities",
                  "energy / utilities", "Energy & Utilities", "utilities"):
        assert resolve_industry_key(alias, SERIES_VERIZON_DBIR) == ["energy_utilities"], \
            f"Alias {alias!r} failed"

def test_energy_dropdown_value():
    # Exact current UI value from generate.html
    assert resolve_industry_key("Energy/Utilities", SERIES_VERIZON_DBIR) == ["energy_utilities"]


# ---------------------------------------------------------------------------
# Extended: every current dropdown option resolves (spec §9 requirement)
# ---------------------------------------------------------------------------

# Exact option value= strings from generate.html and generate_custom.html (both in sync)
DROPDOWN_OPTIONS = [
    "Healthcare",
    "Financial Services",
    "Retail",
    "Construction",
    "Real Estate",
    "Manufacturing",
    "Technology",
    "Education",
    "Energy/Utilities",       # submitted value; slash-normalization handles it
    "Professional Services",
    "Transportation",
    "Hospitality",
    "Government",
]

def test_all_dropdown_options_resolve_at_least_one_series():
    """Every option from /generate must resolve in at least one series."""
    misses = []
    for option in DROPDOWN_OPTIONS:
        hits = [
            resolve_industry_key(option, s)
            for s in known_series()
        ]
        if not any(hits):
            misses.append(option)
    assert misses == [], f"Dropdown options with zero resolution: {misses}"

def test_all_dropdown_options_resolve_dbir():
    """Every option should resolve in DBIR (it has the broadest coverage)."""
    misses = []
    for option in DROPDOWN_OPTIONS:
        if not resolve_industry_key(option, SERIES_VERIZON_DBIR):
            misses.append(option)
    assert misses == [], f"No DBIR key for dropdown options: {misses}"


# ---------------------------------------------------------------------------
# Extended: aliases integrity check
# ---------------------------------------------------------------------------

def test_all_alias_targets_exist_in_canonical_map():
    """Every alias value must point to a real canonical key."""
    bad = {k: v for k, v in ALIASES.items() if v not in CANONICAL_INDUSTRY_MAP}
    assert bad == {}, f"Aliases pointing to unknown canonical keys: {bad}"

def test_no_alias_key_collides_with_canonical_key():
    """Alias keys should not shadow canonical keys (would hide direct lookup)."""
    collisions = set(ALIASES.keys()) & set(CANONICAL_INDUSTRY_MAP.keys())
    assert collisions == set(), f"Alias keys that shadow canonical keys: {collisions}"
