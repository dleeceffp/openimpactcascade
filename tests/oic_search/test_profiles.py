"""Tests for oic_search/profiles.py.

Enforces the structural rules that keep profiles Site-Restricted eligible:
- Every named profile other than "default" must have <= 10 domains.
- No bare TLD patterns (strings beginning with ".").
- "default" must be populated (non-empty).
- get_profile() and list_profiles() behave correctly.
"""

import pytest
from oic_search.profiles import PROFILES, SITE_RESTRICTED_ELIGIBLE, get_profile, list_profiles


# The brief designates these profiles as Site-Restricted eligible
_EXPECTED_SITE_RESTRICTED = {"framework", "threatintel", "incident", "ics"}


class TestProfileStructure:
    def test_all_expected_profiles_present(self):
        expected = {"default", "framework", "threatintel", "incident", "ics"}
        assert expected.issubset(set(PROFILES.keys())), (
            f"Missing profiles: {expected - set(PROFILES.keys())}"
        )

    def test_default_profile_is_populated(self):
        assert len(PROFILES["default"]) > 0, "default profile must not be empty"

    def test_non_default_profiles_max_10_domains(self):
        violations = {
            name: len(sites)
            for name, sites in PROFILES.items()
            if name != "default" and len(sites) > 10
        }
        assert not violations, (
            f"Profiles exceeding 10 domains (breaks Site-Restricted eligibility): {violations}"
        )

    def test_no_bare_tld_patterns(self):
        for name, sites in PROFILES.items():
            bad = [s for s in sites if s.startswith(".")]
            assert not bad, (
                f"Profile '{name}' has bare TLD patterns {bad} — "
                f"rejected by Site-Restricted CSE endpoint"
            )

    def test_no_empty_domain_entries(self):
        for name, sites in PROFILES.items():
            empty = [s for s in sites if not s.strip()]
            assert not empty, f"Profile '{name}' has empty domain entries"

    def test_all_profiles_have_at_least_one_domain(self):
        for name, sites in PROFILES.items():
            assert len(sites) >= 1, f"Profile '{name}' is empty"


class TestSiteRestrictedEligible:
    def test_expected_profiles_are_eligible(self):
        for name in _EXPECTED_SITE_RESTRICTED:
            assert SITE_RESTRICTED_ELIGIBLE.get(name) is True, (
                f"Profile '{name}' should be Site-Restricted eligible"
            )

    def test_default_is_not_eligible(self):
        # default has 22 sites — it must use the standard endpoint
        assert SITE_RESTRICTED_ELIGIBLE.get("default") is False, (
            "default profile exceeds 10 domains and must NOT be Site-Restricted eligible"
        )

    def test_eligible_flag_matches_actual_domain_count(self):
        for name, sites in PROFILES.items():
            expected = len(sites) <= 10 and not any(s.startswith(".") for s in sites)
            assert SITE_RESTRICTED_ELIGIBLE[name] == expected, (
                f"SITE_RESTRICTED_ELIGIBLE['{name}'] is stale — "
                f"expected {expected}, got {SITE_RESTRICTED_ELIGIBLE[name]}"
            )


class TestGetProfile:
    def test_returns_correct_list(self):
        assert get_profile("incident") == PROFILES["incident"]

    def test_unknown_profile_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown search profile"):
            get_profile("nonexistent_profile")

    def test_error_message_lists_available_profiles(self):
        with pytest.raises(ValueError, match="Available:"):
            get_profile("bad")


class TestListProfiles:
    def test_returns_all_profile_names(self):
        names = list_profiles()
        assert set(names) == set(PROFILES.keys())

    def test_returns_list(self):
        assert isinstance(list_profiles(), list)
