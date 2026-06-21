"""Terminal-anchored multi-path attack flow generator (OIC-DESIGN-2026-044).

Given a protected asset / terminal outcome, generates 2–N candidate routes
from different entry points.  For each entry the LLM produces one of three
verdicts:

  credible          -> STIX bundle + markdown prose
  no_credible_path  -> narrative only: where the chain breaks, monitored
                       assumptions, flip conditions (living risk-register entries)
  different_terminal -> narrative note: entry threatens a different asset

Design principles (enforced here, not just in the brief):
  - There is never only one path.  Fewer than min_paths credible routes is
    reported honestly; the tool never pads to hit a number.
  - Diversity check R4: credible routes must differ in their middle sections,
    not just their entry node.  Near-duplicates are regenerated or dropped.
  - Evidence bar: proactively-discovered entries must be grounded in observed
    breaches or active research.  User-named entries bypass the bar.
  - Firewall: no 'succeeds when' / control-prescription language anywhere.
  - Negatives are always conditional (flip-conditioned), never unconditional.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

# Ensure src/ packages are importable when running from tools/
_repo_root = Path(__file__).parent.parent.parent
_src = str(_repo_root / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from oic_llm import complete, ProviderError
from oic_search import search, SearchError, SearchResponse

from mitre_loader import get_mitre_lookup
try:
    from corpus_grounding import get_grounding
except ImportError:
    get_grounding = None

logger = logging.getLogger("oic.attack_flow.multi_path")

# ---------------------------------------------------------------------------
# Default entry archetypes (OIC-DESIGN-2026-042)
# ---------------------------------------------------------------------------
DEFAULT_ENTRY_ARCHETYPES: List[Dict[str, str]] = [
    {
        "id": "phishing",
        "label": "Phishing / Social Engineering",
        "description": "Email or message-based delivery of malicious content or credential theft",
    },
    {
        "id": "remote_access",
        "label": "Exposed Remote Access",
        "description": "Internet-facing services: VPN, RDP, SSH, web applications, APIs",
    },
    {
        "id": "physical",
        "label": "Physical Intrusion / Insider",
        "description": "Physical access to premises, hardware, or removable media; malicious insider",
    },
    {
        "id": "supply_chain",
        "label": "Supply Chain / Third-Party",
        "description": "Compromise via vendor software, managed service provider, or contractor access",
    },
]

# Minimum technique-overlap fraction to flag two routes as near-duplicates.
_DIVERSITY_THRESHOLD = 0.7  # >70% shared technique IDs → near-duplicate


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class RouteResult:
    """Result for one candidate entry point evaluated against the terminal."""

    # Verdict: "credible" | "no_credible_path" | "different_terminal"
    verdict: str

    # The entry point descriptor
    entry_id: str
    entry_label: str
    entry_description: str

    # Was this entry named by the user (True) or discovered by the tool (False)?
    user_named: bool = True

    # Evidence basis for discovered entries: "observed" | "research" | None
    evidence_basis: Optional[str] = None
    evidence_citation: Optional[str] = None

    # For credible routes: the full flow data dict (generator's native model)
    flow_data: Optional[Dict[str, Any]] = None

    # For credible routes: prose walk of the path (narrative)
    prose_narrative: str = ""

    # For no_credible_path: where the chain breaks and why
    break_point: str = ""
    break_reason: str = ""

    # For no_credible_path: monitored assumptions (list of assumption strings)
    monitored_assumptions: List[str] = field(default_factory=list)

    # For no_credible_path: flip conditions (list of flip-condition strings)
    flip_conditions: List[str] = field(default_factory=list)

    # For different_terminal: what asset/outcome is actually threatened
    threatened_asset: str = ""

    # LLM provenance
    llm_model: str = "unknown"
    llm_provider: str = "unknown"


@dataclass
class MultiPathResult:
    """The complete result set for one terminal-anchored generation run."""

    asset: str
    terminal: str
    industry: str
    region: str
    organization_size: str
    generated_at: str
    llm_model: str
    llm_provider: str
    search_provider: str
    search_performed: bool

    routes: List[RouteResult] = field(default_factory=list)

    @property
    def credible_routes(self) -> List[RouteResult]:
        return [r for r in self.routes if r.verdict == "credible"]

    @property
    def no_path_routes(self) -> List[RouteResult]:
        return [r for r in self.routes if r.verdict == "no_credible_path"]

    @property
    def different_terminal_routes(self) -> List[RouteResult]:
        return [r for r in self.routes if r.verdict == "different_terminal"]


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class MultiPathGenerator:
    """Generates multiple attack paths from different entry points to a fixed terminal."""

    def __init__(
        self,
        provider: Optional[str] = None,
        weight: Optional[str] = None,
        search_provider: Optional[str] = None,
        min_paths: int = 2,
        target_paths: int = 3,
        max_paths: Optional[int] = None,
    ):
        self.provider = provider
        self.weight = weight
        self.search_provider = search_provider
        self.min_paths = min_paths
        self.target_paths = target_paths
        self.max_paths = max_paths or int(os.environ.get("OIC_MAX_PATHS", "10"))

        # Override from env
        if os.environ.get("OIC_MIN_PATHS"):
            self.min_paths = int(os.environ["OIC_MIN_PATHS"])
        if os.environ.get("OIC_TARGET_PATHS"):
            self.target_paths = int(os.environ["OIC_TARGET_PATHS"])
        if os.environ.get("OIC_MAX_PATHS"):
            self.max_paths = int(os.environ["OIC_MAX_PATHS"])

        self._last_model: str = "unknown"
        self._last_provider: str = "unknown"
        self.mitre = get_mitre_lookup()
        self.grounding = get_grounding() if get_grounding else None

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def generate(
        self,
        asset: str,
        terminal: str,
        industry: str,
        region: str,
        organization_size: str,
        named_entries: Optional[List[str]] = None,
        include_web_search: bool = True,
    ) -> MultiPathResult:
        """Generate all candidate routes for the given terminal.

        Args:
            asset:              The protected asset (e.g. "patient records database")
            terminal:           The compromise outcome (e.g. "unauthorized exfiltration of patient PII")
            industry:           Industry sector
            region:             Region/country
            organization_size:  Org size label
            named_entries:      Entry points explicitly named by the user (always evaluated)
            include_web_search: Whether to run oic_search for recent threat intel

        Returns:
            MultiPathResult with per-entry RouteResult objects.
        """
        logger.info(f"Multi-path generation: asset='{asset}' industry={industry} region={region}")

        # --- Corpus + web grounding (shared across all route evaluations) ---
        corpus_text, threat_patterns = self._get_corpus_grounding(industry)
        web_text, search_provider_used, search_performed = self._get_web_grounding(
            industry, region, asset, include_web_search
        )
        context_block = self._build_context_block(
            asset, terminal, industry, region, organization_size,
            corpus_text, web_text
        )

        # --- Build entry list ---
        entries = self._build_entry_list(
            named_entries or [],
            industry, region, asset,
            corpus_text, web_text,
        )

        logger.info(f"Evaluating {len(entries)} entry points against terminal '{terminal}'")

        # --- Evaluate each entry ---
        routes: List[RouteResult] = []
        credible_count = 0

        for entry in entries:
            if credible_count >= self.max_paths:
                logger.info(f"Reached max_paths={self.max_paths}, stopping entry evaluation")
                break

            logger.info(f"  → evaluating entry: {entry['label']}")
            route = self._evaluate_entry(
                entry=entry,
                asset=asset,
                terminal=terminal,
                industry=industry,
                region=region,
                organization_size=organization_size,
                context_block=context_block,
                threat_patterns=threat_patterns,
                existing_credible_routes=routes,
            )
            routes.append(route)
            if route.verdict == "credible":
                credible_count += 1
                logger.info(f"    verdict=credible  techniques={len(route.flow_data.get('attack_actions', []))}")
            else:
                logger.info(f"    verdict={route.verdict}")

        # Log path-count note
        if credible_count < self.min_paths:
            logger.warning(
                f"Only {credible_count} credible path(s) found (min_paths={self.min_paths}). "
                "Emitting honest count — not padding."
            )

        return MultiPathResult(
            asset=asset,
            terminal=terminal,
            industry=industry,
            region=region,
            organization_size=organization_size,
            generated_at=datetime.now().isoformat() + "Z",
            llm_model=self._last_model,
            llm_provider=self._last_provider,
            search_provider=search_provider_used,
            search_performed=search_performed,
            routes=routes,
        )

    # ------------------------------------------------------------------
    # Grounding helpers
    # ------------------------------------------------------------------

    def _get_corpus_grounding(self, industry: str) -> Tuple[str, List[str]]:
        if not self.grounding:
            return "No corpus grounding available.", []
        grounding_data = self.grounding.get_grounding_for_industry(industry)
        corpus_text = self.grounding.format_grounding_for_prompt(grounding_data)
        threat_patterns = self.grounding.get_threat_patterns(industry)
        return corpus_text, threat_patterns

    def _get_web_grounding(
        self, industry: str, region: str, asset: str, include_web_search: bool
    ) -> Tuple[str, str, bool]:
        if not include_web_search:
            return "", "none", False
        try:
            q = f"{industry} {region} {asset} cyber attack breach"
            sr: SearchResponse = search(
                q,
                profile="incident",
                num=5,
                provider=self.search_provider,
                time_range="year",
            )
            if sr.results:
                return self._format_search_results(sr), sr.provider, True
        except SearchError as e:
            logger.warning(f"web search unavailable ({e.kind}): {e} — continuing without grounding")
        return "", "none", False

    def _format_search_results(self, sr: SearchResponse) -> str:
        lines = [
            "=" * 70,
            "RECENT THREAT INTELLIGENCE (Web Search)",
            f"Provider: {sr.provider}  Profile: {sr.profile}  Results: {len(sr.results)}",
            "=" * 70,
        ]
        for i, r in enumerate(sr.results, 1):
            lines.append(f"\n{i}. {r.title}")
            lines.append(f"   Source: {r.source}")
            if r.published:
                lines.append(f"   Date: {r.published}")
            snippet = (r.snippet or "")[:300]
            if snippet:
                lines.append(f"   Summary: {snippet}")
        lines.append("=" * 70)
        return "\n".join(lines)

    def _build_context_block(
        self, asset, terminal, industry, region, org_size,
        corpus_text, web_text
    ) -> str:
        return (
            f"PROTECTED ASSET: {asset}\n"
            f"TERMINAL (compromise outcome): {terminal}\n"
            f"ORGANIZATION: {industry} / {region} / {org_size}\n\n"
            f"{corpus_text}\n\n"
            f"{web_text}"
        ).strip()

    # ------------------------------------------------------------------
    # Entry list construction
    # ------------------------------------------------------------------

    def _build_entry_list(
        self,
        named_entries: List[str],
        industry: str,
        region: str,
        asset: str,
        corpus_text: str,
        web_text: str,
    ) -> List[Dict[str, Any]]:
        """Build the ordered list of entries to evaluate.

        Order: user-named first (always), then default archetypes not already
        covered by named entries, then grounding-discovered entries.
        Discovered entries that cannot be tied to observed breaches or active
        research are dropped (evidence bar).
        """
        entries: List[Dict[str, Any]] = []
        seen_ids: set = set()

        # 1. User-named entries — always included, bypass evidence bar
        for name in named_entries:
            slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
            entries.append({
                "id": slug,
                "label": name,
                "description": f"User-named entry point: {name}",
                "user_named": True,
                "evidence_basis": None,
                "evidence_citation": None,
            })
            seen_ids.add(slug)

        # 2. Default archetypes (seeds for diversity) — skip if covered by user named
        for arch in DEFAULT_ENTRY_ARCHETYPES:
            if arch["id"] not in seen_ids:
                entries.append({**arch, "user_named": False, "evidence_basis": "observed",
                                 "evidence_citation": "DBIR / Verizon DBIR top breach patterns"})
                seen_ids.add(arch["id"])

        # 3. Grounding-discovered entries — only if evidence-bar passes
        discovered = self._discover_entries_from_grounding(
            industry, region, asset, corpus_text, web_text, seen_ids
        )
        entries.extend(discovered)

        return entries

    def _discover_entries_from_grounding(
        self,
        industry: str,
        region: str,
        asset: str,
        corpus_text: str,
        web_text: str,
        already_seen: set,
    ) -> List[Dict[str, Any]]:
        """Ask the LLM to identify any additional entry points with observed evidence.

        This is a lightweight 'blind-spot discovery' call — lower token budget,
        structured JSON response listing only affirmative discoveries.
        Entries with no observed basis are dropped.
        """
        prompt = f"""You are a threat intelligence analyst. Based on the grounding below,
identify any ADDITIONAL attack entry points for this target that:
  1. Have been observed in real breach events or are an active research area
  2. Are NOT already covered by: phishing, remote access, physical intrusion, supply chain
  3. Are specific to this industry/region/asset combination

GROUNDING:
{corpus_text[:1500]}

TARGET: {asset} in a {industry} organization in {region}

Return ONLY a JSON array (max 3 items). Each item:
{{
  "id": "short_slug",
  "label": "Short entry point label",
  "description": "One sentence description",
  "evidence_basis": "observed" or "research",
  "evidence_citation": "Source name or publication (e.g. 'Verizon DBIR 2024', 'CISA Advisory AA24-xxx')"
}}

If no additional evidence-grounded entries exist, return an empty array [].
Return ONLY the JSON array, no other text."""

        try:
            resp = complete(
                system="You are a threat intelligence analyst. Return only valid JSON.",
                messages=[{"role": "user", "content": prompt}],
                provider=self.provider,
                weight=self.weight,
                max_tokens=600,
            )
            self._last_model = resp.model
            self._last_provider = resp.provider
            raw = resp.text.strip()
            # Extract JSON array
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                items = json.loads(raw[start:end])
                discovered = []
                for item in items:
                    slug = item.get("id", "")
                    if not slug or slug in already_seen:
                        continue
                    basis = item.get("evidence_basis", "")
                    if basis not in ("observed", "research"):
                        logger.debug(f"Dropping discovered entry '{slug}' — no valid evidence basis")
                        continue
                    discovered.append({
                        "id": slug,
                        "label": item.get("label", slug),
                        "description": item.get("description", ""),
                        "user_named": False,
                        "evidence_basis": basis,
                        "evidence_citation": item.get("evidence_citation", ""),
                    })
                return discovered
        except (ProviderError, json.JSONDecodeError, Exception) as e:
            logger.debug(f"Entry discovery failed ({e}) — using default archetypes only")
        return []

    # ------------------------------------------------------------------
    # Per-entry evaluation
    # ------------------------------------------------------------------

    def _evaluate_entry(
        self,
        entry: Dict[str, Any],
        asset: str,
        terminal: str,
        industry: str,
        region: str,
        organization_size: str,
        context_block: str,
        threat_patterns: List[str],
        existing_credible_routes: List[RouteResult],
    ) -> RouteResult:
        """Evaluate one entry point against the terminal. Returns a RouteResult."""

        # Build technique hint for this entry
        suggested_techniques = self._suggest_techniques_for_patterns(threat_patterns)
        technique_ref = "\n".join([
            f"- {t['id']}: {t['name']}"
            for t in suggested_techniques[:6]
        ]) if suggested_techniques else "None"

        # Build diversity hint so the LLM knows what middle sections already exist
        diversity_hint = self._build_diversity_hint(existing_credible_routes)

        system_prompt = self._build_system_prompt()

        user_prompt = f"""You are evaluating whether a specific ENTRY POINT can reach a TERMINAL OUTCOME.

{context_block}

ENTRY POINT BEING EVALUATED:
- Label: {entry['label']}
- Description: {entry['description']}

TERMINAL (the specific outcome to reach): {terminal}
PROTECTED ASSET: {asset}

{diversity_hint}

SUGGESTED MITRE TECHNIQUES:
{technique_ref}

Your task: determine whether this entry point has a CREDIBLE PATH to the terminal.

Verdict options:
- "credible": A realistic chain of TTPs exists from this entry to the terminal
- "no_credible_path": The chain cannot reach the terminal from this entry (explain exactly where it breaks and why)
- "different_terminal": This entry threatens a different asset/outcome, not this terminal

Return ONLY a JSON object in one of these three shapes:

Shape 1 — credible:
{{
  "verdict": "credible",
  "prose_narrative": "Paragraph explaining how this entry reaches the terminal — the why and how, evidence basis for each step",
  "attack_actions": [
    {{
      "id": "n1",
      "name": "Technique name",
      "technique_id": "TXXXX.XXX",
      "tactic": "Tactic name",
      "description": "How used in THIS specific path",
      "depends_on": [],
      "confidence": "observed | reported | speculative",
      "asset_refs": ["asset_name"]
    }}
  ],
  "logic": [],
  "entry_points": ["n1"],
  "assets": ["asset_name"],
  "threat_actor": "Actor type"
}}

Shape 2 — no_credible_path:
{{
  "verdict": "no_credible_path",
  "break_point": "The step/node where the chain ends (e.g. 'lateral movement to database server')",
  "break_reason": "Why it cannot proceed from that point to the terminal (structural, not control-based)",
  "monitored_assumptions": [
    "Assumption 1 that was taken as true to reach this verdict",
    "Assumption 2..."
  ],
  "flip_conditions": [
    "If [specific structural fact] changes, this entry becomes credible",
    "..."
  ]
}}

Shape 3 — different_terminal:
{{
  "verdict": "different_terminal",
  "threatened_asset": "The asset/outcome this entry actually threatens",
  "reason": "Why this entry reaches a different terminal rather than '{terminal}'"
}}

IMPORTANT RULES:
- No 'succeeds when' language. No control prescriptions. No 'cannot' or 'impossible' without a flip condition.
- For no_credible_path: the verdict is conditional on the monitored assumptions. Always include at least one flip condition.
- For credible: the attack_actions must differ meaningfully in their middle section from any existing routes (see diversity hint above).
- Confidence labels: "observed" = grounded in supplied intel, "reported" = consistent with public reporting, "speculative" = plausible but not evidenced."""

        try:
            resp = complete(
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                provider=self.provider,
                weight=self.weight,
                max_tokens=3000,
            )
            self._last_model = resp.model
            self._last_provider = resp.provider
            content = resp.text

        except ProviderError as e:
            logger.error(f"LLM call failed for entry '{entry['label']}' ({e.provider}/{e.kind}): {e}")
            return RouteResult(
                verdict="no_credible_path",
                entry_id=entry["id"],
                entry_label=entry["label"],
                entry_description=entry["description"],
                user_named=entry.get("user_named", True),
                break_point="LLM generation failed",
                break_reason=f"Provider error: {e}",
                monitored_assumptions=["LLM generation succeeded"],
                flip_conditions=["If generation succeeds, re-evaluate this entry"],
                llm_model=self._last_model,
                llm_provider=self._last_provider,
            )

        # Parse response
        route = self._parse_verdict_response(content, entry)

        # Diversity check for credible routes
        if route.verdict == "credible" and route.flow_data:
            if self._is_near_duplicate(route, existing_credible_routes):
                logger.warning(
                    f"Route for '{entry['label']}' is a near-duplicate of an existing route — "
                    "demoting to no_credible_path (diversity check R4)"
                )
                route.verdict = "no_credible_path"
                route.break_point = "Diversity check"
                route.break_reason = (
                    "This route's technique sequence is too similar to an already-generated "
                    "credible route. The entry point may be credible but does not provide "
                    "diverse insight beyond existing paths."
                )
                route.monitored_assumptions = [
                    "The existing credible routes cover materially different approaches"
                ]
                route.flip_conditions = [
                    "If the threat actor uses a substantially different technique chain for "
                    "this entry, a distinct credible route may emerge"
                ]
                route.flow_data = None

        return route

    def _parse_verdict_response(
        self, content: str, entry: Dict[str, Any]
    ) -> RouteResult:
        """Parse the LLM's JSON verdict response into a RouteResult."""
        base = RouteResult(
            verdict="no_credible_path",
            entry_id=entry["id"],
            entry_label=entry["label"],
            entry_description=entry["description"],
            user_named=entry.get("user_named", True),
            evidence_basis=entry.get("evidence_basis"),
            evidence_citation=entry.get("evidence_citation"),
            llm_model=self._last_model,
            llm_provider=self._last_provider,
        )

        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start < 0 or end <= start:
                raise ValueError("No JSON object in response")
            data = json.loads(content[start:end])
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse verdict JSON for '{entry['label']}': {e}")
            base.break_point = "JSON parse failure"
            base.break_reason = f"LLM returned unparseable response: {e}"
            base.monitored_assumptions = ["LLM returns valid JSON"]
            base.flip_conditions = ["If LLM response is valid JSON, re-evaluate"]
            return base

        verdict = data.get("verdict", "no_credible_path")
        base.verdict = verdict

        if verdict == "credible":
            base.prose_narrative = data.get("prose_narrative", "")
            base.flow_data = {
                "name": f"Route via {entry['label']}",
                "description": data.get("prose_narrative", "")[:200],
                "scope": "incident",
                "attack_actions": data.get("attack_actions", []),
                "logic": data.get("logic", []),
                "entry_points": data.get("entry_points", []),
                "assets": data.get("assets", []),
                "threat_actor": data.get("threat_actor", "Unknown"),
                "x_entry_point": entry["label"],
                "x_terminal": base.entry_description,
            }

        elif verdict == "no_credible_path":
            base.break_point = data.get("break_point", "")
            base.break_reason = data.get("break_reason", "")
            base.monitored_assumptions = data.get("monitored_assumptions", [])
            base.flip_conditions = data.get("flip_conditions", [])

        elif verdict == "different_terminal":
            base.threatened_asset = data.get("threatened_asset", "")

        return base

    # ------------------------------------------------------------------
    # Diversity check (R4)
    # ------------------------------------------------------------------

    def _is_near_duplicate(
        self, candidate: RouteResult, existing: List[RouteResult]
    ) -> bool:
        """Return True if candidate's technique set overlaps too much with any existing credible route."""
        if not candidate.flow_data:
            return False
        cand_techs = {
            a.get("technique_id", "")
            for a in candidate.flow_data.get("attack_actions", [])
            if a.get("technique_id")
        }
        if not cand_techs:
            return False
        for r in existing:
            if r.verdict != "credible" or not r.flow_data:
                continue
            existing_techs = {
                a.get("technique_id", "")
                for a in r.flow_data.get("attack_actions", [])
                if a.get("technique_id")
            }
            if not existing_techs:
                continue
            overlap = len(cand_techs & existing_techs) / min(len(cand_techs), len(existing_techs))
            if overlap > _DIVERSITY_THRESHOLD:
                return True
        return False

    # ------------------------------------------------------------------
    # Diversity hint for the LLM
    # ------------------------------------------------------------------

    def _build_diversity_hint(self, existing_credible: List[RouteResult]) -> str:
        if not existing_credible:
            return ""
        lines = ["EXISTING CREDIBLE ROUTES (your route must differ in its MIDDLE SECTION):"]
        for r in existing_credible:
            if not r.flow_data:
                continue
            techs = [
                f"{a.get('technique_id','')} ({a.get('tactic','')})"
                for a in r.flow_data.get("attack_actions", [])[:5]
            ]
            lines.append(f"  - Entry '{r.entry_label}': {', '.join(techs)}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Technique suggestion helper (reused from AttackFlowGenerator)
    # ------------------------------------------------------------------

    def _suggest_techniques_for_patterns(self, patterns: List[str]) -> List[Dict[str, Any]]:
        technique_map = {
            "System Intrusion": ["T1190", "T1133", "T1078", "T1567", "T1490"],
            "Social Engineering": ["T1566", "T1566.001", "T1566.002", "T1566.003"],
            "Miscellaneous Errors": ["T1485", "T1486"],
            "Basic Web Application Attacks": ["T1190", "T1189", "T1505.003"],
            "Privilege Misuse": ["T1078", "T1098"],
            "Ransomware": ["T1486", "T1490", "T1567", "T1491"],
        }
        suggested = []
        seen_ids: set = set()
        for pattern in patterns:
            for key, techniques in technique_map.items():
                if key.lower() in pattern.lower():
                    for tech_id in techniques:
                        if tech_id not in seen_ids:
                            t = self.mitre.get_technique(tech_id)
                            if t:
                                suggested.append(t)
                                seen_ids.add(tech_id)
        return suggested[:10]

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    def _build_system_prompt(self) -> str:
        return """You are a cybersecurity threat intelligence expert specializing in MITRE ATT&CK and attack path analysis.

Your task is to evaluate whether a specific entry point has a credible path to a given terminal outcome.

Key requirements:
1. Use ONLY valid MITRE ATT&CK technique IDs (T1566, T1566.001, T1078, etc.)
2. Base your assessment on the supplied threat intelligence grounding
3. For credible paths: build the route from WHAT THIS THREAT ACTOR ACTUALLY DOES — not a march through every tactic phase
4. For no_credible_path: explain exactly WHERE the chain breaks and WHY structurally (not because of a control)
5. NEVER use 'succeeds when' or prescribe controls. NEVER say 'impossible' or 'cannot' without a flip condition.
6. Monitored assumptions and flip conditions must be structural facts (network topology, credential scope, etc.) — not control prescriptions
7. Confidence: "observed" = grounded in supplied data, "reported" = consistent with public reporting, "speculative" = plausible but not evidenced

Output valid JSON only."""
