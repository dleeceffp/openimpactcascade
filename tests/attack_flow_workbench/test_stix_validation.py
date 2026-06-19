"""Validation test for the Attack Flow STIX serializer and formatter.

This test can be run directly:

    python tests/attack_flow_workbench/test_stix_validation.py

It constructs a representative in-memory flow (the same shape the generator
returns), serializes it to a STIX 2.1 Attack Flow bundle, and validates the
bundle against the MITRE attack-flow-schema-2.0.0.json schema.
"""
import json
import sys
from pathlib import Path

# Ensure the workbench modules are importable
WORKBENCH = Path(__file__).parent.parent.parent / "tools" / "attack_flow_workbench"
sys.path.insert(0, str(WORKBENCH))

from stix_serializer import convert as to_stix_bundle, count_nodes
from formatter import AttackFlowFormatter
from config import ATTACK_FLOW_SCHEMA_FILE


def build_sample_flow() -> dict:
    """Return a sample in-memory flow matching the generator's output schema."""
    return {
        "name": "Ransomware against Canadian energy SME",
        "description": "Phishing-delivered ransomware with data exfiltration.",
        "scope": "incident",
        "attack_actions": [
            {
                "id": "n1",
                "name": "Spearphishing Attachment",
                "technique_id": "T1566.001",
                "tactic": "Initial Access",
                "description": "Employee opens a malicious email attachment.",
                "depends_on": [],
                "confidence": "observed",
                "asset_refs": ["Workstation"],
            },
            {
                "id": "n2",
                "name": "Malicious File",
                "technique_id": "T1204.002",
                "tactic": "Execution",
                "description": "Malicious macro executes a payload.",
                "depends_on": ["n1"],
                "confidence": "observed",
                "asset_refs": ["Workstation"],
            },
            {
                "id": "n3",
                "name": "Registry Run Keys",
                "technique_id": "T1547.001",
                "tactic": "Persistence",
                "description": "Payload establishes persistence via registry.",
                "depends_on": ["n2"],
                "confidence": "reported",
                "asset_refs": ["Workstation"],
            },
            {
                "id": "n4",
                "name": "Data Encrypted for Impact",
                "technique_id": "T1486",
                "tactic": "Impact",
                "description": "Ransomware encrypts data on servers.",
                "depends_on": ["n3"],
                "confidence": "speculative",
                "asset_refs": ["File Server", "Workstation"],
            },
        ],
        "logic": [],
        "entry_points": ["n1"],
        "assets": ["Workstation", "File Server"],
        "threat_actor": "External - Financially Motivated",
        "x_oic_context": {
            "industry": "energy",
            "region": "Canada",
            "organization_size": "2500",
            "generated_at": "2024-01-01T00:00:00Z",
            "generator": "OIC Attack Flow Workbench v0.1.0",
            "generation_status": "generated",
        },
    }


def validate_against_schema(bundle: dict) -> None:
    """Validate every Attack Flow SDO in the bundle against the MITRE schema.

    The schema validates individual SDOs (attack-flow, attack-action, etc.),
    not the STIX bundle wrapper, so we validate each object of the relevant
    types. Custom provenance fields live on the bundle root and are therefore
    not part of schema validation.
    """
    if not ATTACK_FLOW_SCHEMA_FILE.exists():
        raise FileNotFoundError(f"Schema file not found: {ATTACK_FLOW_SCHEMA_FILE}")

    with open(ATTACK_FLOW_SCHEMA_FILE, "r", encoding="utf-8") as f:
        schema = json.load(f)

    try:
        import jsonschema
    except ImportError:
        raise RuntimeError("jsonschema is required for validation")

    attack_flow_types = {
        "attack-flow", "attack-action", "attack-asset",
        "attack-condition", "attack-operator",
    }
    for obj in bundle.get("objects", []):
        if obj.get("type") in attack_flow_types:
            jsonschema.validate(obj, schema)


def test_stix_serializer() -> None:
    """Run the serialization/validation tests."""
    flow = build_sample_flow()
    bundle = to_stix_bundle(flow)

    # Basic bundle shape
    assert bundle.get("type") == "bundle"
    assert "id" in bundle
    assert "objects" in bundle

    # Object counts
    counts = count_nodes(bundle)
    assert counts.get("extension-definition") == 1
    assert counts.get("identity") == 1
    assert counts.get("attack-flow") == 1
    assert counts.get("attack-action") == 4
    assert counts.get("attack-asset") == 2

    # Locate the flow and action objects
    af = next(o for o in bundle["objects"] if o["type"] == "attack-flow")
    actions = {o["id"]: o for o in bundle["objects"] if o["type"] == "attack-action"}
    assets = {o["id"]: o for o in bundle["objects"] if o["type"] == "attack-asset"}

    # Flow has required fields
    assert af["name"] == flow["name"]
    assert af["scope"] == flow["scope"]
    assert af["start_refs"]

    # Confidence mapped to integer
    for action in actions.values():
        assert isinstance(action["confidence"], int)
        assert 0 <= action["confidence"] <= 100

    # effect_refs derived from depends_on (n1 -> n2 -> n3 -> n4)
    n1 = next(o for o in actions.values() if o["name"] == "Spearphishing Attachment")
    n2 = next(o for o in actions.values() if o["name"] == "Malicious File")
    n3 = next(o for o in actions.values() if o["name"] == "Registry Run Keys")
    n4 = next(o for o in actions.values() if o["name"] == "Data Encrypted for Impact")
    assert n2["id"] in n1.get("effect_refs", [])
    assert n3["id"] in n2.get("effect_refs", [])
    assert n4["id"] in n3.get("effect_refs", [])

    # asset_refs point to known assets
    asset_name_by_id = {aid: a["name"] for aid, a in assets.items()}
    for action in actions.values():
        for ref in action.get("asset_refs", []):
            assert ref in asset_name_by_id

    # Schema validation
    validate_against_schema(bundle)

    # Formatter round-trips
    json_text = AttackFlowFormatter.to_json(flow)
    parsed = json.loads(json_text)
    assert parsed["type"] == "bundle"

    markdown = AttackFlowFormatter.to_summary_markdown(flow)
    assert "STIX 2.1 Attack Flow" in markdown
    assert "Ransomware" in markdown
    assert "Workstation" in markdown
    assert "attack_flow_viewer.html" in markdown

    # Optional: parse with the official stix2 library if installed
    try:
        import stix2
        stix2.parse(bundle, allow_custom=True)
        print("stix2.parse: PASS")
    except ImportError:
        print("stix2 library not installed; skipping stix2.parse check")

    print("STIX serializer validation: PASS")


def test_stix_serializer_roundtrip() -> None:
    """Ensure a bundle that is already STIX is dumped as-is by to_json."""
    bundle = to_stix_bundle(build_sample_flow())
    dumped = AttackFlowFormatter.to_json(bundle)
    assert json.loads(dumped)["type"] == "bundle"
    print("STIX bundle round-trip: PASS")


if __name__ == "__main__":
    test_stix_serializer()
    test_stix_serializer_roundtrip()
    print("\nAll validation tests passed.")
