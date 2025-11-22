# AI-Assisted Risk Scenario Refinement Feature

## Overview

This feature addresses a common user pain point: unskilled users struggle to articulate risk concerns in crisp, measurable terms within character limits. The two-phase AI-assisted approach helps users transform verbose narratives into clear, actionable risk scenarios.

---

## Problem Statement

**Original Issue:**
- `risk_scenario` field limited to 200 characters
- Users provide verbose, unclear descriptions
- Truncation loses important context
- Users don't know how to write "FAIR-appropriate" scenarios

**User Pain Point:**
> "I'm worried about ransomware because our backups are on the same network and we heard about hospitals getting hit. We don't have great monitoring and I'm not sure if our staff would click on phishing emails. Also, we use third-party vendors who might have access to our systems..."

This gets truncated to: "I'm worried about ransomware because our backups are on the same network and we heard about hospitals getting hit. We don't have great monitoring and I'm not sure if our staff would click on..."

---

## Solution: Two-Phase AI Refinement

### Phase 1: Narrative Collection
**User Experience:**
1. User sees a large textarea (2000 char limit)
2. Friendly prompt: "Describe Your Risk Concern"
3. Helpful tips guide them to explain:
   - What type of attack worries them
   - What systems/data might be affected
   - Why they're concerned
   - Similar incidents they've heard about

**Example Input:**
```
We're worried about ransomware because our backups are on the same network 
and we heard about hospitals getting hit. We don't have great monitoring 
and I'm not sure if our staff would click on phishing emails. Also, we 
use third-party vendors who might have access to our systems.
```

### Phase 2: AI Refinement & Selection
**User Experience:**
1. User clicks "✨ Help Me Refine This Into a Clear Scenario"
2. AI analyzes narrative (3-5 seconds)
3. System presents 3-5 crisp scenario options with:
   - Clear, actionable text (50-150 chars)
   - Rationale explaining why this captures their concern
   - Recommended option highlighted
   - Key concerns identified

**Example Output:**
```json
{
  "scenarios": [
    {
      "text": "Ransomware attack on backup systems",
      "rationale": "User mentioned concerns about backups on same network"
    },
    {
      "text": "Phishing campaign targeting employee credentials",
      "rationale": "User expressed uncertainty about staff clicking phishing emails"
    },
    {
      "text": "Supply chain attack via third-party vendor access",
      "rationale": "User mentioned third-party vendors with system access"
    }
  ],
  "key_concerns": [
    "Backup vulnerability",
    "Limited monitoring",
    "User awareness gaps",
    "Third-party access"
  ],
  "recommended_scenario": 0
}
```

4. User selects the scenario that best matches their intent
5. Selected scenario becomes the `risk_scenario` for questionnaire generation

---

## Technical Implementation

### Backend: Flask Endpoint

**New Route:** `/refine_scenario` (POST)

```python
@app.route('/refine_scenario', methods=['POST'])
def refine_scenario():
    """Refine a verbose user narrative into crisp risk scenario options using AI."""
    # Accepts: narrative, industry, region
    # Returns: JSON with scenarios, key_concerns, recommended_scenario
```

**Key Features:**
- User tracking integration (logs API call)
- 2000 character limit on narrative
- Context-aware (uses industry/region)
- JSON extraction from AI response
- Error handling with user-friendly messages

**API Call Tracking:**
```python
tracker.log_api_call(
    user_id=user_id,
    hashed_user_id=hashed_user_id,
    api_type="scenario_refinement",
    model="claude-sonnet-4-20250514",
    request_id=response.id,
    metadata={"industry": industry, "region": region, "narrative_length": len(narrative)}
)
```

### Frontend: Two-Phase UI

**Phase 1 Elements:**
- `#narrativePhase` - Container for narrative input
- `#risk_narrative` - Textarea (2000 chars)
- `#refineBtn` - Trigger refinement
- `#refiningIndicator` - Loading state

**Phase 2 Elements:**
- `#scenarioPhase` - Container for scenario selection (hidden initially)
- `#scenarioOptions` - Dynamic scenario cards
- `.scenario-option` - Individual scenario cards
- `.scenario-option.recommended` - Highlighted recommended option
- `.scenario-option.selected` - User's selection
- `.key-concerns` - Identified concerns box

**JavaScript Functions:**
- `refineScenario()` - AJAX call to backend
- `displayScenarioOptions(data)` - Render scenario cards
- `selectScenario(text, index)` - Handle user selection
- `backToNarrative()` - Return to phase 1

### Fallback Behavior

**If user skips refinement:**
- Form submission auto-populates `risk_scenario` with first 200 chars of narrative
- Allows users to proceed without AI assistance
- Maintains backward compatibility

---

## User Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User enters verbose narrative (up to 2000 chars)         │
│    "We're worried about ransomware because..."              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. User clicks "Help Me Refine This Into a Clear Scenario" │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. AI analyzes narrative (3-5 seconds)                      │
│    - Identifies key concerns                                │
│    - Generates 3-5 crisp scenarios                          │
│    - Recommends best option                                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. User sees scenario options                               │
│    ⭐ Recommended: "Ransomware attack on backup systems"    │
│    ○ "Phishing campaign targeting employees"               │
│    ○ "Supply chain attack via vendor access"               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. User selects scenario OR goes back to edit              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Generate questionnaire with refined scenario             │
└─────────────────────────────────────────────────────────────┘
```

---

## Benefits

### For Unskilled Users
✅ **No technical knowledge required** - Write in plain language  
✅ **Guided by examples** - Tips help structure thoughts  
✅ **AI does the translation** - Converts narrative to crisp scenarios  
✅ **Multiple options** - Choose the best fit  
✅ **Learn by example** - See how experts phrase scenarios

### For Skilled Users
✅ **Optional feature** - Can skip refinement if confident  
✅ **Faster iteration** - Quickly explore multiple scenario angles  
✅ **Validation** - Confirm their scenario is well-structured

### For the System
✅ **Better input quality** - Crisp scenarios improve questionnaire generation  
✅ **User tracking** - All refinement calls logged for abuse prevention  
✅ **Cost-effective** - Small API call (~$0.01) prevents poor questionnaires  
✅ **Backward compatible** - Existing flow still works

---

## Cost Analysis

**Per Refinement:**
- Input tokens: ~500-800 (prompt + narrative)
- Output tokens: ~300-500 (scenarios + rationale)
- Estimated cost: **$0.01-0.02 per refinement**

**Value Proposition:**
- Prevents poor questionnaires that waste larger generation calls ($0.05-0.15)
- Improves user satisfaction and reduces support burden
- Small upfront cost for better downstream results

---

## Testing Scenarios

### Test Case 1: Verbose Narrative
**Input:**
```
I'm really worried about our company getting hacked. We have customer data 
and financial records. I heard about companies getting ransomware and having 
to pay millions. We don't have a security team, just IT. Our employees work 
from home and use their own devices sometimes. I'm not sure if we're doing 
enough to protect ourselves.
```

**Expected Output:**
- Scenario 1: "Ransomware attack on customer database"
- Scenario 2: "Data breach via compromised employee device"
- Scenario 3: "Business Email Compromise targeting finance"
- Key concerns: Customer data exposure, Remote work risks, Limited security resources

### Test Case 2: Technical User
**Input:**
```
Concerned about SQL injection vulnerabilities in our legacy web application. 
We have parameterized queries in most places but some dynamic SQL in reporting 
modules. WAF is in place but not tuned for our app.
```

**Expected Output:**
- Scenario 1: "SQL injection on legacy web application"
- Scenario 2: "SQL injection in reporting modules"
- Key concerns: Legacy code, Dynamic SQL, WAF configuration

### Test Case 3: Industry-Specific
**Input:**
```
Healthcare org worried about HIPAA violations. We have patient records in 
multiple systems. Some staff access records they shouldn't. We've had close 
calls with data going to wrong patients.
```

**Expected Output:**
- Scenario 1: "Unauthorized access to patient records"
- Scenario 2: "Data disclosure to wrong patient"
- Key concerns: HIPAA compliance, Access control, Multiple systems

---

## Future Enhancements

### Phase 3: Iterative Refinement
- Allow users to edit selected scenario
- AI suggests improvements to user edits
- Learn from user selections to improve recommendations

### Enhanced Context
- Consider organization size in refinement
- Use historical scenarios from same industry
- Suggest related compliance requirements

### Multi-Language Support
- Accept narratives in multiple languages
- Translate to English for processing
- Return scenarios in user's language

---

## Files Modified

1. **`flask_app_chat.py`**
   - Added `/refine_scenario` endpoint
   - Integrated user tracking
   - JSON extraction logic

2. **`templates/generate_custom.html`**
   - Two-phase UI (narrative → scenarios)
   - CSS for scenario cards and states
   - JavaScript for AJAX and phase transitions

---

## Deployment Notes

**No additional dependencies required** - Uses existing Anthropic API client

**Environment variables:** Same as existing (ANTHROPIC_API_KEY)

**Backward compatible:** Existing custom scenario flow still works

**User tracking:** All refinement calls logged to `./logs/api_calls/`

---

## Success Metrics

**User Satisfaction:**
- % of users who use refinement feature
- % who select recommended scenario
- % who go back to edit narrative

**Quality Improvement:**
- Compare questionnaire quality (refined vs. non-refined)
- Measure scenario clarity (length, specificity)
- Track generation success rate

**Cost Efficiency:**
- Refinement cost vs. questionnaire generation cost
- Reduction in failed generations
- User time saved

---

## Support & Troubleshooting

### Common Issues

**"Failed to refine scenario"**
- Check ANTHROPIC_API_KEY is set
- Verify API call logs in `./logs/api_calls/`
- Check browser console for errors

**"Please select an industry and region first"**
- User must fill industry/region before refinement
- Validation prevents context-less refinement

**Scenarios don't match narrative**
- AI may need more context
- User can go back and add more details
- Can skip refinement and use narrative directly

---

**Version:** 1.0.0  
**Date:** October 2025  
**Status:** Production Ready
