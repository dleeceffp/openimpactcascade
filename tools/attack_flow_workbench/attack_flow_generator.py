"""Attack Flow generation logic using LLM and threat intelligence grounding."""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    import anthropic
except ImportError:
    anthropic = None

from config import OIC_MODEL, OIC_MODEL_FAST, build_system
from mitre_loader import get_mitre_lookup
try:
    from corpus_grounding import get_grounding
except ImportError:
    get_grounding = None
try:
    from web_search import get_web_search
except ImportError:
    get_web_search = None

logger = logging.getLogger("oic.attack_flow.generator")


class AttackFlowGenerator:
    """Generates MITRE Attack Flows based on industry, region, and org size."""

    def __init__(self, api_key: Optional[str] = None):
        if anthropic is None:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable must be set")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.mitre = get_mitre_lookup()
        self.grounding = get_grounding() if get_grounding else None
        self.web_search = get_web_search() if get_web_search else None

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

        web_results = []
        if include_web_search and self.web_search and self.web_search.enabled:
            web_results = self.web_search.search_threats(industry, region)

        web_text = self.web_search.format_results_for_prompt(web_results) if (self.web_search and web_results) else ""

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

        try:
            response = self.client.messages.create(
                model=OIC_MODEL,
                max_tokens=4000,
                system=build_system(system_prompt),
                messages=[{"role": "user", "content": user_prompt}]
            )

            # Extract JSON from response
            content = response.content[0].text if response.content else ""

            # Try to find JSON in the response
            json_start = content.find("{")
            json_end = content.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                flow_data = json.loads(json_str)
                return flow_data
            else:
                raise ValueError("No valid JSON found in LLM response")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response content: {content}")
            # Return a fallback structure
            return self._generate_fallback_flow(industry, threat_patterns)
        except Exception as e:
            logger.error(f"Error generating attack flow with LLM: {e}")
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

