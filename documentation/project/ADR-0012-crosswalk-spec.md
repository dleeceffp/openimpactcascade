# OIC Pillar Crosswalk — Implementation Spec

**Artifact:** `oic-pillar-crosswalk-spec`
**Status:** proposed (OIC-authored)
**Scope:** Build step 1 of N for the pillar-grounding layer — the industry
crosswalk and its resolver, as a standalone, unit-testable module. Nothing
else in the pillar pipeline is in scope here.

---

## 1. Purpose

The three pillar publishers use incompatible industry taxonomies. DBIR uses
NAICS verticals, IBM uses its own ~17 industries, NetDiligence uses ~18
sectors. The DBIR source file explicitly warns against cross-referencing its
labels to IBM's. This module is the single sanctioned bridge: one canonical OIC
industry vocabulary on the left, mapped to each publisher's own key on the
right. Every downstream pillar lookup resolves its publisher-specific key
through this module and nowhere else.

This map is **OIC-authored interpretation**. It is not endorsed by any
publisher and must be labeled as such in the file header.

## 2. Non-goals (deferred to later steps — do NOT build here)

- No YAML parsing, no file I/O, no `PillarReader`.
- No revenue/headcount band resolution (NetDiligence bands).
- No likelihood/magnitude slicing or prompt-block formatting.
- No edition selection. This module does **not** know which editions exist or
  whether a given edition's file actually contains the resolved key. It maps
  *canonical industry → publisher taxonomy key* only. The reader handles
  editions and missing-key fallback later.
- No changes to `retrieve.py`, `config.py`, or the generator in this step.

## 3. File to create

`pillar_crosswalk.py`, sitting alongside `retrieve.py`. Dependency-free
(standard library only — `logging`, `re`). This keeps step 1 testable with no
files present and no new deployment surface, mirroring the dependency-free
discipline already used in `library.py`.

## 4. Design decision: columns keyed on `comparable_series`

The map's per-publisher columns are keyed on each file's **`comparable_series`**
value — `dbir-by-industry`, `ibm-cost-by-industry`,
`netdiligence-cyber-claims` — not on a publisher name and not on a filename.

Rationale (this is the answer to "what happens at 20–30 documents"):

- **Editions collapse to one column.** All DBIR-by-industry files (2024, 2025,
  2026, …) share `comparable_series: dbir-by-industry`, so they share one
  column. Adding a new edition adds zero crosswalk rows.
- **Different cuts self-exclude.** IBM also ships a *region* series
  (`ibm-cost-by-region`) whose taxonomy is countries, not industries. Because
  it is a different `comparable_series`, it is simply not a column in this
  industry crosswalk and is excluded automatically — no special-casing.
- **A new publisher is one new column**, not a rebuild.

A flat list value (`["financial_insurance", "financial_services"]`, "try both")
resolves by accident-of-uniqueness and fails silently when two files share a
spelling. Per-publisher columns make every resolution explicit and make a
missing mapping a loud, logged miss.

## 5. Data structures

```python
# pillar_crosswalk.py
#
# OIC-AUTHORED industry crosswalk (status: proposed).
# Maps the canonical OIC industry vocabulary to each pillar publisher's own
# taxonomy key. NOT endorsed by Verizon, IBM, or NetDiligence. The DBIR source
# explicitly warns against cross-referencing NAICS labels to IBM's; this table
# is the deliberate OIC bridge and every judgment call is annotated inline.

# Column keys are `comparable_series` values, so editions stack into one column.
SERIES_DBIR = "dbir-by-industry"
SERIES_IBM  = "ibm-cost-by-industry"
SERIES_ND   = "netdiligence-cyber-claims"

# Canonical keys are lowercase, single-spaced. Value per column is a publisher
# key (str) or, where one canonical industry has no single publisher row, a
# list of keys (str | list[str]). [] / absent = no coverage in that series.
CANONICAL_INDUSTRY_MAP: dict[str, dict[str, "str | list[str]"]] = {
    "healthcare": {
        SERIES_DBIR: "healthcare",
        SERIES_IBM:  "healthcare",
        SERIES_ND:   "healthcare",
    },
    "financial services": {
        SERIES_DBIR: "financial_insurance",
        SERIES_IBM:  "financial",
        SERIES_ND:   "financial_services",
    },
    "manufacturing": {
        SERIES_DBIR: "manufacturing",
        SERIES_IBM:  "industrial",      # IBM "industrial" = chemical/engineering/manufacturing
        SERIES_ND:   "manufacturing",
    },
    "professional services": {
        SERIES_DBIR: "professional_services",
        SERIES_IBM:  "professional_services",
        SERIES_ND:   "professional_services",
    },
    "retail": {
        SERIES_DBIR: "retail",
        SERIES_IBM:  "retail",
        SERIES_ND:   "retail",
    },
    "education": {
        SERIES_DBIR: "education",
        SERIES_IBM:  "education",
        SERIES_ND:   "education",
    },
    "technology": {
        SERIES_DBIR: "information",      # OIC judgment: DBIR NAICS-51 "information" carries tech
        SERIES_IBM:  "technology",
        SERIES_ND:   "technology",
    },
    "media": {
        SERIES_DBIR: "information",      # OIC judgment: media also sits in DBIR NAICS-51
        SERIES_IBM:  "media",
        SERIES_ND:   "media",
    },
    "telecommunications": {
        SERIES_DBIR: "information",      # OIC judgment: telecom also in DBIR NAICS-51
        SERIES_IBM:  "communications",
        SERIES_ND:   "telecommunications",
    },
    "energy": {
        SERIES_DBIR: "energy_utilities",
        SERIES_IBM:  "energy",
        SERIES_ND:   "energy",
    },
    "public sector": {
        SERIES_DBIR: "public_administration",
        SERIES_IBM:  "public",
        SERIES_ND:   "public_entity",
    },
    "hospitality": {
        SERIES_DBIR: "accommodation_food",
        SERIES_IBM:  "hospitality",
        SERIES_ND:   "hospitality",
    },
    "transportation": {
        SERIES_DBIR: "transportation",
        SERIES_IBM:  "transportation",  # NOTE: present in IBM 2025, absent in IBM 2024 — reader handles edition gaps
        SERIES_ND:   "transportation",
    },
    "pharmaceuticals": {
        SERIES_IBM:  "pharmaceuticals", # partial coverage: IBM only; DBIR/ND columns intentionally absent
    },
    # EXTEND to match the GET /generate dropdown vocabulary (see §9).
}

# Optional: accept dropdown / legacy spellings without duplicating rows.
ALIASES: dict[str, str] = {
    "financial": "financial services",
    "finance": "financial services",
    "fin services": "financial services",
    "government": "public sector",
    "public administration": "public sector",
    "tech": "technology",
    "telecom": "telecommunications",
    "communications": "telecommunications",
    "energy & utilities": "energy",
    "utilities": "energy",
    "pro services": "professional services",
}
```

Notes for the implementer:

- Many canonical rows pointing to one publisher key is fine (technology, media,
  telecommunications all map to DBIR `information`). One canonical row pointing
  to a list is the rarer case; support it but do not force it — keep the
  canonical vocabulary granular enough to avoid one→many where possible.
- A column may be **absent** for a canonical industry (pharmaceuticals has no
  DBIR/ND row). Absent ≠ error; it means "no grounding from that pillar for
  this industry," which the reader will surface honestly later.

## 6. Resolver contract

```python
def normalize_industry(industry: str) -> str:
    """Lowercase, strip, convert _ and - to spaces, collapse whitespace,
    then apply ALIASES. Returns the canonical key (or the normalized string
    if no alias applies)."""

def resolve_industry_key(industry: str, series: str) -> list[str]:
    """Resolve a canonical industry to a publisher's taxonomy key(s).

    Returns a list (single-key mappings normalized to a 1-element list).
    Returns [] on any miss. Logging distinguishes the miss types:
      - unknown canonical industry  -> WARNING  (likely dropdown drift / bug)
      - known industry, series column absent -> DEBUG (expected, e.g. region cut
        or a pillar with no row for this sector)
    Never raises on a miss.
    """

def canonical_industries() -> list[str]:
    """Sorted list of canonical keys — for validating against the dropdown."""

def known_series() -> list[str]:
    """The series columns this crosswalk covers."""
```

Behavior requirements:

- `normalize_industry("  Professional_Services ")` → `"professional services"`.
- `resolve_industry_key` calls `normalize_industry` on input first.
- Single-value columns return a 1-element list; list-value columns return as-is.
- Miss returns `[]` — never `None`, never an exception. The reader decides what
  a `[]` means (skip that pillar, note the gap).
- Use the stdlib `logging` module (logger name `oic.pillar_crosswalk`),
  consistent with `context_storage.py`.

## 7. Provenance requirement

The file header comment (shown in §5) is mandatory. Every inline taxonomy
judgment (the `information`, `industrial`, `accommodation_food`,
`energy_utilities`, `public_*` mappings, and any one→many) carries a short
`# OIC judgment:` annotation so the curation reasoning is auditable in place.

## 8. Acceptance tests

Drop into `test_pillar_crosswalk.py`. All must pass before this step is "done."

```python
from pillar_crosswalk import (
    resolve_industry_key, normalize_industry,
    canonical_industries, known_series,
    SERIES_DBIR, SERIES_IBM, SERIES_ND,
)

def test_aligned_industry_all_three():
    assert resolve_industry_key("Healthcare", SERIES_DBIR) == ["healthcare"]
    assert resolve_industry_key("Healthcare", SERIES_IBM)  == ["healthcare"]
    assert resolve_industry_key("Healthcare", SERIES_ND)   == ["healthcare"]

def test_financial_diverges_per_publisher():
    assert resolve_industry_key("financial services", SERIES_DBIR) == ["financial_insurance"]
    assert resolve_industry_key("financial services", SERIES_IBM)  == ["financial"]
    assert resolve_industry_key("financial services", SERIES_ND)   == ["financial_services"]

def test_manufacturing_ibm_is_industrial():
    assert resolve_industry_key("manufacturing", SERIES_IBM) == ["industrial"]

def test_dbir_information_shared_by_three_canonicals():
    assert resolve_industry_key("technology", SERIES_DBIR)        == ["information"]
    assert resolve_industry_key("media", SERIES_DBIR)            == ["information"]
    assert resolve_industry_key("telecommunications", SERIES_DBIR) == ["information"]

def test_alias_resolves():
    assert resolve_industry_key("financial", SERIES_IBM) == ["financial"]
    assert resolve_industry_key("government", SERIES_DBIR) == ["public_administration"]

def test_normalization_underscores_and_case():
    assert normalize_industry("Professional_Services") == "professional services"
    assert resolve_industry_key("Professional_Services", SERIES_ND) == ["professional_services"]

def test_partial_coverage_returns_empty_not_error():
    # pharmaceuticals has IBM only
    assert resolve_industry_key("pharmaceuticals", SERIES_IBM)  == ["pharmaceuticals"]
    assert resolve_industry_key("pharmaceuticals", SERIES_DBIR) == []   # logs DEBUG
    assert resolve_industry_key("pharmaceuticals", SERIES_ND)   == []   # logs DEBUG

def test_unknown_series_returns_empty():
    # region cut is not an industry column
    assert resolve_industry_key("healthcare", "ibm-cost-by-region") == []

def test_unknown_industry_returns_empty():
    assert resolve_industry_key("underwater basket weaving", SERIES_DBIR) == []  # logs WARNING

def test_helpers():
    assert "healthcare" in canonical_industries()
    assert set(known_series()) >= {SERIES_DBIR, SERIES_IBM, SERIES_ND}
```

## 9. Open items to confirm before/while implementing

1. **Anchor the canonical vocabulary to the dropdown.** Pull the exact industry
   option list from `GET /generate` (in `main.py`) and make the left-hand keys
   of `CANONICAL_INDUSTRY_MAP` cover every option, normalized. Any dropdown
   option that doesn't resolve is a bug, not a default-to-nothing. Use
   `canonical_industries()` vs the dropdown list as a CI check later.
2. **Keep it in code, not YAML, for beta.** It's curated and code-reviewed; a
   Python literal documents the judgment calls inline and needs no parser. If
   non-developers ever need to edit it, externalize then — not now.
3. Confirm whether any planned pillar (e.g. a loss-dataset publisher) introduces
   a *fourth* taxonomy; if so it's just one more `SERIES_*` column.
