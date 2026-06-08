# Layered Controls Toggle Feature

## Overview

Added a strategic feature that allows users to indicate secondary/layered controls, applying a 25% vulnerability reduction while transparently acknowledging the limitation and promoting the paid Cascade Risk Modeling™ product.

## Business Strategy

### Problem Addressed
Single vulnerability numbers assume all controls fail together, oversimplifying defense-in-depth scenarios where multiple control layers exist.

### Solution Approach
- **Simple toggle**: Easy to understand and use
- **Fixed 25% reduction**: Conservative but meaningful adjustment
- **Transparent limitation**: Clear messaging that this is simplified
- **Natural upsell**: Creates pain point for precise multi-layer analysis

## User Experience

### When It Appears
After selecting a control strength option (e.g., "Basic - Antivirus + some email security"), a toggle appears below the selected choice.

### Visual Design
```
┌─────────────────────────────────────────────────────────────────┐
│ ☐ Secondary/layered controls in place?                          │
│   Examples: Network segmentation, offline backups, EDR/XDR,     │
│   SIEM, incident response plan, security awareness training     │
│                                                                  │
│   ✓ Reduces vulnerability by 25% (simplified single-factor      │
│     model)                                                       │
│                                                                  │
│   ⚠ Note: This is a basic adjustment. For precise multi-layer  │
│     control effectiveness and attack path analysis, consider    │
│     Cascade Risk Modeling™ [Contact Sales →]                    │
│                                                                  │
│ Adjusted Vulnerability: 34% (reduced from 45%)                  │
└─────────────────────────────────────────────────────────────────┘
```

## Technical Implementation

### Variables Added
```javascript
let vulnerability = null;           // Current vulnerability (may be adjusted)
let baseVulnerability = null;       // Original vulnerability before adjustment
let layeredControlsApplied = false; // Tracking flag
```

### Functions Added

#### `showLayeredControlsToggle(selectedElement)`
- Displays toggle UI after control selection
- Includes examples, adjustment explanation, and upsell messaging
- Removes any existing toggle before showing new one

#### `applyLayeredControlsAdjustment(isChecked)`
- Applies 25% reduction when checked: `vulnerability = baseVulnerability * 0.75`
- Reverts to original when unchecked: `vulnerability = baseVulnerability`
- Updates UI to show adjusted value
- Sends tracking data to backend via `updateBackendContext()`

### Adjustment Factor

**Constant**: `ADJUSTMENT_FACTOR = 0.75` (25% reduction)

**Rationale**:
- Conservative enough to be credible
- Large enough to have material impact on results
- Round number that's easy to understand
- Creates meaningful differentiation for upsell

### Integration with Calculations

The LEF calculation automatically uses the adjusted vulnerability:

```javascript
// LEF = TEF × Vulnerability
const calc_lef_min = (tef_min * vuln).toFixed(2);
const calc_lef_mle = (tef_mle * vuln).toFixed(2);
const calc_lef_max = (tef_max * vuln).toFixed(2);
```

If layered controls are checked:
- Base vulnerability: 45%
- Adjusted vulnerability: 34% (45% × 0.75)
- LEF calculation uses 34%

## Impact Examples

### Scenario: Healthcare Ransomware

**Without Layered Controls**:
- TEF: 1.0 attempts/year
- Vulnerability: 45%
- LEF: 0.45 successes/year
- Loss Magnitude: $50,000
- **Expected Annual Loss**: $22,500

**With Layered Controls** (toggle checked):
- TEF: 1.0 attempts/year
- Vulnerability: 34% (reduced from 45%)
- LEF: 0.34 successes/year
- Loss Magnitude: $50,000
- **Expected Annual Loss**: $17,000

**Reduction**: ~24% lower expected loss

## Upsell Messaging

### Key Phrases Used

1. **"Simplified single-factor model"**
   - Sets expectation of limitation
   - Implies existence of multi-factor alternative

2. **"Basic adjustment"**
   - Acknowledges imprecision
   - Suggests more sophisticated options exist

3. **"For precise multi-layer control effectiveness and attack path analysis"**
   - Describes capability gap
   - Hints at features available in paid product

4. **"Cascade Risk Modeling™"**
   - Branded paid product name
   - Creates clear upgrade path

5. **"Contact Sales →"**
   - Direct call-to-action
   - Email link: `sales@openimpactcascade.com`

## Value Proposition Comparison

| Free Tool | Cascade Risk Modeling™ (Paid) |
|-----------|-------------------------------|
| Single vulnerability number | Per-control effectiveness scoring |
| 25% blanket adjustment | Precise attack path probability |
| Assumes serial failures | Models AND/OR logic gates |
| One scenario at a time | Multi-scenario comparisons |
| Simplified calculation | Monte Carlo on attack trees |
| Toggle checkbox | Visual attack tree builder |
| Fixed adjustment factor | Custom control parameters |
| No dependency modeling | Full dependency analysis |

## Backend Context Tracking

When toggle is changed, sends to backend:

```javascript
updateBackendContext('layered_controls_adjustment', {
    applied: true/false,
    base_vulnerability: 0.45,
    adjusted_vulnerability: 0.34,
    adjustment_factor: 0.75
});
```

This data is stored in SQLite and can be used for:
- Product analytics
- Feature usage tracking
- Upsell opportunity identification
- User behavior analysis

## Design Principles

### 1. Transparency
- Clearly states "simplified model"
- Shows exact adjustment (25%)
- Displays both base and adjusted values

### 2. Simplicity
- Single checkbox (not multi-level dropdown)
- Fixed factor (not user-configurable)
- Binary choice (yes/no secondary controls)

### 3. Strategic Limitation
- Intentionally simplified to create demand
- Leaves obvious capability gaps
- Makes case for paid product naturally

### 4. User Respect
- Provides real value (25% adjustment)
- Doesn't hide limitations
- Offers clear upgrade path

## Future Enhancements (Paid Product)

Potential Cascade Risk Modeling™ features:

1. **Attack Tree Builder**
   - Visual drag-and-drop interface
   - AND/OR gate logic
   - Multi-stage attack modeling

2. **Per-Control Effectiveness**
   - Individual success/failure rates
   - Control dependencies
   - Failure mode analysis

3. **Scenario Comparison**
   - Side-by-side comparisons
   - Control investment ROI
   - Mitigation strategy optimization

4. **Advanced Distributions**
   - Control-specific distributions
   - Correlated failures
   - Time-varying effectiveness

5. **Compliance Integration**
   - Map controls to frameworks
   - Gap analysis
   - Evidence collection

## Testing Checklist

- [x] Toggle appears after control selection
- [x] Checkbox can be checked/unchecked
- [x] Adjusted value displays when checked
- [x] Adjusted value hides when unchecked
- [x] LEF calculation uses adjusted vulnerability
- [x] Backend context tracking works
- [x] "Contact Sales" link works
- [x] Toggle removed when selecting different control
- [x] Console logging shows adjustments
- [x] Visual styling is professional

## Metrics to Track

1. **Usage Rate**: % of users who check the toggle
2. **Upsell Clicks**: Clicks on "Contact Sales" link
3. **Impact on Results**: Average change in expected loss
4. **Time to Decision**: How long users consider toggle
5. **Correlation**: Toggle usage vs. contact rate

## Files Modified

- `app/templates/questionnaire_chat_rationale.html`:
  - Added `baseVulnerability` and `layeredControlsApplied` variables
  - Added `showLayeredControlsToggle()` function
  - Added `applyLayeredControlsAdjustment()` function
  - Modified `selectChoice()` to trigger toggle display
  - Existing LEF calculation automatically uses adjusted value

---

**Status**: ✅ Implemented  
**Version**: v221-layered-controls  
**Date**: November 2025  
**Strategic Goal**: Create natural upsell path to Cascade Risk Modeling™
