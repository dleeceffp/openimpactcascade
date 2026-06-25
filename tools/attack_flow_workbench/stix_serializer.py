"""Convert the generator's in-memory Attack Flow into a STIX 2.1 bundle.

This module is the canonical serializer for the workbench. It does NOT read
`.afb` files; it takes the generator's native JSON-like flow object (actions,
assets, depends_on, etc.) and emits a STIX 2.1 Attack Flow bundle.

Reference shape: `afb_to_stix.py` (used as the spec). The main difference is
that this serializer is driven by the generator's in-memory model, not by an
`.afb` file.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from mitre_loader import get_mitre_lookup
except ImportError:  # pragma: no cover - supports running file standalone
    get_mitre_lookup = None

logger = logging.getLogger("oic.attack_flow.stix_serializer")

# Canonical MITRE Attack Flow extension definition id.
AF_EXT = "extension-definition--fb9c968a-745b-4ade-9b25-c324172197f4"
EXT_BLOCK = {AF_EXT: {"extension_type": "new-sdo"}}

PRODUCER_NAME = "OIC Attack Flow Workbench"

# Attack Flow confidence vocabulary -> integer 0-100.
CONF_INT = {
    "certain": 100,
    "very-probable": 90,
    "probable": 75,
    "even-odds": 50,
    "doubtful": 30,
    "very-doubtful": 10,
    "speculative": 0,
    # generator vocabulary -> scale
    "observed": 100,
    "confirmed": 100,
    "reported": 75,
    "speculation": 0,
}

# Tactic name -> MITRE ATT&CK tactic id.
TACTIC_NAME_TO_ID = {
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


def _now() -> str:
    """Return the current UTC timestamp in STIX format."""
    ts = datetime.now(timezone.utc)
    return f"{ts.strftime('%Y-%m-%dT%H:%M:%S.')}{ts.microsecond // 1000:03d}Z"


def _sid(stix_type: str) -> str:
    """Generate a STIX id for the given type."""
    return f"{stix_type}--{uuid.uuid4()}"


def _map_confidence(value: Any) -> Optional[int]:
    """Map a generator confidence value to a STIX integer 0-100, if possible."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).lower().strip()
    if s in CONF_INT:
        return CONF_INT[s]
    # Try to interpret a numeric string.
    try:
        return int(float(s))
    except ValueError:
        return None


def _omit_nulls(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Drop keys whose value is None. STIX schema rejects nulls."""
    return {k: v for k, v in obj.items() if v is not None}


def _resolve_tactic(tactic_value: Any) -> str:
    """Return a TA#### id from whatever the generator emitted."""
    if not tactic_value:
        return ""
    tv = str(tactic_value).strip()
    if tv.upper().startswith("TA"):
        return tv.upper()
    return TACTIC_NAME_TO_ID.get(tv, tv)


def _lookup_technique(technique_id: str) -> Optional[Dict[str, Any]]:
    """Return MITRE technique data if the loader is available."""
    if not get_mitre_lookup or not technique_id:
        return None
    try:
        return get_mitre_lookup().get_technique(technique_id)
    except Exception as e:
        logger.warning(f"MITRE technique lookup failed for {technique_id}: {e}")
        return None


def _lookup_tactic(tactic_id: str) -> Optional[Dict[str, Any]]:
    """Return MITRE tactic data if the loader is available."""
    if not get_mitre_lookup or not tactic_id:
        return None
    try:
        return get_mitre_lookup().get_tactic(tactic_id)
    except Exception as e:
        logger.warning(f"MITRE tactic lookup failed for {tactic_id}: {e}")
        return None


def _build_context(flow_data: Dict[str, Any], industry: str, region: str,
                   organization_size: str) -> Dict[str, Any]:
    """Build the x_oic_context block for the markdown formatter."""
    return {
        "industry": industry,
        "region": region,
        "organization_size": organization_size,
        "generated_at": _now(),
        "generator": "OIC Attack Flow Workbench v0.1.0",
        "generation_status": flow_data.get("generation_status", "generated"),
    }


def convert(flow_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a generator in-memory flow object to a STIX 2.1 Attack Flow bundle.

    Args:
        flow_data: The generator's native flow dict with keys such as:
            name, description, scope, attack_actions, logic, entry_points,
            assets, threat_actor, generation_status, and optionally
            x_oic_context with industry/region/organization_size.

    Returns:
        A STIX 2.1 bundle dict with type "bundle" and an "objects" list.
    """
    if not isinstance(flow_data, dict):
        raise ValueError("flow_data must be a dict")

    ts = _now()
    ctx = flow_data.get("x_oic_context", {})
    industry = ctx.get("industry", "unknown")
    region = ctx.get("region", "unknown")
    org_size = ctx.get("organization_size", "unknown")

    # --- extension-definition (canonical Attack Flow extension) ---
    bundle_objs = []
    bundle_objs.append({
        "type": "extension-definition",
        "spec_version": "2.1",
        "id": AF_EXT,
        "created": "2022-08-02T19:34:35.143Z",
        "modified": "2022-08-02T19:34:35.143Z",
        "name": "Attack Flow",
        "description": "Extends STIX 2.1 with features to create Attack Flows.",
        "schema": "https://center-for-threat-informed-defense.github.io/attack-flow/stix/attack-flow-schema-2.0.0.json",
        "version": "2.0.0",
        "extension_types": ["new-sdo"],
    })

    # --- identity (producer) ---
    ident_id = _sid("identity")
    bundle_objs.append({
        "type": "identity",
        "spec_version": "2.1",
        "id": ident_id,
        "created": ts,
        "modified": ts,
        "name": PRODUCER_NAME,
        "identity_class": "system",
    })

    # --- map generator ids to STIX ids ---
    actions = flow_data.get("attack_actions", [])
    assets = flow_data.get("assets", [])

    action_id_map: Dict[str, str] = {}
    for action in actions:
        aid = action.get("id")
        if aid and aid not in action_id_map:
            action_id_map[aid] = _sid("attack-action")

    asset_id_map: Dict[str, str] = {}
    for asset in assets:
        key = asset if isinstance(asset, str) else asset.get("id") or asset.get("name")
        if key and key not in asset_id_map:
            asset_id_map[key] = _sid("attack-asset")

    # --- successor graph from depends_on ---
    # successors[action_id] = list of action ids that depend on it.
    successors: Dict[str, List[str]] = {aid: [] for aid in action_id_map}
    has_incoming: set = set()
    for action in actions:
        aid = action.get("id")
        for dep in action.get("depends_on", []) or []:
            if dep in successors and aid:
                successors[dep].append(aid)
                has_incoming.add(aid)

    # --- build attack-action objects ---
    for action in actions:
        aid = action.get("id")
        if not aid:
            continue
        stix_id = action_id_map[aid]

        tactic_id = _resolve_tactic(action.get("tactic"))
        technique_id = action.get("technique_id")
        technique = _lookup_technique(technique_id) if technique_id else None

        obj: Dict[str, Any] = {
            "type": "attack-action",
            "spec_version": "2.1",
            "id": stix_id,
            "created": ts,
            "modified": ts,
            "name": action.get("name", "Unnamed action"),
            "tactic_id": tactic_id or None,
            "technique_id": technique_id or None,
            "description": action.get("description", "") or None,
            "extensions": EXT_BLOCK,
        }

        if tactic_id:
            tactic = _lookup_tactic(tactic_id)
            if tactic:
                obj["tactic_ref"] = tactic.get("stix_id")
        if technique and technique.get("stix_id"):
            obj["technique_ref"] = technique["stix_id"]

        confidence = _map_confidence(action.get("confidence"))
        if confidence is not None:
            obj["confidence"] = confidence

        # effect_refs = successors (STIX edges point forward)
        effects = [action_id_map[s] for s in successors.get(aid, []) if s in action_id_map]
        if effects:
            obj["effect_refs"] = effects

        # asset_refs = targeted assets this action compromises
        refs = action.get("asset_refs", []) or []
        if refs:
            asset_refs = []
            for ref in refs:
                # Accept either a raw asset name or a key already known to the flow.
                key = ref if isinstance(ref, str) else (ref.get("id") or ref.get("name"))
                if key and key in asset_id_map:
                    asset_refs.append(asset_id_map[key])
                elif key:
                    # Unknown asset name: create a new asset on the fly so refs never dangle.
                    asset_id_map[key] = _sid("attack-asset")
                    asset_refs.append(asset_id_map[key])
            if asset_refs:
                obj["asset_refs"] = asset_refs

        bundle_objs.append(_omit_nulls(obj))

    # --- build attack-asset objects ---
    for key, stix_id in asset_id_map.items():
        asset_name = key if isinstance(key, str) else key.get("name", "Unnamed asset")
        bundle_objs.append({
            "type": "attack-asset",
            "spec_version": "2.1",
            "id": stix_id,
            "created": ts,
            "modified": ts,
            "name": asset_name,
            "extensions": EXT_BLOCK,
        })

    # --- start_refs = entry points or actions with no incoming edge ---
    entry_points = flow_data.get("entry_points", []) or []
    if entry_points:
        starts = [action_id_map[ep] for ep in entry_points if ep in action_id_map]
    else:
        starts = [action_id_map[aid] for aid in action_id_map if aid not in has_incoming]
    if not starts and action_id_map:
        # Fallback: first action in the list.
        starts = [action_id_map[next(iter(action_id_map))]]

    # --- attack-flow SDO ---
    flow_id = _sid("attack-flow")
    is_stub = flow_data.get("generation_status") == "fallback_stub"
    description = flow_data.get("description", "") or ""
    if is_stub:
        description = "[FALLBACK STUB - generation failed, not grounded] " + description

    flow_obj: Dict[str, Any] = {
        "type": "attack-flow",
        "spec_version": "2.1",
        "id": flow_id,
        "created": ts,
        "modified": ts,
        "created_by_ref": ident_id,
        "name": flow_data.get("name", "Generated Attack Flow"),
        "description": description or None,
        "scope": flow_data.get("scope", "incident") or "incident",
        "start_refs": starts,
        "extensions": EXT_BLOCK,
    }
    bundle_objs.append(_omit_nulls(flow_obj))

    bundle = {
        "type": "bundle",
        "id": _sid("bundle"),
        "objects": bundle_objs,
    }

    # Preserve provenance/context for the markdown formatter. These are not
    # STIX properties and live on the bundle root so they do not affect schema
    # validation of the SDO objects.
    bundle["x_oic_context"] = _build_context(flow_data, industry, region, org_size)
    bundle["x_original_flow"] = flow_data

    return bundle


def count_nodes(bundle: Dict[str, Any]) -> Dict[str, int]:
    """Return counts of STIX object types in a bundle."""
    counts: Dict[str, int] = {}
    for obj in bundle.get("objects", []):
        t = obj.get("type")
        counts[t] = counts.get(t, 0) + 1
    return counts
