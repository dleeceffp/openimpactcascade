"""
Test script to verify STIX bundle format with author identity and proper timestamps.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from attack_flow_generator import AttackFlowGenerator


def test_fallback_flow_format():
    """Test that fallback flow generates proper STIX format."""
    print("=" * 70)
    print("Testing STIX Bundle Format")
    print("=" * 70)

    # Create generator - bypass API key check for testing
    import anthropic
    original_init = anthropic.Anthropic.__init__
    anthropic.Anthropic.__init__ = lambda self, **kwargs: None

    try:
        gen = AttackFlowGenerator(api_key="dummy_key_for_testing")
    except Exception as e:
        print(f"Could not create generator: {e}")
        return
    finally:
        anthropic.Anthropic.__init__ = original_init

    # Generate fallback flow directly
    flow = gen._generate_fallback_flow("energy", ["System Intrusion"])
    print("\n1. Fallback Flow Data Structure:")
    print(f"   - Name: {flow['name']}")
    print(f"   - Scope: {flow['scope']}")
    print(f"   - Generation Status: {flow.get('generation_status', 'N/A')}")
    print(f"   - Actions: {len(flow['attack_actions'])}")

    # Check schema
    print("\n2. Schema Validation:")
    for action in flow['attack_actions']:
        assert 'id' in action, "Missing 'id' field"
        assert 'depends_on' in action, "Missing 'depends_on' field"
        assert 'confidence' in action, "Missing 'confidence' field"
    print("   ✓ All actions have 'id', 'depends_on', and 'confidence'")

    # Format as STIX bundle
    print("\n3. STIX Bundle Format:")
    stix_bundle = gen._format_as_attack_flow(
        flow,
        industry="energy",
        region="Canada",
        organization_size="2500"
    )

    print(f"   - Bundle type: {stix_bundle['type']}")
    print(f"   - Objects count: {len(stix_bundle['objects'])}")

    # Check for identity object
    identity_objects = [obj for obj in stix_bundle['objects'] if obj['type'] == 'identity']
    print(f"   - Identity objects: {len(identity_objects)}")

    if identity_objects:
        identity = identity_objects[0]
        print(f"     * ID: {identity['id']}")
        print(f"     * Name: {identity['name']}")
        print(f"     * Class: {identity.get('identity_class', 'N/A')}")
        print(f"     * Created: {identity.get('created', 'N/A')}")

    # Check attack-flow object
    flow_objects = [obj for obj in stix_bundle['objects'] if obj['type'] == 'attack-flow']
    if flow_objects:
        af = flow_objects[0]
        print(f"   - Attack-flow object:")
        print(f"     * ID: {af['id']}")
        print(f"     * Created: {af.get('created', 'N/A')}")
        print(f"     * Created by ref: {af.get('created_by_ref', 'N/A')}")
        print(f"     * Start refs: {af.get('start_refs', [])}")
        print(f"     * Scope: {af.get('scope', 'N/A')}")

    # Check attack-action objects
    action_objects = [obj for obj in stix_bundle['objects'] if obj['type'] == 'attack-action']
    print(f"   - Attack-action objects: {len(action_objects)}")

    if action_objects:
        action = action_objects[0]
        print(f"     * First action ID: {action['id']}")
        print(f"     * Created: {action.get('created', 'N/A')}")
        print(f"     * Created by ref: {action.get('created_by_ref', 'N/A')}")
        print(f"     * Effect refs: {action.get('effect_refs', 'N/A')}")

    # Verify all objects have required fields
    print("\n4. Validating All Objects:")
    all_valid = True
    for obj in stix_bundle['objects']:
        if 'created' not in obj:
            print(f"   ✗ {obj['type']} missing 'created'")
            all_valid = False
        if 'created_by_ref' not in obj and obj['type'] != 'identity':
            print(f"   ✗ {obj['type']} missing 'created_by_ref'")
            all_valid = False

    if all_valid:
        print("   ✓ All objects have 'created' and 'created_by_ref'")

    # Check effect_refs connect properly
    print("\n5. Edge Connection Check:")
    id_map = {obj['id']: obj for obj in stix_bundle['objects']}
    for obj in stix_bundle['objects']:
        if obj['type'] == 'attack-action' and 'effect_refs' in obj:
            for ref in obj['effect_refs']:
                if ref not in id_map:
                    print(f"   ✗ Dangling effect_ref: {ref}")
                else:
                    target = id_map[ref]
                    print(f"   ✓ {obj['id'][:20]}... -> {target['type']} {target['id'][:20]}...")

    # Save sample output
    print("\n6. Saving Sample Output:")
    output_path = Path(__file__).parent / "test_output.json"
    with open(output_path, 'w') as f:
        json.dump(stix_bundle, f, indent=2)
    print(f"   Saved to: {output_path}")

    print("\n" + "=" * 70)
    print("Test Complete")
    print("=" * 70)


if __name__ == "__main__":
    test_fallback_flow_format()
