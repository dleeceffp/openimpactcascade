# =============================================================================
# OIC Pillar Crosswalk — Industry Taxonomy Bridge
# Status: proposed (OIC-authored interpretation)
#
# Maps the canonical OIC industry vocabulary to each pillar publisher's own
# taxonomy key. NOT endorsed by Verizon, IBM, or NetDiligence.
#
# The DBIR source explicitly warns against cross-referencing its NAICS labels
# to IBM's industry labels. This table is the deliberate OIC bridge; every
# judgment call is annotated inline with "# OIC judgment:".
#
# Column keys are `comparable_series` values from the YAML files so that:
#   - All editions of a series share one column (2024/2025/2026 DBIR = one col)
#   - Different cuts of the same publisher self-exclude (ibm-cost-by-region is
#     not an industry series and therefore has no column here)
#   - A new publisher adds one column, not a rebuild
#
# Scope (step 1 of N): crosswalk and resolver only.
# No YAML parsing, no file I/O, no PillarReader, no band resolution.
# =============================================================================

import logging
import re
from typing import Union

logger = logging.getLogger("oic.pillar_crosswalk")

# ---------------------------------------------------------------------------
# Series constants — named by publisher to avoid ambiguity at 20+ documents
# ---------------------------------------------------------------------------
SERIES_VERIZON_DBIR  = "dbir-by-industry"
SERIES_IBM_BREACH    = "ibm-cost-by-industry"
SERIES_NETDILIGENCE  = "netdiligence-cyber-claims"

# ---------------------------------------------------------------------------
# Canonical industry map
#
# Left-hand keys: canonical OIC vocabulary (lowercase, space-separated).
# Right-hand values per column:
#   str        — single publisher taxonomy key
#   list[str]  — ordered preference list: [most_representative, fallback, ...]
#                Reader contract: use the FIRST key that exists in the loaded
#                file. Do NOT average or blend multiple keys — blending
#                sub-sector rows within one publisher is itself an OIC judgment
#                and violates the never-blend discipline. If the first key is
#                absent in the edition file, try the next; log a DEBUG noting
#                the fallback. This list encodes curation order, not a set.
#   absent     — no coverage in that series for this industry; reader surfaces
#                the gap honestly rather than substituting a default.
#
# Partial-coverage rows are valid and expected. An absent column means
# "no grounding from that pillar for this industry" — not an error.
# ---------------------------------------------------------------------------
CANONICAL_INDUSTRY_MAP: dict[str, dict[str, Union[str, list[str]]]] = {

    # -------------------------------------------------------------------------
    # Full three-pillar coverage
    # -------------------------------------------------------------------------
    "healthcare": {
        SERIES_VERIZON_DBIR: "healthcare",
        SERIES_IBM_BREACH:   "healthcare",
        SERIES_NETDILIGENCE: "healthcare",
    },
    "financial services": {
        SERIES_VERIZON_DBIR: "financial_insurance",   # NAICS 52
        SERIES_IBM_BREACH:   "financial",
        SERIES_NETDILIGENCE: "financial_services",
    },
    "manufacturing": {
        SERIES_VERIZON_DBIR: "manufacturing",          # NAICS 31-33
        SERIES_IBM_BREACH:   "industrial",             # OIC judgment: IBM "industrial" = chemical/engineering/manufacturing; best available match
        SERIES_NETDILIGENCE: "manufacturing",
    },
    "professional services": {
        SERIES_VERIZON_DBIR: "professional_services",  # NAICS 54
        SERIES_IBM_BREACH:   "professional_services",  # IBM chart label "Services"
        SERIES_NETDILIGENCE: "professional_services",
    },
    "retail": {
        SERIES_VERIZON_DBIR: "retail",                 # NAICS 44-45
        SERIES_IBM_BREACH:   "retail",
        SERIES_NETDILIGENCE: "retail",
    },
    "education": {
        SERIES_VERIZON_DBIR: "education",              # NAICS 61
        SERIES_IBM_BREACH:   "education",
        SERIES_NETDILIGENCE: "education",
    },
    "energy": {
        SERIES_VERIZON_DBIR: "energy_utilities",       # OIC judgment: DBIR combines NAICS 21 (mining) + 22 (utilities) as energy_utilities
        SERIES_IBM_BREACH:   "energy",                 # IBM: oil & gas, utilities, alt energy
        SERIES_NETDILIGENCE: "energy",
    },
    "transportation": {
        SERIES_VERIZON_DBIR: "transportation",         # NAICS 48-49
        SERIES_IBM_BREACH:   "transportation",         # present in IBM 2025; absent in 2024 — reader handles edition gaps
        SERIES_NETDILIGENCE: "transportation",
    },
    "hospitality": {
        SERIES_VERIZON_DBIR: "accommodation_food",     # OIC judgment: DBIR NAICS 72 = accommodation & food services
        SERIES_IBM_BREACH:   "hospitality",
        SERIES_NETDILIGENCE: "hospitality",
    },
    "government": {
        SERIES_VERIZON_DBIR: "public_administration",  # NAICS 92
        SERIES_IBM_BREACH:   "public",
        SERIES_NETDILIGENCE: "public_entity",
    },

    # -------------------------------------------------------------------------
    # NAICS-51 "information" in DBIR covers tech, media, and telecom.
    # IBM and NetDiligence split these into separate rows.
    # Three canonical OIC verticals share one DBIR key (NAICS 51 "information").
    # This is many-canonical → one-publisher-key, not one-canonical → many.
    # The reader receives a resolved single key per call; no deduplication
    # is needed or expected — each canonical resolves independently.
    # -------------------------------------------------------------------------
    "technology": {
        SERIES_VERIZON_DBIR: "information",            # OIC judgment: DBIR NAICS 51 covers software/tech services
        SERIES_IBM_BREACH:   "technology",
        SERIES_NETDILIGENCE: "technology",
    },
    "media": {
        SERIES_VERIZON_DBIR: "information",            # OIC judgment: media sits in DBIR NAICS 51 alongside tech
        SERIES_IBM_BREACH:   "media",
        SERIES_NETDILIGENCE: "media",
    },
    "telecommunications": {
        SERIES_VERIZON_DBIR: "information",            # OIC judgment: telecom also in DBIR NAICS 51
        SERIES_IBM_BREACH:   "communications",
        SERIES_NETDILIGENCE: "telecommunications",
    },

    # -------------------------------------------------------------------------
    # Partial-coverage rows
    # -------------------------------------------------------------------------
    "real estate": {
        SERIES_VERIZON_DBIR: "real_estate",          # NAICS 53 — dedicated row with BEC/wire-fraud notable
        SERIES_NETDILIGENCE: "professional_services", # OIC judgment: ND explicitly lists real estate within its professional_services sector (see ND prof_services.sme note: "law, accounting, consulting, real estate")
        # SERIES_IBM_BREACH intentionally absent — no real-estate bucket in IBM
    },
    "construction": {
        SERIES_VERIZON_DBIR: "construction",           # NAICS 23; DBIR has a dedicated row
        SERIES_IBM_BREACH:   "industrial",             # OIC judgment: IBM "industrial" is the closest available bucket (chemical/engineering/manufacturing); treat as indicative only
        # SERIES_NETDILIGENCE intentionally absent — no construction row in ND data
    },
    "pharmaceuticals": {
        SERIES_IBM_BREACH:   "pharmaceuticals",
        # SERIES_VERIZON_DBIR and SERIES_NETDILIGENCE intentionally absent
    },
    "entertainment": {
        SERIES_VERIZON_DBIR: "entertainment",          # NAICS 71
        SERIES_IBM_BREACH:   "entertainment",          # present in IBM 2024; absent in some editions — reader handles
        SERIES_NETDILIGENCE: "entertainment",
    },
}

# ---------------------------------------------------------------------------
# Aliases — accept UI dropdown values and common alternate spellings without
# duplicating canonical map rows.
#
# IMPORTANT: All keys here must be written in their POST-normalization form
# (after normalize_industry's slash, underscore, case, and whitespace steps
# have been applied). The normalize_industry function normalizes FIRST, then
# does an exact-match lookup in this dict. Any key containing a raw slash,
# underscore, or mixed case will never be matched.
#
# To derive the correct alias key from a raw string: run normalize_industry
# on it with ALIASES = {} and use the resulting string as the key.
#
# Values must be existing keys in CANONICAL_INDUSTRY_MAP.
# ---------------------------------------------------------------------------
ALIASES: dict[str, str] = {
    # Financial
    "financial":                      "financial services",
    "finance":                        "financial services",
    "financial services banking":     "financial services",   # value="Financial Services / Banking" after slash-norm
    "fin services":                   "financial services",
    "banking":                        "financial services",

    # Government
    "public sector":                  "government",
    "public administration":          "government",
    "government public sector":       "government",           # value="Government / Public Sector" after slash-norm

    # Technology
    "tech":                           "technology",
    "technology software":            "technology",           # value="Technology / Software" after slash-norm
    "software":                       "technology",

    # Telecom
    "telecom":                        "telecommunications",
    "communications":                 "telecommunications",

    # Energy — "Energy/Utilities" and all spacing variants collapse to "energy utilities"
    "energy utilities":               "energy",               # covers Energy/Utilities, Energy / Utilities, energy/utilities
    "energy & utilities":             "energy",               # ampersand form; & is not a slash so kept as alias
    "utilities":                      "energy",

    # Manufacturing
    "manufacturing industrial":       "manufacturing",        # value="Manufacturing / Industrial" after slash-norm
    "industrial":                     "manufacturing",        # OIC judgment: route bare "industrial" to manufacturing; construction is separate

    # Construction — current dropdown emits "Construction" directly (canonical hit, no alias needed).
    # This alias handles any legacy combined value by routing to construction.
    # Real estate is its own canonical in CANONICAL_INDUSTRY_MAP.
    "construction real estate":       "construction",         # legacy combined value after slash-norm; OIC judgment: routes to construction

    # Hospitality
    "hospitality tourism":            "hospitality",          # value="Hospitality / Tourism" after slash-norm
    "tourism":                        "hospitality",

    # Transportation
    "transportation logistics":       "transportation",       # value="Transportation / Logistics" after slash-norm
    "logistics":                      "transportation",

    # Professional services
    "pro services":                   "professional services",
    "legal":                          "professional services",
    "accounting":                     "professional services",
    "consulting":                     "professional services",
    "professional services (legal, accounting, consulting)": "professional services",  # display text that may arrive verbatim

}


# ---------------------------------------------------------------------------
# Resolver API
# ---------------------------------------------------------------------------

def normalize_industry(industry: str) -> str:
    r"""Normalize an industry string to a canonical lookup key.

    Steps (in order):
      1. Strip leading/trailing whitespace and lowercase.
      2. Replace underscores and hyphens with spaces.
      3. Collapse \s*/\s* (slash with optional surrounding spaces) to a
         single space — so "Energy/Utilities", "Energy / Utilities", and
         "energy / utilities" all produce "energy utilities" before alias
         lookup. This means ALIASES keys must be written in their
         post-slash-normalization form.
      4. Collapse runs of whitespace to a single space.
      5. Apply ALIASES (exact match on the normalized string).

    Returns the canonical key if an alias matches, otherwise the normalized
    string (which may or may not exist in CANONICAL_INDUSTRY_MAP).

    Examples:
        normalize_industry("  Professional_Services ") -> "professional services"
        normalize_industry("Energy/Utilities")         -> "energy"
        normalize_industry("Energy / Utilities")       -> "energy"
        normalize_industry("Healthcare")               -> "healthcare"
        normalize_industry("Construction / Real Estate") -> "construction"
    """
    normalized = industry.strip().lower()
    normalized = re.sub(r"[_\-]+", " ", normalized)
    normalized = re.sub(r"\s*/\s*", " ", normalized)   # slash normalization
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return ALIASES.get(normalized, normalized)


def resolve_industry_key(industry: str, series: str) -> list[str]:
    """Resolve a canonical industry name to the publisher's taxonomy key(s).

    Args:
        industry: Industry name in any supported spelling (normalized internally).
        series:   A `comparable_series` value, e.g. SERIES_VERIZON_DBIR.

    Returns:
        A list of publisher taxonomy key strings (single-key mappings return a
        1-element list; list-value mappings return as-is). Returns [] on any miss.

    Logging:
        WARNING  — industry not found in canonical map after normalization
                   (likely a dropdown drift or a typo; caller should surface this)
        DEBUG    — industry found but series column absent
                   (expected for partial-coverage rows, or wrong series cut)
    """
    canonical = normalize_industry(industry)
    row = CANONICAL_INDUSTRY_MAP.get(canonical)

    if row is None:
        logger.warning(
            "resolve_industry_key: unknown canonical industry %r "
            "(normalized from %r) for series %r",
            canonical, industry, series,
        )
        return []

    value = row.get(series)

    if value is None:
        logger.debug(
            "resolve_industry_key: industry %r has no coverage in series %r",
            canonical, series,
        )
        return []

    if isinstance(value, list):
        return value
    return [value]


def canonical_industries() -> list[str]:
    """Sorted list of canonical industry keys defined in this crosswalk.

    Use to validate the /generate dropdown: every dropdown option (normalized)
    should appear here or in ALIASES.
    """
    return sorted(CANONICAL_INDUSTRY_MAP.keys())


def known_series() -> list[str]:
    """The comparable_series columns this crosswalk covers."""
    return [SERIES_VERIZON_DBIR, SERIES_IBM_BREACH, SERIES_NETDILIGENCE]
