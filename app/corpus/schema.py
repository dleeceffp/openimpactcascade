"""
OIC corpus frontmatter schema, controlled vocabularies, source governance, and
validation.

Single source of truth for:
  - app/corpus/build_index.py   CI gate: rejects invalid or excluded documents
  - app/corpus/ingest.py        proposes + validates generated frontmatter
  - app/corpus/retrieve.py      selection reads validated index records
  - the web-search gap path     resolve_web_usage(url) -> link_only vs summarize

Governance has TWO independent axes (see ADR-0012 §5.2):

  license_usage  — may this source be INGESTED into the corpus and generated from?
                   This is the original ISACA/ISC2 exclusion. Enforced at build time.

  web_usage      — when a LIVE web-search result comes from this source, may the
                   model summarize/paraphrase it, or only cite the link?
                   Web results have no frontmatter, so this is resolved at runtime
                   from a domain/org policy table, not (only) from a file.

The distinction that matters legally is "reproducing/generating from" vs
"pointing at". ISACA/ISC2 et al.: license_usage=excluded (never in corpus),
web_usage=link_only (surface the URL as a citation, never inject the body).

No third-party dependencies; frontmatter PARSING (YAML) lives in build_index.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Any
from urllib.parse import urlparse

SCHEMA_VERSION = "1.1.0"  # 1.1.0 adds web_usage / link_only governance

# ─────────────────────────────────────────────────────────────────────────────
# Controlled vocabularies (validate against these; pass them into ingest prompts)
# ─────────────────────────────────────────────────────────────────────────────
SOURCE_ORGS = frozenset({
    "NIST", "CISA", "CCCS", "OWASP", "MITRE", "FAIR-Institute",
    "CaffeinatedRisk", "ISACA", "ISC2", "SANS", "other",
})
SOURCE_TYPES = frozenset({
    "standards_body", "regulator", "advisory", "academic",
    "vendor", "analyst", "original_analysis",
})
INDUSTRIES = frozenset({
    "healthcare", "finance", "government", "energy",
    "retail", "technology", "manufacturing", "cross_industry",
})
REGIONS = frozenset({"Canada", "US", "EU", "UK", "global"})
DOC_TYPES = frozenset({
    "standard", "framework", "guideline", "regulatory", "advisory",
    "runbook", "incident_report", "whitepaper", "academic_paper",
    "original_analysis",
})
DOMAINS = frozenset({
    "Identity", "Network", "Endpoint", "Cloud", "DevSecOps",
    "OT/ICS", "Physical", "Governance/ESRM",
})
SCENARIO_TAGS = frozenset({
    "ransomware", "BEC", "data_exfil", "insider_threat", "supply_chain",
    "phishing", "ddos", "web_app", "credential_stuffing",
    "cloud_misconfig", "third_party",
})
LIFECYCLE_STAGES = frozenset({
    "strategy", "design", "implementation", "operations",
    "incident_response", "audit", "training",
})
FAIR_COMPONENTS = frozenset({
    "TEF", "vulnerability", "LEF", "LM", "controls", "secondary_loss",
})
FRESHNESS = frozenset({"low", "medium", "high"})
STATUSES = frozenset({"active", "draft", "deprecated"})

# Governance vocabularies
LICENSE_USAGE = frozenset({"ok_to_ground", "ok_to_quote", "reference_only", "excluded"})
WEB_USAGE = frozenset({"ok_to_summarize", "link_only", "blocked"})

# Named constants (use these instead of bare strings in code)
LICENSE_GROUND = "ok_to_ground"
LICENSE_QUOTE = "ok_to_quote"
LICENSE_REFERENCE = "reference_only"
LICENSE_EXCLUDED = "excluded"

WEB_OK = "ok_to_summarize"
WEB_LINK_ONLY = "link_only"
WEB_BLOCKED = "blocked"

MITRE_RE = re.compile(r"^T\d{4}(?:\.\d{3})?$")


# ─────────────────────────────────────────────────────────────────────────────
# Source governance — the shared policy consulted by ingest AND the search path
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Governance:
    """Default governance for a source. `license_usage` gates corpus ingestion;
    `web_usage` gates how live web-search results from this source are handled."""
    license_usage: str
    web_usage: str
    note: str = ""


# Keyed by SOURCE_ORG. Orgs whose ToS prohibit AI grounding are excluded from the
# corpus but may still be referenced by link on the web.
SOURCE_GOVERNANCE: dict[str, Governance] = {
    # AI-grounding-restricted professional bodies: never ingest, link only on web.
    "ISACA": Governance(LICENSE_EXCLUDED, WEB_LINK_ONLY,
                        "ToS restricts AI grounding. Reference by link only; do not inject body."),
    "ISC2":  Governance(LICENSE_EXCLUDED, WEB_LINK_ONLY,
                        "ToS restricts AI grounding. Reference by link only; do not inject body."),
    # Public authoritative sources: ground freely, summarize web results.
    "NIST":           Governance(LICENSE_GROUND, WEB_OK),
    "CISA":           Governance(LICENSE_GROUND, WEB_OK),
    "CCCS":           Governance(LICENSE_GROUND, WEB_OK),
    "OWASP":          Governance(LICENSE_GROUND, WEB_OK),
    "MITRE":          Governance(LICENSE_GROUND, WEB_OK),
    "FAIR-Institute": Governance(LICENSE_QUOTE,  WEB_OK,
                        "Open FAIR ontology is public; confirm quoting limits for deeper material."),
    "SANS":           Governance(LICENSE_REFERENCE, WEB_LINK_ONLY,
                        "Mixed licensing; default conservative until reviewed per-asset."),
    # Your own content.
    "CaffeinatedRisk": Governance(LICENSE_GROUND, WEB_OK, "Original transformative analysis."),
    # Unknown.
    "other":          Governance(LICENSE_REFERENCE, WEB_OK, "Unknown source; conservative default."),
}

# Domain-substring governance for WEB results (which carry no source_org).
# First match wins; extend as new sources appear in gap-fill searches.
DOMAIN_GOVERNANCE: tuple[tuple[str, Governance], ...] = (
    ("isaca.org",  SOURCE_GOVERNANCE["ISACA"]),
    ("isc2.org",   SOURCE_GOVERNANCE["ISC2"]),
    ("sans.org",   SOURCE_GOVERNANCE["SANS"]),
    ("nist.gov",   SOURCE_GOVERNANCE["NIST"]),
    ("cisa.gov",   SOURCE_GOVERNANCE["CISA"]),
    ("cyber.gc.ca", SOURCE_GOVERNANCE["CCCS"]),
    ("owasp.org",  SOURCE_GOVERNANCE["OWASP"]),
    ("mitre.org",  SOURCE_GOVERNANCE["MITRE"]),
)

DEFAULT_GOVERNANCE = Governance(LICENSE_REFERENCE, WEB_OK, "Unmapped source; safe default.")


def governance_for_org(org: str | None) -> Governance:
    return SOURCE_GOVERNANCE.get(org or "other", DEFAULT_GOVERNANCE)


def governance_for_domain(domain: str) -> Governance:
    d = (domain or "").lower()
    for needle, gov in DOMAIN_GOVERNANCE:
        if needle in d:
            return gov
    return DEFAULT_GOVERNANCE


def governance_for_url(url: str) -> Governance:
    return governance_for_domain(urlparse(url or "").netloc)


def resolve_web_usage(url_or_domain: str) -> str:
    """Used by the web-search gap path. Returns one of WEB_USAGE.

      ok_to_summarize -> may inject result text into the prompt and paraphrase (with citation)
      link_only       -> return the URL as a citation card ONLY; do NOT inject body text
      blocked         -> do not surface the result at all
    """
    target = url_or_domain or ""
    gov = governance_for_url(target) if "://" in target or "." in target.split("/")[0] \
        else governance_for_domain(target)
    return gov.web_usage


def is_ingestable(org: str | None, license_usage: str | None = None) -> bool:
    """True if content from this org/license may be written into the corpus."""
    eff = license_usage or governance_for_org(org).license_usage
    return eff != LICENSE_EXCLUDED


# ─────────────────────────────────────────────────────────────────────────────
# The document metadata record (frontmatter)
# ─────────────────────────────────────────────────────────────────────────────
REQUIRED_FIELDS = (
    "id", "title", "version", "source_url", "source_org", "source_type",
    "publication_year", "retrieved_date", "industry", "region", "doc_type",
    "primary_domain", "quality_rating", "curator_notes", "freshness_sensitivity",
    "last_reviewed", "license_usage", "status", "include_in_free_tier",
)

# field -> allowed-set, for scalar enum fields
_SCALAR_ENUMS = {
    "source_org": SOURCE_ORGS,
    "source_type": SOURCE_TYPES,
    "doc_type": DOC_TYPES,
    "primary_domain": DOMAINS,
    "freshness_sensitivity": FRESHNESS,
    "status": STATUSES,
    "license_usage": LICENSE_USAGE,
    "web_usage": WEB_USAGE,
}
# field -> allowed-set, for array enum fields
_ARRAY_ENUMS = {
    "industry": INDUSTRIES,
    "region": REGIONS,
    "secondary_domains": DOMAINS,
    "scenario_tags": SCENARIO_TAGS,
    "lifecycle_stage": LIFECYCLE_STAGES,
    "fair_components": FAIR_COMPONENTS,
}


@dataclass
class DocMeta:
    # identity & provenance
    id: str
    title: str
    version: str
    source_url: str
    source_org: str
    source_type: str
    publication_year: int
    retrieved_date: str           # ISO date
    # classification facets
    industry: list[str]
    region: list[str]
    doc_type: str
    primary_domain: str
    # curation & quality
    quality_rating: int
    curator_notes: str
    freshness_sensitivity: str
    last_reviewed: str            # ISO date
    # governance & licensing
    license_usage: str
    # retrieval control
    status: str
    include_in_free_tier: bool
    # optional
    secondary_domains: list[str] = field(default_factory=list)
    scenario_tags: list[str] = field(default_factory=list)
    lifecycle_stage: list[str] = field(default_factory=list)
    mitre_techniques: list[str] = field(default_factory=list)
    fair_components: list[str] = field(default_factory=list)
    authority_basis: str = ""
    license_note: str = ""
    attribution_required: bool = False
    web_usage: str | None = None      # if None, defaults from source-org governance
    priority_weight: float = 1.0
    # auto-populated by build_index.py
    content_hash: str = ""
    max_tokens_hint: int = 0

    def effective_web_usage(self) -> str:
        return self.web_usage or governance_for_org(self.source_org).web_usage

    def to_index_record(self) -> dict[str, Any]:
        rec = asdict(self)
        rec["web_usage"] = self.effective_web_usage()
        return rec


def apply_governance_defaults(meta: dict[str, Any]) -> dict[str, Any]:
    """Fill web_usage from the source-org policy if absent. Non-destructive copy."""
    out = dict(meta)
    if not out.get("web_usage"):
        out["web_usage"] = governance_for_org(out.get("source_org")).web_usage
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Validation — the CI gate. Returns a list of human-readable errors ([] == ok).
# ─────────────────────────────────────────────────────────────────────────────
def validate(meta: dict[str, Any], *, source: str = "<doc>") -> list[str]:
    """Validate a frontmatter dict against the schema and governance rules.

    Hard-fails (these MUST keep excluded content out of the corpus):
      - license_usage == "excluded"                      -> never ingestable
      - source_org governance is excluded but the doc claims a grounding license
    """
    errors: list[str] = []
    m = apply_governance_defaults(meta)

    # required present
    for f in REQUIRED_FIELDS:
        if m.get(f) in (None, "", []):
            errors.append(f"{source}: missing required field '{f}'")

    # scalar enums
    for f, allowed in _SCALAR_ENUMS.items():
        v = m.get(f)
        if v is not None and v not in allowed:
            errors.append(f"{source}: '{f}'='{v}' not in {sorted(allowed)}")

    # array enums
    for f, allowed in _ARRAY_ENUMS.items():
        vals = m.get(f) or []
        if not isinstance(vals, list):
            errors.append(f"{source}: '{f}' must be a list")
            continue
        for v in vals:
            if v not in allowed:
                errors.append(f"{source}: '{f}' has invalid value '{v}'")

    # quality_rating 1..5
    qr = m.get("quality_rating")
    if qr is not None and (not isinstance(qr, int) or not (1 <= qr <= 5)):
        errors.append(f"{source}: 'quality_rating' must be an int 1-5 (got {qr!r})")

    # publication_year sane
    yr = m.get("publication_year")
    if yr is not None and (not isinstance(yr, int) or not (1990 <= yr <= 2100)):
        errors.append(f"{source}: 'publication_year' looks wrong ({yr!r})")

    # MITRE technique format
    for t in (m.get("mitre_techniques") or []):
        if not MITRE_RE.match(str(t)):
            errors.append(f"{source}: mitre technique '{t}' not in Txxxx[.xxx] form")

    # ── GOVERNANCE GATES ──────────────────────────────────────────────
    lic = m.get("license_usage")
    org = m.get("source_org")
    if lic == LICENSE_EXCLUDED:
        errors.append(
            f"{source}: license_usage='excluded' — this source must NOT be in the corpus "
            f"(reference it via web link_only instead). See ADR-0012 §5.2."
        )
    org_gov = governance_for_org(org)
    if org_gov.license_usage == LICENSE_EXCLUDED and lic in (LICENSE_GROUND, LICENSE_QUOTE):
        errors.append(
            f"{source}: source_org='{org}' is grounding-excluded by policy "
            f"({org_gov.note}) but license_usage='{lic}'. Refuse ingest."
        )

    return errors


def assert_valid(meta: dict[str, Any], *, source: str = "<doc>") -> DocMeta:
    """Validate and return a DocMeta, or raise ValueError listing all problems."""
    errs = validate(meta, source=source)
    if errs:
        raise ValueError("Frontmatter validation failed:\n  - " + "\n  - ".join(errs))
    known = {f for f in DocMeta.__dataclass_fields__}  # type: ignore[attr-defined]
    return DocMeta(**{k: v for k, v in apply_governance_defaults(meta).items() if k in known})


def vocab_for_prompt() -> dict[str, list[str]]:
    """Controlled vocabularies as sorted lists, for seeding the ingest LLM prompt
    so it can only propose valid values (the LLM proposes, the schema disposes)."""
    return {
        "source_org": sorted(SOURCE_ORGS),
        "source_type": sorted(SOURCE_TYPES),
        "industry": sorted(INDUSTRIES),
        "region": sorted(REGIONS),
        "doc_type": sorted(DOC_TYPES),
        "primary_domain": sorted(DOMAINS),
        "scenario_tags": sorted(SCENARIO_TAGS),
        "lifecycle_stage": sorted(LIFECYCLE_STAGES),
        "fair_components": sorted(FAIR_COMPONENTS),
        "freshness_sensitivity": sorted(FRESHNESS),
    }
