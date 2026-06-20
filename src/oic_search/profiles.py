"""OIC curated source profiles — the ONLY place site lists live.

Mirrors the role of MODEL_MATRIX in oic_llm/registry.py: a single source of
truth so apps never hardcode domain lists.

Profile design rules (enforced in tests/oic_search/test_profiles.py):
- Every named profile other than "default" must have <= 10 domains.
  This keeps each profile eligible for Google's Site-Restricted CSE endpoint
  (customsearch/v1/siterestrict) which carries no daily query limit.
  "default" deliberately exceeds 10 so it is annotated accordingly.
- No bare TLD patterns (e.g. ".gov") — only concrete domains or paths.
  TLD patterns are rejected by the Site-Restricted endpoint.
- Profiles are disjoint by intent; overlap is allowed but each profile is
  optimised for a distinct query type.

Profile -> Google CSE engine mapping:
  Each profile that uses Google CSE needs its own engine ID configured as an
  environment variable:  OIC_SEARCH_CSE_<PROFILE_UPPER>
  e.g.  OIC_SEARCH_CSE_DEFAULT, OIC_SEARCH_CSE_INCIDENT, OIC_SEARCH_CSE_ICS
  The registry reads these at runtime.  See registry.py.

Multi-profile queries:
  Pass profiles=["ics", "incident"] to search() for OT/ICS queries.  The
  registry will fan out, deduplicate by URL, and merge into one SearchResponse.
"""

from typing import Dict, List

# ---------------------------------------------------------------------------
# Profile definitions
# ---------------------------------------------------------------------------

PROFILES: Dict[str, List[str]] = {
    # "default" — consolidated list used when no profile is specified.
    # NOTE: 22 sites, exceeds 10-domain Site-Restricted limit.
    # Uses the standard CSE endpoint (100/day free, 10k/day paid).
    "default": [
        "attack.mitre.org",
        "cve.org",
        "nvd.nist.gov",
        "cisa.gov",
        "ic3.gov",
        "verizon.com",
        "mandiant.com",
        "microsoft.com",
        "crowdstrike.com",
        "unit42.paloaltonetworks.com",
        "talosintelligence.com",
        "enisa.europa.eu",
        "ncsc.gov.uk",
        "cyber.gc.ca",
        "dragos.com",
        "claroty.com",
        "nozominetworks.com",
        "nerc.com",
        "isa.org",
        "verisframework.org",
        "capec.mitre.org",
        "github.com/vz-risk/veris",
    ],

    # "framework" — authoritative taxonomy and vulnerability sources.
    # 7 domains: Site-Restricted eligible.
    "framework": [
        "attack.mitre.org",
        "ctid.mitre.org",
        "capec.mitre.org",
        "verisframework.org",
        "cve.org",
        "nvd.nist.gov",
        "center-for-threat-informed-defense.github.io",
    ],

    # "threatintel" — commercial and vendor threat intelligence.
    # 6 domains: Site-Restricted eligible.
    "threatintel": [
        "mandiant.com",
        "microsoft.com",
        "crowdstrike.com",
        "unit42.paloaltonetworks.com",
        "talosintelligence.com",
        "cloud.google.com",
    ],

    # "incident" — government advisories, breach statistics, and incident reports.
    # 7 domains: Site-Restricted eligible.
    "incident": [
        "cisa.gov",
        "ic3.gov",
        "verizon.com",
        "enisa.europa.eu",
        "ncsc.gov.uk",
        "cyber.gc.ca",
        "github.com/vz-risk/veris",
    ],

    # "ics" — OT/ICS-specific sources.
    # 8 domains: Site-Restricted eligible.
    # NOTE: OT attacks typically start on the IT side, so pairing "ics" +
    # "incident" is recommended for ICS/OT queries:
    #   search(q, profiles=["ics", "incident"])
    "ics": [
        "cisa.gov",
        "dragos.com",
        "claroty.com",
        "nozominetworks.com",
        "attack.mitre.org",
        "nerc.com",
        "eisac.com",
        "isa.org",
    ],
}

# Profiles that are Site-Restricted eligible (<=10 concrete domains, no TLD patterns).
# Computed at import time; used by google_cse_provider to pick the correct endpoint.
SITE_RESTRICTED_ELIGIBLE: Dict[str, bool] = {
    name: len(sites) <= 10 and not any(s.startswith(".") for s in sites)
    for name, sites in PROFILES.items()
}


def get_profile(name: str) -> List[str]:
    """Return the site list for a named profile.

    Raises:
        ValueError: If the profile name is not recognised.
    """
    if name not in PROFILES:
        available = ", ".join(sorted(PROFILES.keys()))
        raise ValueError(f"Unknown search profile: '{name}'. Available: {available}")
    return PROFILES[name]


def list_profiles() -> List[str]:
    """Return all profile names."""
    return list(PROFILES.keys())
