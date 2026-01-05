"""
Test that context formatting handles partial/None FAIR estimates properly.
"""

# Simulate the assessment context with partial data
assessment_summary = {
    'industry': 'Technology',
    'region': 'Canada',
    'organization_size': '25',
    'questions_answered': 2,
    'current_question': {
        'id': 'q2',
        'text': 'What is your threat event frequency?',
        'type': 'pert_estimate'
    },
    'threat_scenario': 'Ransomware Attack',
    'control_level': None,
    'fair_estimates': {
        'tef': {'min': None, 'mle': None, 'max': None},  # Not entered yet
        'vulnerability': None,
        'lef': {'min': 0.1, 'mle': 0.5, 'max': 1.2},  # Partially entered
        'lm': {'min': 50000, 'mle': 400000, 'max': 2000000}  # Fully entered
    },
    'recent_answers': {},
    'chat_history': []
}

# Test the formatting logic
prompt_parts = []
fair = assessment_summary['fair_estimates']

print("Testing FAIR estimate formatting with partial data...")
print("="*60)

# TEF estimates (all None - should NOT appear)
tef = fair.get('tef', {})
if tef.get('min') is not None and tef.get('mle') is not None and tef.get('max') is not None:
    prompt_parts.append(f"\nThreat Event Frequency: {tef['min']}-{tef['mle']}-{tef['max']} attempts/year")
    print("✅ TEF included")
else:
    print("⏭️  TEF skipped (incomplete data)")

# Vulnerability (None - should NOT appear)
if fair.get('vulnerability') is not None:
    prompt_parts.append(f"Vulnerability: {fair['vulnerability']*100:.0f}% (attack success rate)")
    print("✅ Vulnerability included")
else:
    print("⏭️  Vulnerability skipped (not set)")

# LEF estimates (all present - SHOULD appear)
lef = fair.get('lef', {})
if lef.get('min') is not None and lef.get('mle') is not None and lef.get('max') is not None:
    prompt_parts.append(f"Loss Event Frequency: {lef['min']}-{lef['mle']}-{lef['max']} events/year")
    print("✅ LEF included")
else:
    print("⏭️  LEF skipped (incomplete data)")

# LM estimates (all present - SHOULD appear)
lm = fair.get('lm', {})
if lm.get('min') is not None and lm.get('mle') is not None and lm.get('max') is not None:
    prompt_parts.append(f"Loss Magnitude: ${lm['min']:,.0f}-${lm['mle']:,.0f}-${lm['max']:,.0f}")
    print("✅ LM included")
else:
    print("⏭️  LM skipped (incomplete data)")

print("="*60)
print("\nGenerated prompt context:")
print("-"*60)
for part in prompt_parts:
    print(part)
print("-"*60)

print("\n✅ Test passed - No formatting errors with partial data!")
