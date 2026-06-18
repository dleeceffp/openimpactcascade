"""
Demo script showing the Attack Flow Workbench components without API calls.

This demonstrates:
1. MITRE ATT&CK technique lookup
2. Corpus grounding from DBIR data
3. Attack flow structure generation

Run without API keys:
    python example_demo.py
"""

import sys
from pathlib import Path

# Ensure imports work when running directly
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))

from mitre_loader import MitreTechniqueLookup
from formatter import AttackFlowFormatter


def demo_mitre_lookup():
    """Demonstrate MITRE technique lookup."""
    print("=" * 70)
    print("DEMO: MITRE ATT&CK Technique Lookup")
    print("=" * 70)

    lookup = MitreTechniqueLookup()
    lookup.load()

    # Look up a common technique
    tech_id = "T1566.001"  # Spearphishing Attachment
    technique = lookup.get_technique(tech_id)

    if technique:
        print(f"\nTechnique: {technique['id']} - {technique['name']}")
        print(f"Description: {technique['description'][:200]}...")

        # Get tactic for this technique
        tactic = lookup.get_tactic_for_technique(tech_id)
        if tactic:
            print(f"Tactic: {tactic['id']} - {tactic['name']}")
    else:
        print(f"Technique {tech_id} not found (MITRE matrix may not be loaded)")

    # List some common techniques
    print("\nCommon Initial Access Techniques:")
    common_techniques = ["T1566", "T1566.001", "T1566.002", "T1190", "T1133"]
    for tech_id in common_techniques:
        tech = lookup.get_technique(tech_id)
        if tech:
            print(f"  - {tech['id']}: {tech['name']}")

    print(f"\nTotal techniques loaded: {len(lookup.list_all_techniques())}")


def demo_attack_flow_structure():
    """Demonstrate attack flow structure and formatting."""
    print("\n" + "=" * 70)
    print("DEMO: Attack Flow Structure and Formatting")
    print("=" * 70)

    # Create a sample attack flow (without LLM) - using new dependency-based schema
    sample_flow = {
        "type": "attack-flow",
        "id": "attack-flow--demo-123",
        "name": "Ransomware Attack - Healthcare",
        "description": "A typical ransomware attack targeting a healthcare organization",
        "scope": "incident",
        "start_refs": ["attack-action--step1"],
        "x_oic_context": {
            "industry": "healthcare",
            "region": "United States",
            "organization_size": "500-1000",
            "generated_at": "2025-01-15T10:00:00",
            "generator": "OIC Attack Flow Workbench Demo"
        },
        "attack_actions": [
            {
                "id": "n1",
                "name": "Spearphishing Attachment",
                "technique_id": "T1566.001",
                "tactic": "Initial Access",
                "description": "Phishing email with malicious attachment delivered to employee",
                "depends_on": [],
                "confidence": "observed"
            },
            {
                "id": "n2",
                "name": "Malicious File",
                "technique_id": "T1204.002",
                "tactic": "Execution",
                "description": "User opens malicious attachment executing malware",
                "depends_on": ["n1"],
                "confidence": "observed"
            },
            {
                "id": "n3",
                "name": "Registry Run Keys",
                "technique_id": "T1547.001",
                "tactic": "Persistence",
                "description": "Malware establishes persistence via registry keys",
                "depends_on": ["n2"],
                "confidence": "reported"
            },
            {
                "id": "n4",
                "name": "Data Encrypted for Impact",
                "technique_id": "T1486",
                "tactic": "Impact",
                "description": "Ransomware encrypts patient records and critical systems",
                "depends_on": ["n3"],
                "confidence": "observed"
            }
        ],
        "logic": [],
        "entry_points": ["n1"],
        "assets": ["Workstation", "File Server", "EMR System", "Patient Database"],
        "threat_actor": "External - Financially Motivated"
    }

    print("\nSample Attack Flow Structure:")
    print(f"  Name: {sample_flow['name']}")
    print(f"  Scope: {sample_flow['scope']}")
    print(f"  Actions: {len(sample_flow['attack_actions'])}")

    # Format as markdown
    print("\n" + "-" * 70)
    print("Markdown Summary:")
    print("-" * 70)
    md_output = AttackFlowFormatter.to_summary_markdown(sample_flow)
    print(md_output[:500] + "...")

    # Format as JSON
    print("\n" + "-" * 70)
    print("JSON Output (excerpt):")
    print("-" * 70)
    json_output = AttackFlowFormatter.to_json(sample_flow)
    print(json_output[:500] + "...")


def demo_corpus_check():
    """Check if corpus grounding is available."""
    print("\n" + "=" * 70)
    print("DEMO: Corpus Grounding Check")
    print("=" * 70)

    try:
        from corpus_grounding import get_grounding

        grounding = get_grounding()

        if grounding._enabled:
            print("[OK] Corpus grounding is available")

            # Get grounding for healthcare
            result = grounding.get_grounding_for_industry("healthcare")
            print(f"\nHealthcare Grounding:")
            print(f"  Industry: {result['industry_canonical']}")
            print(f"  Source: {result['source'] or 'N/A'}")
            print(f"  Coverage: {result['coverage']}")

            if result['sector_data']:
                print(f"  Top Patterns: {result['sector_data'].get('top_patterns', 'N/A')[:80]}...")

            # Format as text
            formatted = grounding.format_grounding_for_prompt(result)
            print(f"\nFormatted Grounding (first 300 chars):")
            print(formatted[:300] + "...")
        else:
            print("[WARNING] Corpus grounding is not available")
            print("   (DBIR pillar data not found in app/corpus/ref_pillars/)")

    except Exception as e:
        print(f"[ERROR] Error checking corpus: {e}")
        print("   (Expected if running outside the full OIC environment)")


def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("MITRE Attack Flow Generation Workbench - Demo")
    print("=" * 70)
    print("\nThis demo shows the workbench components without requiring API keys.\n")

    try:
        demo_mitre_lookup()
    except Exception as e:
        print(f"MITRE lookup demo error: {e}")

    try:
        demo_attack_flow_structure()
    except Exception as e:
        print(f"Attack flow structure demo error: {e}")

    try:
        demo_corpus_check()
    except Exception as e:
        print(f"Corpus check demo error: {e}")

    print("\n" + "=" * 70)
    print("Demo Complete")
    print("=" * 70)
    print("\nTo generate full Attack Flows with LLM:")
    print("  1. Set ANTHROPIC_API_KEY environment variable")
    print("  2. Run: python cli.py --industry healthcare --region 'US' --org-size SME")
    print()


if __name__ == "__main__":
    main()
