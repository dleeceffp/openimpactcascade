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
        """Format the generated data as a proper MITRE Attack Flow (.afb format).

        The .afb format is the native Attack Flow Builder canvas state. Every node
        needs 12 anchor points (every 30 degrees). Edges are represented as:
          horizontal_anchor (attached to a node's anchor UUID)
            -> generic_latch (connection point, listed in h_anchor.latches)
              -> dynamic_line.source/target (both latches)
                -> dynamic_line.handles -> generic_handle (midpoint for routing)
        """

        # Check if this is a fallback stub
        is_stub = flow_data.get("generation_status") == "fallback_stub"
        scope = flow_data.get("scope", "incident")

        # Current timestamp
        created_timestamp = datetime.now().isoformat() + "Z"

        # Build author property array
        author_properties = [
            ["name", "OIC Attack Flow Workbench"],
            ["identity_class", None],
            ["contact_information", "oic@sandbox.local"]
        ]

        # Build flow properties
        description = flow_data.get("description", "")
        if is_stub:
            description = "[FALLBACK STUB - generation failed, not grounded] " + description

        flow_properties = [
            ["name", flow_data.get("name", f"Attack Flow - {industry}")],
            ["description", description],
            ["author", author_properties],
            ["scope", scope],
            ["external_references", []],
            ["created", created_timestamp]
        ]

        # Tactic name -> TA#### ID mapping
        tactic_id_map = {
            "Reconnaissance": "TA0043",
            "Resource Development": "TA0042",
            "Initial Access": "TA0001",
            "Execution": "TA0002",
            "Persistence": "TA0003",
            "Privilege Escalation": "TA0004",
            "Defense Evasion": "TA0005",
            "Credential Access": "TA0006",
            "Discovery": "TA0007",
            "Lateral Movement": "TA0008",
            "Collection": "TA0009",
            "Command and Control": "TA0011",
            "Exfiltration": "TA0010",
            "Impact": "TA0040",
        }

        # Tactic name -> STIX tactic ref mapping
        tactic_ref_map = {
            "TA0043": "x-mitre-tactic--daa4cbb1-b4f4-4723-a824-7f1efd6e0592",
            "TA0042": "x-mitre-tactic--d679bca2-e57d-4935-8650-8031c87a4400",
            "TA0001": "x-mitre-tactic--ffd5bcee-6e16-4dd2-8eca-7b3beedf33ca",
            "TA0002": "x-mitre-tactic--4ca45d45-df4d-4613-8980-bac22d278fa5",
            "TA0003": "x-mitre-tactic--5bc1d813-693e-4823-9961-abf9af4b0e92",
            "TA0004": "x-mitre-tactic--1f3e5d8b-f7bf-4078-a40f-68f3506fb0e9",
            "TA0005": "x-mitre-tactic--78b23412-0651-46d7-a540-170a1ce8bd5a",
            "TA0006": "x-mitre-tactic--2558fd61-8c75-4730-900d-122e8cdaea9e",
            "TA0007": "x-mitre-tactic--0b20d6d2-e6cd-4c36-b984-eed9f15f4bff",
            "TA0008": "x-mitre-tactic--7141578b-e50b-4dcc-bfa4-08a8dd689e9e",
            "TA0009": "x-mitre-tactic--d108ce10-2953-4444-b7c9-e1fcbe35a5f1",
            "TA0011": "x-mitre-tactic--f72804c5-f15a-449e-a5da-2eecd181f813",
            "TA0010": "x-mitre-tactic--9a4e74ab-5008-408c-84bf-a10dfbc53462",
            "TA0040": "x-mitre-tactic--5569339b-94c2-49ee-afb3-2222936582c8",
        }

        # All canvas objects collected here
        all_objects = []

        # ── helper: build the 12 anchor-point dict for a node ──────────────
        # Each anchor slot holds a horizontal_anchor instance UUID.
        # We store the anchor objects and return the slot->uuid map.
        def _make_node_anchors() -> Dict[str, str]:
            """Return {degree_str: h_anchor_instance_uuid} and emit h_anchor objects."""
            slot_map = {}
            for deg in range(0, 360, 30):
                h_anchor_id = str(uuid.uuid4())
                slot_map[str(deg)] = h_anchor_id
                all_objects.append({
                    "id": "horizontal_anchor",
                    "instance": h_anchor_id,
                    "latches": []
                })
            return slot_map

        # ── helper: create a directed edge between two node anchor slots ────
        def _make_edge(src_anchor_id: str, tgt_anchor_id: str) -> None:
            """Emit generic_latch × 2, generic_handle × 1, dynamic_line × 1."""
            src_latch_id = str(uuid.uuid4())
            tgt_latch_id = str(uuid.uuid4())
            handle_id = str(uuid.uuid4())
            line_id = str(uuid.uuid4())

            # Attach latches to their h_anchor objects
            for obj in all_objects:
                if obj.get("id") == "horizontal_anchor":
                    if obj["instance"] == src_anchor_id:
                        obj["latches"].append(src_latch_id)
                    elif obj["instance"] == tgt_anchor_id:
                        obj["latches"].append(tgt_latch_id)

            all_objects.append({"id": "generic_latch", "instance": src_latch_id})
            all_objects.append({"id": "generic_latch", "instance": tgt_latch_id})
            all_objects.append({"id": "generic_handle", "instance": handle_id})
            all_objects.append({
                "id": "dynamic_line",
                "instance": line_id,
                "source": src_latch_id,
                "target": tgt_latch_id,
                "handles": [handle_id]
            })
            return line_id

        # ── Generate instance UUIDs for all actions ──────────────────────────
        actions = flow_data.get("attack_actions", [])
        assets = flow_data.get("assets", [])

        instance_map: Dict[str, str] = {}
        for action in actions:
            internal_id = action.get("id", f"action-{len(instance_map)}")
            if internal_id not in instance_map:
                instance_map[internal_id] = str(uuid.uuid4())

        # ── Build successor graph from depends_on ────────────────────────────
        # successors[internal_id] = [list of internal_ids that depend on it]
        successors: Dict[str, List[str]] = {a.get("id", ""): [] for a in actions}
        for action in actions:
            for dep in action.get("depends_on", []):
                if dep in successors:
                    successors[dep].append(action.get("id", ""))

        # ── Create action objects ─────────────────────────────────────────────
        # anchor slot 90° = output (bottom), slot 270° = input (top) by convention
        OUTPUT_SLOT = "90"
        INPUT_SLOT  = "270"

        action_node_map: Dict[str, Dict] = {}  # internal_id -> {instance, anchor_slots}

        action_objects = []
        for idx, action in enumerate(actions):
            internal_id = action.get("id", f"action-{idx}")
            instance_id = instance_map.get(internal_id, str(uuid.uuid4()))

            tactic_name = action.get("tactic", "")
            tactic_ta_id = tactic_id_map.get(tactic_name, tactic_name)
            tactic_ref = tactic_ref_map.get(tactic_ta_id, None)

            technique_id = action.get("technique_id", "")
            technique = self.mitre.get_technique(technique_id) if technique_id else None

            anchor_slots = _make_node_anchors()

            action_props = [
                ["name", action.get("name", "Unknown Action")],
                ["tactic_id", tactic_ta_id],
                ["tactic_ref", tactic_ref],
                ["technique_id", technique_id],
                ["technique_ref", technique["stix_id"] if technique else None],
                ["description", action.get("description", "")],
                ["confidence", action.get("confidence", None)],
                ["execution_start", None],
                ["execution_end", None],
                ["ttp", [
                    ["tactic", tactic_ta_id],
                    ["technique", technique_id]
                ]]
            ]

            action_obj = {
                "id": "action",
                "instance": instance_id,
                "properties": action_props,
                "anchors": anchor_slots
            }
            all_objects.append(action_obj)
            action_objects.append(action_obj)
            action_node_map[internal_id] = {"instance": instance_id, "anchors": anchor_slots}

        # ── Create asset objects ──────────────────────────────────────────────
        asset_objects = []
        for asset_name in assets:
            asset_instance = str(uuid.uuid4())
            anchor_slots = _make_node_anchors()
            asset_obj = {
                "id": "asset",
                "instance": asset_instance,
                "properties": [["name", asset_name], ["description", None]],
                "anchors": anchor_slots
            }
            all_objects.append(asset_obj)
            asset_objects.append(asset_obj)

        # ── Draw edges between actions ────────────────────────────────────────
        edge_line_ids = []
        for src_id, tgt_ids in successors.items():
            src_node = action_node_map.get(src_id)
            if not src_node:
                continue
            src_anchor_uuid = src_node["anchors"][OUTPUT_SLOT]
            for tgt_id in tgt_ids:
                tgt_node = action_node_map.get(tgt_id)
                if not tgt_node:
                    continue
                tgt_anchor_uuid = tgt_node["anchors"][INPUT_SLOT]
                line_id = _make_edge(src_anchor_uuid, tgt_anchor_uuid)
                edge_line_ids.append(line_id)

        # ── Collect all dynamic_line instance IDs ────────────────────────────
        line_instances = [o["instance"] for o in all_objects if o.get("id") == "dynamic_line"]

        # ── Build the flow object ─────────────────────────────────────────────
        flow_anchor_slots = _make_node_anchors()
        node_instances = [obj["instance"] for obj in action_objects + asset_objects]
        all_flow_objects = node_instances + line_instances

        flow_obj = {
            "id": "flow",
            "instance": str(uuid.uuid4()),
            "properties": flow_properties,
            "objects": all_flow_objects,
            "anchors": flow_anchor_slots
        }

        # Insert flow at the front
        all_objects.insert(0, flow_obj)

        # Build final .afb
        afb_flow = {
            "schema": "attack_flow_v2",
            "theme": "dark_theme",
            "objects": all_objects
        }

        # Store metadata for formatter reference
        afb_flow["x_oic_context"] = {
            "industry": industry,
            "region": region,
            "organization_size": organization_size,
            "generated_at": created_timestamp,
            "generator": "OIC Attack Flow Workbench v0.1.0",
            "generation_status": flow_data.get("generation_status", "generated"),
            "original_flow": flow_data
        }

        return afb_flow

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
