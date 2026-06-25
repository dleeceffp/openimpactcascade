"""Attack Flow generation logic using oic_llm and oic_search for grounding.

Provider and search backend are selected at construction time (or resolved
from environment/config defaults).  No vendor-specific code lives here.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
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

logger = logging.getLogger("oic.attack_flow.generator")


class AttackFlowGenerator:
    """Generates MITRE Attack Flows based on industry, region, and org size."""

    def __init__(
        self,
        provider: Optional[str] = None,
        weight: Optional[str] = None,
        search_provider: Optional[str] = None,
    ):
        # None → oic_llm resolves from OIC_LLM_PROVIDER / OIC_LLM_WEIGHT env vars
        self.provider = provider
        self.weight = weight
        # None → oic_search resolves from OIC_SEARCH_PROVIDER env var (default: tavily)
        self.search_provider = search_provider

        # Provenance fields populated by _generate_with_llm
        self._last_model: str = "unknown"
        self._last_provider: str = "unknown"
        self._last_usage: dict = {}

        self.mitre = get_mitre_lookup()
        self.grounding = get_grounding() if get_grounding else None

    def generate_flow(
        self,
        industry: str,
        region: str,
        organization_size: str,
        threat_scenario: Optional[str] = None,
        include_web_search: bool = True
    ) -> Dict[str, Any]:
        """Generate a complete Attack Flow for the given context."""

        # Gather threat intelligence
        logger.info(f"Generating Attack Flow for {industry} in {region} ({organization_size})")

        if self.grounding:
            corpus_grounding = self.grounding.get_grounding_for_industry(industry)
            corpus_text = self.grounding.format_grounding_for_prompt(corpus_grounding)
            threat_patterns = self.grounding.get_threat_patterns(industry)
        else:
            corpus_text = "No corpus grounding available."
            threat_patterns = []

        web_text = ""
        search_provider_used = "none"
        search_performed = False
        if include_web_search:
            try:
                q = f"{industry} {region} cyber attack breach ransomware"
                sr: SearchResponse = search(
                    q,
                    profile="incident",
                    num=5,
                    provider=self.search_provider,  # None → oic_search env default
                    time_range="year",              # Tavily recency filter; Brave ignores it
                )
                if sr.results:
                    web_text = self._format_search_results(sr)
                    search_provider_used = sr.provider
                    search_performed = True
            except SearchError as e:
                logger.warning(f"web search unavailable ({e.kind}): {e}  — continuing without grounding")

        # Get relevant MITRE techniques based on threat patterns
        suggested_techniques = self._suggest_techniques_for_patterns(threat_patterns)

        # Generate the Attack Flow using LLM
        flow_data = self._generate_with_llm(
            industry=industry,
            region=region,
            organization_size=organization_size,
            threat_scenario=threat_scenario,
            corpus_grounding=corpus_text,
            web_results=web_text,
            suggested_techniques=suggested_techniques,
            threat_patterns=threat_patterns
        )

        # Attach provenance/context so formatters can render it without the .afb wrapper
        flow_data["x_oic_context"] = {
            "industry": industry,
            "region": region,
            "organization_size": organization_size,
            "generated_at": datetime.now().isoformat() + "Z",
            "generator": "OIC Attack Flow Workbench v0.1.0",
            "generation_status": flow_data.get("generation_status", "generated"),
            "llm_provider": self._last_provider,
            "llm_model": self._last_model,
            "search_provider": search_provider_used,
            "search_performed": search_performed,
        }

        return flow_data

    def _suggest_techniques_for_patterns(self, patterns: List[str]) -> List[Dict[str, Any]]:
        """Suggest MITRE techniques based on threat patterns."""
        technique_map = {
            "System Intrusion": ["T1190", "T1133", "T1078", "T1567", "T1490"],
            "Social Engineering": ["T1566", "T1566.001", "T1566.002", "T1566.003"],
            "Miscellaneous Errors": ["T1485", "T1486"],
            "Basic Web Application Attacks": ["T1190", "T1189", "T1505.003"],
            "Privilege Misuse": ["T1078", "T1098"],
            "Ransomware": ["T1486", "T1490", "T1567", "T1491"],
        }

        suggested = []
        seen_ids = set()

        for pattern in patterns:
            for key, techniques in technique_map.items():
                if key.lower() in pattern.lower():
                    for tech_id in techniques:
                        if tech_id not in seen_ids:
                            technique = self.mitre.get_technique(tech_id)
                            if technique:
                                suggested.append(technique)
                                seen_ids.add(tech_id)

        return suggested[:10]  # Limit suggestions

    def _generate_with_llm(
        self,
        industry: str,
        region: str,
        organization_size: str,
        threat_scenario: Optional[str],
        corpus_grounding: str,
        web_results: str,
        suggested_techniques: List[Dict],
        threat_patterns: List[str]
    ) -> Dict[str, Any]:
        """Use LLM to generate the Attack Flow structure."""

        system_prompt = self._build_system_prompt()

        # Build technique reference
        technique_ref = "\n".join([
            f"- {t['id']}: {t['name']}" +
            (f" ({self.mitre.get_tactic_for_technique(t['id'])['name']})" if self.mitre.get_tactic_for_technique(t['id']) else "")
            for t in suggested_techniques[:8]
        ]) if suggested_techniques else "No specific technique suggestions available."

        user_prompt = f"""Generate a MITRE Attack Flow for the following context:

ORGANIZATION CONTEXT:
- Industry: {industry}
- Region: {region}
- Organization Size: {organization_size}
- Threat Scenario: {threat_scenario or "Not specified - select the most relevant based on threat intelligence"}

{corpus_grounding}

{web_results}

SUGGESTED MITRE TECHNIQUES (based on {', '.join(threat_patterns) if threat_patterns else 'industry patterns'}):
{technique_ref}

Generate a realistic, industry-specific attack flow that:
1. Uses valid MITRE ATT&CK technique IDs (e.g., T1566.001 for Spearphishing Attachment)
2. Reconstructs how THIS SPECIFIC actor reaches its objective against this target — branching, skipping, or repeating tactics as the real pattern requires, rather than marching through every ATT&CK phase. A flow with 4 well-evidenced steps is better than 12 padded ones.
3. Includes 4-12 attack actions (techniques) based on the most relevant threats
4. Considers the organization size (SME vs Enterprise may have different attack patterns)

Return ONLY a JSON object with this structure:
{{
    "name": "Attack flow name",
    "description": "Description of the attack scenario",
    "scope": "incident",
    "attack_actions": [
        {{
            "id": "n1",
            "name": "Technique name",
            "technique_id": "TXXXX.XXX",
            "tactic": "Tactic name (e.g., Initial Access)",
            "description": "How this technique is used in the attack",
            "depends_on": [],
            "confidence": "observed | reported | speculative",
            "asset_refs": ["asset_name"]
        }}
    ],
    "logic": [
        {{"type": "AND", "inputs": ["n2", "n3"], "output": "n4"}}
    ],
    "entry_points": ["n1"],
    "assets": ["asset_name"],
    "threat_actor": "Threat actor type"
}}

Schema guidance:
- "depends_on" lists the id(s) of node(s) that must occur before this node. It REPLACES "order".
  * Two nodes sharing one predecessor = a fork (the attacker had two options/paths from there).
  * One node listing several predecessors = a join (it needed all of them).
  * Entry nodes have "depends_on": [] and must appear in "entry_points".
- "asset_refs" lists the names of the targeted assets this action directly compromises
  (from the flow's "assets" list). Leave it empty only if the action truly does not target
  any named asset.
- Use "logic" ONLY when a node genuinely requires a combination of predecessors:
  AND = all inputs needed; OR = any one input suffices. Omit "logic" (use []) for simple chains.
- Model a repeated tactic as DISTINCT nodes (e.g. "Discovery", later "Discovery (round 2)"),
  never as a back-edge. The dependency graph must be acyclic.
- Do not emit an "order" field.
- Set "confidence" for each node: "observed" (grounded in supplied data), "reported" (consistent with public intel), or "speculative" (plausible but not evidenced)."""

        # TODO: restore prompt caching via oic_llm cache_system flag once
        # AnthropicProvider supports it (config.build_system() content-block
        # format is incompatible with oic_llm.complete(system: str)).
        try:
            resp = complete(
                system=system_prompt,   # plain string — no Anthropic-native content blocks
                messages=[{"role": "user", "content": user_prompt}],
                provider=self.provider,  # None → oic_llm env/config default
                weight=self.weight,
                max_tokens=4000,
            )
            content = resp.text
            self._last_model = resp.model
            self._last_provider = resp.provider
            self._last_usage = resp.usage or {}

        except ProviderError as e:
            logger.error(f"LLM generation failed ({e.provider}/{e.kind}): {e}")
            return self._generate_fallback_flow(industry, threat_patterns)

        # Extract JSON from response — provider-agnostic, works for all backends
        try:
            json_start = content.find("{")
            json_end = content.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                return json.loads(json_str)
            else:
                raise ValueError("No valid JSON found in LLM response")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response content: {content}")
            return self._generate_fallback_flow(industry, threat_patterns)
        except ValueError as e:
            logger.error(f"LLM response extraction failed: {e}")
            return self._generate_fallback_flow(industry, threat_patterns)

    def _build_system_prompt(self) -> str:
        """Build the system prompt for attack flow generation."""
        return """You are a cybersecurity threat intelligence expert specializing in MITRE ATT&CK.

Your task is to generate realistic, industry-specific attack flows following the MITRE Attack Flow specification.

Key requirements:
1. Use ONLY valid MITRE ATT&CK technique IDs (T1566, T1566.001, T1078, etc.)
2. Ensure techniques are appropriate for the industry and region
3. Treat the 14 ATT&CK tactics as a LABELLING VOCABULARY, not a sequence to complete.
   Real intrusions skip tactics, repeat them, and run steps in parallel: a smash-and-grab
   may go straight from initial access to impact; an attacker holding valid credentials may
   never escalate privilege; discovery and lateral movement often interleave and repeat.
   Build the flow from WHAT THIS THREAT ACTOR ACTUALLY DOES to reach its objective — based
   on the supplied threat intelligence and forensic patterns — then label each node with
   whichever tactic fits. Include only the steps this actor needs, in the structure the
   evidence supports. Do NOT add a node merely to "complete" a tactic chain.
4. Consider organization size (SMEs have different attack patterns than enterprises)
5. Base the flow on real threat intelligence patterns
6. Anchor every node in observed behaviour. Prefer techniques attested in the supplied DBIR
   patterns, web intelligence, or known actor MO for this industry/region. Tag each node:
     - "observed"    : directly supported by the supplied grounding
     - "reported"    : consistent with public reporting on this actor/pattern
     - "speculative" : plausible but not evidenced — use sparingly, never as padding
   An unevidenced node added only for completeness is a defect, not a feature.

You have access to:
- Verizon DBIR threat patterns by industry
- Recent threat intelligence from web search
- MITRE ATT&CK technique database

Output must be valid JSON that can be converted to a MITRE Attack Flow document."""

    def _format_search_results(self, sr: SearchResponse) -> str:
        """Format oic_search results into a prompt-injectable context block.

        Mirrors the shape of the legacy web_search.format_results_for_prompt()
        so the LLM sees the same structure, but now includes source domain and
        published date so the model can weight authority and recency.
        """
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

    def _generate_fallback_flow(self, industry: str, patterns: List[str]) -> Dict[str, Any]:
        """Generate a basic fallback flow if LLM generation fails."""
        return {
            "name": f"Common Attack Pattern - {industry}",
            "description": f"A representative attack pattern targeting {industry} organizations",
            "scope": "other",
            "generation_status": "fallback_stub",
            "attack_actions": [
                {
                    "id": "n1",
                    "name": "Spearphishing Attachment",
                    "technique_id": "T1566.001",
                    "tactic": "Initial Access",
                    "description": "Malicious email attachment delivered to employee",
                    "depends_on": [],
                    "confidence": "speculative",
                    "asset_refs": ["Workstation"]
                },
                {
                    "id": "n2",
                    "name": "Malicious File",
                    "technique_id": "T1204.002",
                    "tactic": "Execution",
                    "description": "User executes malicious attachment",
                    "depends_on": ["n1"],
                    "confidence": "speculative",
                    "asset_refs": ["Workstation"]
                },
                {
                    "id": "n3",
                    "name": "Registry Run Keys",
                    "technique_id": "T1547.001",
                    "tactic": "Persistence",
                    "description": "Malware establishes persistence via registry",
                    "depends_on": ["n2"],
                    "confidence": "speculative",
                    "asset_refs": ["Workstation"]
                },
                {
                    "id": "n4",
                    "name": "Data Encrypted for Impact",
                    "technique_id": "T1486",
                    "tactic": "Impact",
                    "description": "Ransomware encrypts critical data",
                    "depends_on": ["n3"],
                    "confidence": "speculative",
                    "asset_refs": ["File Server", "Workstation"]
                }
            ],
            "logic": [],
            "entry_points": ["n1"],
            "assets": ["Workstation", "File Server"],
            "threat_actor": "External - Financially Motivated"
        }

