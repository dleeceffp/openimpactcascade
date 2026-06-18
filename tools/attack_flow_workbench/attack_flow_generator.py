"""Attack Flow generation logic using LLM and threat intelligence grounding."""

import os
import json
import logging
import uuid
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

        # Validate and format as proper MITRE Attack Flow
        attack_flow = self._format_as_attack_flow(
            flow_data=flow_data,
            industry=industry,
            region=region,
            organization_size=organization_size
        )

        return attack_flow

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
            "confidence": "observed | reported | speculative"
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
            "scope": "stub",
            "generation_status": "fallback_stub",
            "attack_actions": [
                {
                    "id": "n1",
                    "name": "Spearphishing Attachment",
                    "technique_id": "T1566.001",
                    "tactic": "Initial Access",
                    "description": "Malicious email attachment delivered to employee",
                    "depends_on": [],
                    "confidence": "speculative"
                },
                {
                    "id": "n2",
                    "name": "Malicious File",
                    "technique_id": "T1204.002",
                    "tactic": "Execution",
                    "description": "User executes malicious attachment",
                    "depends_on": ["n1"],
                    "confidence": "speculative"
                },
                {
                    "id": "n3",
                    "name": "Registry Run Keys",
                    "technique_id": "T1547.001",
                    "tactic": "Persistence",
                    "description": "Malware establishes persistence via registry",
                    "depends_on": ["n2"],
                    "confidence": "speculative"
                },
                {
                    "id": "n4",
                    "name": "Data Encrypted for Impact",
                    "technique_id": "T1486",
                    "tactic": "Impact",
                    "description": "Ransomware encrypts critical data",
                    "depends_on": ["n3"],
                    "confidence": "speculative"
                }
            ],
            "logic": [],
            "entry_points": ["n1"],
            "assets": ["Workstation", "File Server"],
            "threat_actor": "External - Financially Motivated"
        }

    def _format_as_attack_flow(
        self,
        flow_data: Dict[str, Any],
        industry: str,
        region: str,
        organization_size: str
    ) -> Dict[str, Any]:
        """Format the generated data as a proper MITRE Attack Flow."""

        # Generate STIX IDs
        bundle_id = f"bundle--{uuid.uuid4()}"
        flow_id = f"attack-flow--{uuid.uuid4()}"
        identity_id = f"identity--{uuid.uuid4()}"

        # Current timestamp for all objects
        created_timestamp = datetime.now().isoformat() + "Z"

        objects = []

        # Check if this is a fallback stub
        is_stub = flow_data.get("generation_status") == "fallback_stub"
        scope = flow_data.get("scope", "incident")

        # Create identity object for author (required for created_by_ref)
        identity_obj = {
            "type": "identity",
            "id": identity_id,
            "spec_version": "2.1",
            "name": "OIC Attack Flow Workbench",
            "identity_class": "organization",
            "contact_information": "oic@sandbox.local",
            "created": created_timestamp,
            "modified": created_timestamp
        }
        objects.append(identity_obj)

        # Create the attack-flow object
        attack_flow = {
            "type": "attack-flow",
            "id": flow_id,
            "spec_version": "2.1",
            "created": created_timestamp,
            "modified": created_timestamp,
            "created_by_ref": identity_id,
            "name": flow_data.get("name", f"Attack Flow - {industry}"),
            "description": flow_data.get("description", ""),
            "scope": scope,
            "start_refs": [],
            "extensions": {
                "extension-definition--fb9c968a-745b-4ade-9b25-c324172197f4": {
                    "extension_type": "new-sdo"
                }
            }
        }

        # Add OIC metadata
        attack_flow["x_oic_context"] = {
            "industry": industry,
            "region": region,
            "organization_size": organization_size,
            "generated_at": created_timestamp,
            "generator": "OIC Attack Flow Workbench v0.1.0",
            "generation_status": flow_data.get("generation_status", "generated")
        }

        # Add warning for stub flows
        if is_stub:
            attack_flow["description"] = "[FALLBACK STUB - generation failed, not grounded] " + attack_flow["description"]

        objects.append(attack_flow)

        # Create attack-action objects
        actions = flow_data.get("attack_actions", [])

        # Map internal IDs to STIX IDs
        id_map: Dict[str, str] = {}
        for action in actions:
            internal_id = action.get("id", f"action-{len(id_map)}")
            if internal_id not in id_map:
                id_map[internal_id] = f"attack-action--{uuid.uuid4()}"

        # Build reverse map for effect_refs (which actions come after this one)
        successors: Dict[str, List[str]] = {action["id"]: [] for action in actions if action.get("id")}

        for action in actions:
            action_id = action.get("id")
            depends_on = action.get("depends_on", [])
            for dep_id in depends_on:
                if dep_id in successors:
                    successors[dep_id].append(action_id)

        # Create attack-action objects
        for action in actions:
            internal_id = action.get("id", f"action-{len(objects)}")
            action_id = id_map.get(internal_id, f"attack-action--{uuid.uuid4()}()")

            tactic = action.get("tactic", "")
            tactic_shortname = self._tactic_name_to_shortname(tactic)

            technique_id = action.get("technique_id", "")
            technique = self.mitre.get_technique(technique_id) if technique_id else None

            attack_action = {
                "type": "attack-action",
                "id": action_id,
                "spec_version": "2.1",
                "created": created_timestamp,
                "modified": created_timestamp,
                "created_by_ref": identity_id,
                "name": action.get("name", "Unknown Action"),
                "description": action.get("description", ""),
                "tactic_id": tactic_shortname,
                "technique_id": technique_id if technique_id else None,
                "technique_ref": technique["stix_id"] if technique else None,
                "extensions": {
                    "extension-definition--fb9c968a-745b-4ade-9b25-c324172197f4": {
                        "extension_type": "new-sdo"
                    }
                },
                "x_oic_metadata": {
                    "confidence": action.get("confidence", "unspecified"),
                    "internal_id": internal_id
                }
            }

            # Add effect_refs based on successors (which actions depend on this one)
            if internal_id in successors and successors[internal_id]:
                effect_refs = [id_map.get(sid) for sid in successors[internal_id] if sid in id_map]
                if effect_refs:
                    attack_action["effect_refs"] = effect_refs

            objects.append(attack_action)

        # Update start_refs from entry_points
        entry_points = flow_data.get("entry_points", [])
        start_refs = [id_map.get(ep) for ep in entry_points if ep in id_map]
        if start_refs:
            attack_flow["start_refs"] = start_refs
        elif id_map:
            # Fallback: find nodes with no dependencies
            entry_ids = [a["id"] for a in actions if not a.get("depends_on")]
            if entry_ids:
                attack_flow["start_refs"] = [id_map.get(eid) for eid in entry_ids if eid in id_map]

        # Create logic gates (AND/OR operators) if present
        logic_gates = flow_data.get("logic", [])
        for gate in logic_gates:
            gate_id = f"attack-operator--{uuid.uuid4()}"
            gate_type = gate.get("type", "AND")
            output_id = gate.get("output")

            operator_obj = {
                "type": "attack-operator",
                "id": gate_id,
                "spec_version": "2.1",
                "created": created_timestamp,
                "modified": created_timestamp,
                "created_by_ref": identity_id,
                "operator": gate_type,
                "extensions": {
                    "extension-definition--fb9c968a-745b-4ade-9b25-c324172197f4": {
                        "extension_type": "new-sdo"
                    }
                }
            }
            objects.append(operator_obj)

            # Connect inputs to operator
            inputs = gate.get("inputs", [])
            for inp_id in inputs:
                if inp_id in id_map:
                    # Find the action and add effect_ref to operator
                    # This is a simplified approach
                    pass

        # Create attack-asset objects
        assets = flow_data.get("assets", [])
        for asset_name in assets:
            asset_id = f"attack-asset--{uuid.uuid4()}"
            asset_obj = {
                "type": "attack-asset",
                "id": asset_id,
                "spec_version": "2.1",
                "created": created_timestamp,
                "modified": created_timestamp,
                "created_by_ref": identity_id,
                "name": asset_name,
                "extensions": {
                    "extension-definition--fb9c968a-745b-4ade-9b25-c324172197f4": {
                        "extension_type": "new-sdo"
                    }
                }
            }
            objects.append(asset_obj)

        # Build final bundle with original data preserved for formatting
        attack_flow_bundle = {
            "type": "bundle",
            "id": bundle_id,
            "objects": objects,
            "x_original_flow": flow_data  # Preserve original for formatter
        }

        return attack_flow_bundle

    def _tactic_name_to_shortname(self, tactic_name: str) -> str:
        """Convert tactic name to MITRE shortname."""
        mapping = {
            "Reconnaissance": "reconnaissance",
            "Resource Development": "resource-development",
            "Initial Access": "initial-access",
            "Execution": "execution",
            "Persistence": "persistence",
            "Privilege Escalation": "privilege-escalation",
            "Defense Evasion": "defense-evasion",
            "Credential Access": "credential-access",
            "Discovery": "discovery",
            "Lateral Movement": "lateral-movement",
            "Collection": "collection",
            "Command and Control": "command-and-control",
            "Exfiltration": "exfiltration",
            "Impact": "impact",
        }
        return mapping.get(tactic_name, tactic_name.lower().replace(" ", "-"))
