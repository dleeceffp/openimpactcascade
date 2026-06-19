"""Output formatters for Attack Flows."""

import json
import logging
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime

from stix_serializer import convert as to_stix_bundle

logger = logging.getLogger("oic.attack_flow.formatter")


class AttackFlowFormatter:
    """Formats Attack Flow data for various output formats."""

    @staticmethod
    def _topo_order(actions: List[Dict], logic: List[Dict] = None) -> List[str]:
        """
        Topological sort over depends_on edges.

        Args:
            actions: List of action dicts with 'id' and 'depends_on'
            logic: Optional list of logic gates

        Returns:
            List of action IDs in valid execution order

        Raises:
            ValueError: If the dependency graph contains a cycle
        """
        import collections

        # Build dependency map
        deps = {a["id"]: set(a.get("depends_on", [])) for a in actions if a.get("id")}

        # Add logic gate edges (inputs -> output)
        for gate in (logic or []):
            output = gate.get("output")
            inputs = gate.get("inputs", [])
            if output and inputs:
                deps.setdefault(output, set()).update(inputs)

        # Kahn's algorithm
        order = []
        ready = [i for i, d in deps.items() if not d]
        seen = set()

        while ready:
            n = ready.pop(0)
            order.append(n)
            seen.add(n)

            # Find nodes that now have all dependencies satisfied
            for node_id, node_deps in deps.items():
                if node_id not in seen and node_deps <= seen and node_id not in ready:
                    ready.append(node_id)

        if len(order) != len(deps):
            raise ValueError("attack flow dependency graph contains a cycle")

        return order

    @staticmethod
    def to_json(flow_data: Dict[str, Any], indent: int = 2) -> str:
        """Format as a STIX 2.1 JSON string.

        If the input is already a STIX bundle, it is dumped directly. Otherwise
        the generator's native flow model is converted to a STIX 2.1 Attack
        Flow bundle before serialization.
        """
        if flow_data.get("type") == "bundle":
            return json.dumps(flow_data, indent=indent, ensure_ascii=False)
        return json.dumps(to_stix_bundle(flow_data), indent=indent, ensure_ascii=False)

    @staticmethod
    def to_summary_markdown(flow_data: Dict[str, Any]) -> str:
        """Format as a human-readable Markdown summary."""
        lines = []

        # Resolve the flow object and the original generator model
        if flow_data.get("type") == "bundle":
            flow_obj = None
            for obj in flow_data.get("objects", []):
                if obj.get("type") == "attack-flow":
                    flow_obj = obj
                    break
            original_flow = flow_data.get("x_original_flow", {})
        elif flow_data.get("type") == "attack-flow":
            flow_obj = flow_data
            original_flow = flow_data
        else:
            # Native generator flow model (no "type" yet)
            flow_obj = flow_data
            original_flow = flow_data

        if not flow_obj:
            return "# Error: No attack-flow object found"

        # Check for stub warning
        # x_oic_context lives on the bundle root (not on the SDO) so it stays
        # out of the schema-validated STIX payload.
        context = flow_obj.get("x_oic_context", {}) or flow_data.get("x_oic_context", {})
        is_stub = context.get("generation_status") == "fallback_stub"
        scope = flow_obj.get("scope", "incident")

        # Header with warning if stub
        if is_stub:
            lines.append("# ⚠️ FALLBACK STUB — generation failed, not grounded")
            lines.append("")
            lines.append(f"## {flow_obj.get('name', 'Untitled Attack Flow')}")
        else:
            lines.append(f"# {flow_obj.get('name', 'Untitled Attack Flow')}")

        lines.append("")

        # Context
        context = flow_obj.get("x_oic_context", {})
        if context:
            lines.append("## Context")
            lines.append(f"- **Industry:** {context.get('industry', 'Unknown')}")
            lines.append(f"- **Region:** {context.get('region', 'Unknown')}")
            lines.append(f"- **Organization Size:** {context.get('organization_size', 'Unknown')}")
            lines.append(f"- **Generated:** {context.get('generated_at', 'Unknown')}")
            lines.append("")

        # Description
        if flow_obj.get("description"):
            lines.append("## Description")
            desc = flow_obj["description"]
            if desc.startswith("[FALLBACK STUB"):
                lines.append(f"**⚠️ {desc}**")
            else:
                lines.append(desc)
            lines.append("")

        # Scope
        if is_stub:
            lines.append(f"**Scope:** {scope} (stub - not a real incident)")
        else:
            lines.append(f"**Scope:** {scope}")
        lines.append("")

        # Attack Actions with dependency graph
        actions = original_flow.get("attack_actions", [])
        logic = original_flow.get("logic", flow_data.get("logic", []))

        if actions:
            lines.append("## Attack Actions (MITRE ATT&CK Techniques)")
            lines.append("")

            # Try topological sort, fall back gracefully on cycle
            try:
                topo_order = AttackFlowFormatter._topo_order(actions, logic)
                has_cycle = False
            except ValueError as e:
                logger.warning(f"Cycle detected in attack flow: {e}")
                topo_order = [a.get("id") for a in actions if a.get("id")]
                has_cycle = True
                lines.append("⚠️ **Warning:** Dependency cycle detected in flow structure")
                lines.append("")

            # Build action lookup
            action_map = {a.get("id"): a for a in actions if a.get("id")}

            # Build successor map (which actions come after this one)
            successors: Dict[str, List[str]] = {a.get("id", f"a{i}"): [] for i, a in enumerate(actions)}
            for action in actions:
                action_id = action.get("id")
                for other in actions:
                    if action_id in other.get("depends_on", []):
                        successors[action_id].append(other.get("id"))

            # Header row with confidence column
            lines.append("| ID | Tactic | Technique | Description | Predecessors | Confidence |")
            lines.append("|----|--------|-----------|-------------|--------------|------------|")

            for node_id in topo_order:
                action = action_map.get(node_id, {})
                name = action.get("name", "Unknown")
                tactic = action.get("tactic_id", action.get("tactic", "Unknown"))
                tech_id = action.get("technique_id", "")
                tech_ref = f"{tech_id} - " if tech_id else ""
                desc = action.get("description", "")[:50]
                if len(action.get("description", "")) > 50:
                    desc += "..."

                # Get depends_on for display
                deps = action.get("depends_on", [])
                deps_str = ", ".join(deps) if deps else "(entry)"

                # Get confidence
                confidence = action.get("confidence", "unspecified")
                if isinstance(confidence, str):
                    conf_marker = {
                        "observed": "✓ observed",
                        "reported": "~ reported",
                        "speculative": "? speculative",
                        "unspecified": "- unspecified"
                    }.get(confidence, confidence)
                else:
                    # Get from x_oic_metadata if present
                    metadata = action.get("x_oic_metadata", {})
                    conf_marker = metadata.get("confidence", "unspecified")

                lines.append(f"| {node_id} | {tactic} | {tech_ref}{name} | {desc} | {deps_str} | {conf_marker} |")

            lines.append("")

            # Show graph structure notes
            if has_cycle:
                lines.append("⚠️ This flow contains a dependency cycle and may not represent a valid attack sequence.")
                lines.append("")

            # Identify branches and joins
            branches = [aid for aid, succs in successors.items() if len(succs) > 1]
            joins = [aid for aid in topo_order if len(action_map.get(aid, {}).get("depends_on", [])) > 1]

            if branches:
                lines.append(f"**Branch points:** {', '.join(branches)}")
            if joins:
                lines.append(f"**Join points:** {', '.join(joins)}")
            if branches or joins:
                lines.append("")

        # Logic Gates
        if logic:
            lines.append("## Logic Gates")
            lines.append("")
            for gate in logic:
                gate_type = gate.get("type", "AND")
                inputs = gate.get("inputs", [])
                output = gate.get("output", "unknown")
                lines.append(f"- **{gate_type}**: {', '.join(inputs)} → {output}")
            lines.append("")

        # Assets
        assets = original_flow.get("assets", [])
        if assets:
            lines.append("## Targeted Assets")
            for asset in assets:
                lines.append(f"- {asset}")
            lines.append("")

        # Threat Actor
        threat_actor = original_flow.get("threat_actor", flow_data.get("threat_actor", ""))
        if threat_actor:
            lines.append(f"**Threat Actor:** {threat_actor}")
            lines.append("")

        # Output reference
        lines.append("## STIX 2.1 Attack Flow")
        lines.append("The complete Attack Flow is available as a STIX 2.1 bundle in the `.json` output.")
        lines.append("Open `attack_flow_viewer.html` in the same directory to explore it.")
        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def save_to_file(flow_data: Dict[str, Any], filepath: Path, format: str = "json") -> Path:
        """Save the attack flow to a file."""
        filepath = Path(filepath)

        # Ensure directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)

        if format.lower() in ("stix", "json"):
            content = AttackFlowFormatter.to_json(flow_data)
            if filepath.suffix != ".json":
                filepath = filepath.with_suffix(".json")
        elif format.lower() in ("md", "markdown"):
            content = AttackFlowFormatter.to_summary_markdown(flow_data)
            if filepath.suffix != ".md":
                filepath = filepath.with_suffix(".md")
        else:
            raise ValueError(f"Unknown format: {format}")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Saved Attack Flow to {filepath}")
        return filepath

    @staticmethod
    def generate_filename(industry: str, region: str, org_size: str, suffix: str = ".json") -> str:
        """Generate a filename for the attack flow."""
        # Clean up inputs for filename
        safe_industry = industry.lower().replace(" ", "_").replace("/", "_")[:20]
        safe_region = region.lower().replace(" ", "_")[:15]
        safe_size = org_size.lower().replace(" ", "_")[:10]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"attack_flow_{safe_industry}_{safe_region}_{safe_size}_{timestamp}{suffix}"
