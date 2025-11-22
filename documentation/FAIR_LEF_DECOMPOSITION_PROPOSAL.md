# FAIR LEF Decomposition: TEF + Vulnerability Approach

## Executive Summary

**Problem:** Current LLM-generated questions for Loss Event Frequency (LEF) confuse users because they don't differentiate between attack attempts (TEF) and successful attacks that result in loss (LEF).

**Solution:** Decompose LEF into its FAIR components: Threat Event Frequency (TEF) × Vulnerability, with control effectiveness mapped to vulnerability percentages.

## Background: The Open FAIR Ontology

### Core Formula
```
LEF = TEF × Vulnerability
```

Where:
- **TEF (Threat Event Frequency)**: How often a threat actor *attempts* an attack (events/year)
- **Vulnerability**: Probability that an attack attempt succeeds and causes loss (0.0 to 1.0)
- **LEF (Loss Event Frequency)**: How often attacks *successfully cause loss* (events/year)

### Real-World Example (from user)

**Scenario:** APT targeting with social engineering for credentials

- **Threat Event Frequency (TEF):** 2 attacks/year
  - "An APT targets my company twice a year with social engineering"
  
- **Vulnerability:** 10% (0.10)
  - "They occasionally get creds but fail 90% of the time due to additional controls"
  - Ability to resist = 90% (strong)
  - Vulnerability = 10% (1 - 0.90)
  
- **Loss Event Frequency (LEF):** 0.2 events/year
  - LEF = 2 × 0.10 = 0.2
  - "One successful breach every 5 years on average"

### Why This Matters

From FAIR Institute research:
- **Most-missed question** on FAIR certification exam
- Users conflate "how often attacked" with "how often harmed"
- Critical for accurate risk quantification

## Current Implementation Issues

### Problem 1: Single LEF Question
```json
{
  "id": "threat_ransomware_frequency",
  "text": "How often do you estimate this ransomware threat could occur?",
  "type": "pert_estimate",
  "estimate_type": "frequency_per_year"
}
```

**Issue:** Users don't know if this means:
- How often they're attacked? (TEF)
- How often attacks succeed? (LEF)
- Something in between?

### Problem 2: Control Questions Don't Map to Vulnerability
```json
{
  "text": "What security controls do you have in place?",
  "choices": [
    {"text": "Basic antivirus only", "risk_multiplier": 2.0},
    {"text": "EDR + backup + training", "risk_multiplier": 0.5}
  ]
}
```

**Issue:** 
- `risk_multiplier` affects LEF but doesn't explicitly represent vulnerability
- No clear connection between control strength and attack success probability
- Users can't see how controls reduce vulnerability

## Recommended Solution: Three-Question Decomposition

### Approach 1: Explicit TEF + Vulnerability (RECOMMENDED)

#### Question 1: Threat Event Frequency (TEF)
```json
{
  "id": "threat_ransomware_tef",
  "text": "How often do threat actors attempt ransomware attacks against organizations like yours?",
  "type": "pert_estimate",
  "estimate_type": "threat_attempts_per_year",
  "help_text": "This is the frequency of ATTEMPTS, not successful breaches. Based on your threat intelligence, how often do attackers try to compromise you?",
  "fair_component": "TEF",
  "guidance": {
    "minimum": "Best case - rare targeting (e.g., 0.5 = once every 2 years)",
    "most_likely": "Realistic estimate based on industry data (e.g., 4 = 4 attempts/year)",
    "maximum": "Worst case - heavy targeting (e.g., 12 = monthly attempts)"
  },
  "examples": {
    "Healthcare": "Healthcare orgs see avg 6-10 ransomware attempts/year (CISA 2024)",
    "Finance": "Financial services see avg 15-20 targeted attacks/year (FS-ISAC 2024)",
    "Retail": "Retail orgs see avg 3-5 ransomware campaigns/year (NRF 2024)"
  }
}
```

#### Question 2: Control Effectiveness
```json
{
  "id": "threat_ransomware_controls",
  "text": "What is your organization's ability to resist ransomware attacks?",
  "type": "multiple_choice",
  "help_text": "Select the option that best describes your defensive controls. This determines what percentage of attack attempts successfully cause a loss event.",
  "fair_component": "Vulnerability",
  "choices": [
    {
      "id": "controls_minimal",
      "text": "Minimal - Basic antivirus only",
      "description": "No EDR, limited email security, no security awareness training",
      "vulnerability": 0.70,
      "vulnerability_display": "70% of attacks succeed (weak resistance)",
      "control_examples": ["Basic antivirus", "Standard email filtering"],
      "next_question_id": "threat_ransomware_tef"
    },
    {
      "id": "controls_basic",
      "text": "Basic - Antivirus + some email security",
      "description": "Antivirus, email filtering, but no EDR or backup verification",
      "vulnerability": 0.40,
      "vulnerability_display": "40% of attacks succeed (moderate resistance)",
      "control_examples": ["Antivirus", "Email security", "Basic patching"],
      "next_question_id": "threat_ransomware_tef"
    },
    {
      "id": "controls_intermediate",
      "text": "Intermediate - EDR + email security + some training",
      "description": "EDR/XDR, advanced email security, quarterly security training, tested backups",
      "vulnerability": 0.15,
      "vulnerability_display": "15% of attacks succeed (good resistance)",
      "control_examples": ["EDR/XDR", "Advanced email security", "Security training", "Tested backups"],
      "next_question_id": "threat_ransomware_tef"
    },
    {
      "id": "controls_advanced",
      "text": "Advanced - Comprehensive security program",
      "description": "EDR/XDR, SIEM, MFA, continuous training, immutable backups, incident response plan",
      "vulnerability": 0.05,
      "vulnerability_display": "5% of attacks succeed (strong resistance)",
      "control_examples": ["EDR/XDR + SIEM", "Universal MFA", "Monthly training", "Immutable backups", "IR playbooks"],
      "next_question_id": "threat_ransomware_tef"
    }
  ]
}
```

#### Question 3: Calculated LEF (Auto-computed)
```json
{
  "id": "threat_ransomware_lef_result",
  "text": "Based on your inputs, here is the calculated Loss Event Frequency:",
  "type": "calculated_display",
  "calculation": "LEF = TEF × Vulnerability",
  "display_format": {
    "tef": "{tef_mle} attack attempts per year",
    "vulnerability": "{vulnerability}% success rate",
    "lef": "{lef_mle} successful breaches per year",
    "interpretation": "On average, 1 successful breach every {1/lef_mle} years"
  },
  "editable": true,
  "help_text": "This is automatically calculated from your threat frequency and control effectiveness. You can adjust if you have better data.",
  "next_question_id": "threat_ransomware_magnitude"
}
```

### Calculation Logic

```python
def calculate_lef(tef_min, tef_mle, tef_max, vulnerability):
    """
    Calculate LEF from TEF and Vulnerability.
    
    Args:
        tef_min: Minimum threat event frequency (attempts/year)
        tef_mle: Most likely threat event frequency (attempts/year)
        tef_max: Maximum threat event frequency (attempts/year)
        vulnerability: Probability of success (0.0 to 1.0)
    
    Returns:
        Tuple of (lef_min, lef_mle, lef_max)
    """
    lef_min = tef_min * vulnerability
    lef_mle = tef_mle * vulnerability
    lef_max = tef_max * vulnerability
    
    return (lef_min, lef_mle, lef_max)

# Example from user scenario:
tef = (1, 2, 4)  # Min 1, Most likely 2, Max 4 attacks/year
vulnerability = 0.10  # 10% succeed (90% blocked)
lef = calculate_lef(*tef, vulnerability)
# Result: (0.1, 0.2, 0.4) = Most likely 0.2 successful breaches/year
# Interpretation: 1 breach every 5 years on average
```

### Approach 2: Simplified Two-Question (ALTERNATIVE)

If three questions feel like too much, combine controls with TEF:

```json
{
  "id": "threat_ransomware_frequency_with_controls",
  "text": "Considering your current security controls, how often would ransomware attacks SUCCESSFULLY cause a loss event?",
  "type": "pert_estimate",
  "estimate_type": "frequency_per_year",
  "help_text": "Think about this in two parts: (1) How often are you attacked? (2) What % of attacks succeed given your controls? LEF = Attacks × Success Rate",
  "guidance": {
    "calculation_helper": {
      "step_1": "Estimate attack attempts per year (TEF)",
      "step_2": "Estimate your control effectiveness",
      "weak_controls": "70% of attacks succeed",
      "moderate_controls": "40% of attacks succeed",
      "strong_controls": "15% of attacks succeed",
      "advanced_controls": "5% of attacks succeed",
      "step_3": "Multiply: LEF = TEF × Success Rate"
    },
    "minimum": "Best case (e.g., 0.1 = once every 10 years)",
    "most_likely": "Most realistic with your controls (e.g., 0.5 = once every 2 years)",
    "maximum": "Worst case (e.g., 2 = twice per year)"
  }
}
```

## Control Effectiveness to Vulnerability Mapping

### Vulnerability Percentage Guidelines

Based on industry research and FAIR practitioner guidance:

| Control Maturity | Vulnerability | Description | Control Examples |
|-----------------|---------------|-------------|------------------|
| **Minimal** | 60-80% | Very weak resistance | Basic AV only |
| **Basic** | 35-50% | Weak resistance | AV + email filtering |
| **Intermediate** | 10-20% | Moderate resistance | EDR + training + backups |
| **Advanced** | 3-8% | Strong resistance | EDR + SIEM + MFA + immutable backups |
| **Mature** | 1-3% | Very strong resistance | Full security program + threat hunting |

### Threat-Specific Adjustments

Different threats have different vulnerability patterns:

#### Ransomware
- **Minimal controls:** 70% (ransomware is highly effective)
- **Basic controls:** 40%
- **Intermediate:** 15%
- **Advanced:** 5%

#### Phishing/Social Engineering
- **Minimal controls:** 60% (user behavior varies)
- **Basic controls:** 30%
- **Intermediate:** 10%
- **Advanced:** 3%

#### DDoS
- **Minimal controls:** 90% (hard to stop without specific controls)
- **Basic controls:** 70%
- **Intermediate:** 30%
- **Advanced:** 10%

#### Insider Threat
- **Minimal controls:** 80% (insiders bypass perimeter)
- **Basic controls:** 50%
- **Intermediate:** 20%
- **Advanced:** 8%

## Implementation Plan

### Phase 1: Update Question Generator Prompt (ai_question_generator_v214.py)

**Changes needed:**

1. **Update system prompt** to instruct Claude to generate TEF + Control questions instead of direct LEF
2. **Add vulnerability mapping** to control choices
3. **Include calculation guidance** in the JSON structure

### Phase 2: Update Flask App (flask_oic_v215.py)

**Changes needed:**

1. **Modify analyze endpoint** to:
   - Accept both TEF inputs and vulnerability (from controls)
   - Calculate LEF = TEF × Vulnerability
   - Pass both TEF and LEF to simulation

2. **Update UI rendering** to:
   - Show the decomposition clearly
   - Display: "TEF → Vulnerability → LEF"
   - Provide real-time calculation preview

### Phase 3: Update Templates

**questionnaire_chat.html changes:**

1. Add calculation preview widget
2. Show vulnerability percentage when control is selected
3. Display LEF calculation formula

### Phase 4: Update Chat Assistant Guidance

**Chat assistant should help users understand:**

- Difference between TEF (attempts) and LEF (successes)
- How controls reduce vulnerability
- Examples specific to their threat/industry

## Validation Against Open FAIR

This approach aligns with Open FAIR Standard (O-RA 2.0, O-RT 3.0):

✅ **Decomposes LEF correctly:** LEF = TEF × Vulnerability  
✅ **Makes vulnerability explicit:** Controls map to resistance/susceptibility  
✅ **Improves user comprehension:** Separate questions for each component  
✅ **Maintains PERT estimation:** Still uses 3-point estimates for TEF  
✅ **Supports FAIR certification:** Teaches correct FAIR thinking  

## Benefits

### For Users
1. **Clearer mental model:** Separate "how often attacked" from "how often harmed"
2. **Better control assessment:** See direct impact of security investments
3. **More accurate estimates:** Easier to think about components separately
4. **Educational value:** Learn proper FAIR methodology

### For Risk Analysis
1. **Higher fidelity:** Captures the true relationship between threats and controls
2. **Sensitivity analysis:** Can vary TEF and Vulnerability independently
3. **Control ROI:** Show how control improvements reduce LEF
4. **Audit trail:** Clear rationale for LEF estimates

## Recommended Next Steps

1. ✅ **Review this proposal** - Confirm approach aligns with your vision
2. **Pilot implementation** - Update one threat scenario as proof of concept
3. **Test with users** - Validate that decomposition improves comprehension
4. **Full rollout** - Update all question templates
5. **Documentation** - Add FAIR methodology guide to help system

## Open Questions

1. **Should we always decompose, or make it optional?**
   - Recommendation: Always decompose (better accuracy)
   - Alternative: Offer "simple" vs "detailed" mode

2. **How to handle custom scenarios?**
   - User provides: Threat description + rough TEF
   - LLM suggests: Appropriate vulnerability based on described controls
   - User adjusts: Both TEF and vulnerability if needed

3. **Should controls question come before or after TEF?**
   - Recommendation: Controls FIRST (sets context for TEF estimation)
   - Rationale: Users think "Given my controls, how often am I attacked?"

4. **Allow manual LEF override?**
   - Recommendation: YES - show calculated LEF but allow override
   - Rationale: Users may have empirical data that trumps calculation

## References

1. **FAIR Institute Blog:** "FAIR Terminology 101 – Risk, Threat Event Frequency and Vulnerability"
   - URL: https://www.fairinstitute.org/blog/fair-terminology-101-risk-threat-event-frequency-and-vulnerability
   - Key point: TEF vs LEF is most-missed certification question

2. **Open FAIR Standard O-RT 3.0** - Risk Taxonomy (November 2020)
   - Defines: LEF = TEF × Vulnerability (also called "Susceptibility")

3. **RiskLens FAIR Controls Analysis**
   - URL: https://www.risklens.com/resource-center/blog/how-it-auditors-evaluate-the-effectiveness-of-controls-with-risk-quantification
   - Key point: Controls measured by their effect on vulnerability percentage

4. **User feedback:** Real-world example of APT targeting with 10% success rate demonstrating the need for decomposition

---

## Example: Complete Question Flow

### Scenario: Healthcare Ransomware

**Q1: Controls** *(Sets vulnerability)*
```
"What ransomware defenses do you have?"
→ User selects: "Intermediate" (EDR + training + backups)
→ Vulnerability = 15%
```

**Q2: Threat Frequency** *(Estimates TEF)*
```
"How often do ransomware groups attempt to attack healthcare orgs like yours?"
→ User estimates: Min=2, Most Likely=6, Max=12 attempts/year
→ TEF = (2, 6, 12)
```

**Q3: Calculated LEF** *(Auto-computed, editable)*
```
CALCULATION:
  TEF (Most Likely) = 6 attacks/year
  × Vulnerability = 15% (from your controls)
  = LEF = 0.9 successful breaches/year

INTERPRETATION:
  "With your current controls, you can expect approximately
   1 successful ransomware breach every 13 months"

[Accept] [Adjust Values]
```

**Q4: Loss Magnitude**
```
"What would be the financial impact per successful breach?"
→ Standard PERT estimate
```

**Result:** Risk = LEF × LM with full traceability

---

**Document prepared:** 2025-01-22  
**Status:** PROPOSAL - Awaiting approval for implementation
