"""
Quick test to verify lognormal distribution now produces proper fat-tailed catastrophic values.
Tests with the user's actual input: LM = $100k - $500k - $2M
"""

import sys
sys.path.insert(0, 'app')

from simulation_v211 import run_monte_carlo

print("="*80)
print("TESTING LOGNORMAL FAT TAIL FIX")
print("="*80)
print()

# User's actual values from the log
lef_min = 0.1
lef_mle = 0.35
lef_max = 0.75

lm_min = 100000
lm_mle = 500000
lm_max = 2000000

print(f"Input Values:")
print(f"  LEF: {lef_min} - {lef_mle} - {lef_max} events/year")
print(f"  LM:  ${lm_min:,} - ${lm_mle:,} - ${lm_max:,}")
print()

# Run simulation with lognormal for LM
results = run_monte_carlo(
    lef_min=lef_min,
    lef_mle=lef_mle,
    lef_max=lef_max,
    lm_min=lm_min,
    lm_mle=lm_mle,
    lm_max=lm_max,
    n_simulations=10000,
    lef_distribution='pert',
    lm_distribution='lognormal'
)

print(f"Results:")
print(f"  Mean:   ${results['mean']:,.0f}")
print(f"  Median: ${results['p50']:,.0f}")
print(f"  StdDev: ${results['std']:,.0f}")
print()

print(f"Percentiles:")
print(f"  P10:  ${results['p10']:,.0f}")
print(f"  P25:  ${results['p25']:,.0f}")
print(f"  P50:  ${results['p50']:,.0f}")
print(f"  P75:  ${results['p75']:,.0f}")
print(f"  P90:  ${results['p90']:,.0f}")
print(f"  P95:  ${results['p95']:,.0f}")
print(f"  P99:  ${results['p99']:,.0f}")
print(f"  Max:  ${results['max']:,.0f}")
print()

print("="*80)
print("ANALYSIS OF FAT TAIL BEHAVIOR")
print("="*80)
print()

# Check if catastrophic values exceed user's max input
max_input = lm_max
p95_value = results['p95']
p99_value = results['p99']
max_value = results['max']

print(f"User's Max Input:     ${max_input:,.0f}")
print(f"P95 (1 in 20):        ${p95_value:,.0f}  [{p95_value/max_input:.1f}x max]")
print(f"P99 (1 in 100):       ${p99_value:,.0f}  [{p99_value/max_input:.1f}x max]")
print(f"Simulation Max:       ${max_value:,.0f}  [{max_value/max_input:.1f}x max]")
print()

# Verification
if p95_value > max_input:
    print("✅ PASS: P95 exceeds user's max input (fat tail working correctly)")
else:
    print("❌ FAIL: P95 should exceed user's max input")

if p99_value > max_input * 1.5:
    print("✅ PASS: P99 is significantly beyond max input (catastrophic tail working)")
else:
    print("⚠️  WARNING: P99 might be too conservative")

print()
print("Expected behavior for cyber risk lognormal:")
print("  - Most values: Below mode ($500k)")
print("  - P85:        Near user's max ($2M)")
print("  - P95:        1.5-2x user's max ($3M-$4M)")
print("  - P99:        2-4x user's max ($4M-$8M)")
print("  - Max:        Could be 5-10x max in rare cases")
print()
