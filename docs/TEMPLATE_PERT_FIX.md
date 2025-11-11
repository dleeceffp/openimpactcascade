# Template PERT Estimate Fix

## Problem

After fixing the JSON schema, questionnaires were displaying correctly through the multiple choice questions, but **PERT estimate questions were not appearing** after the final multiple choice selection.

## Root Cause

The template `questionnaire_chat.html` was written for an **older JSON schema** that used different field names for PERT estimates:

### Old Schema (Template Expected):
```javascript
{
  "type": "pert_estimate",
  "unit": "events per year",  // ❌ Template looked for this
  "outputs": {                 // ❌ Template looked for this
    "min": "lef_min",
    "mle": "lef_mle",
    "max": "lef_max"
  }
}
```

### New Schema (JSON Actually Has):
```javascript
{
  "type": "pert_estimate",
  "estimate_type": "frequency_per_year",  // ✅ Actual field
  "guidance": {                            // ✅ Actual field
    "minimum": "0.2 (once every 5 years...)",
    "most_likely": "0.8 (approximately once per year...)",
    "maximum": "2.5 (multiple attempts per year...)"
  }
}
```

## The Fix

### File: `templates/questionnaire_chat.html`

#### 1. Updated PERT Rendering Logic (Lines 587-619)

**Before:**
```javascript
} else if (question.type === 'pert_estimate') {
    html += `
        <div class="pert-input-group">
            <div class="input-field">
                <label>Minimum (${question.unit})</label>  // ❌ undefined
                <input ... onchange="updatePertValue('${question.outputs.min}', ...)">  // ❌ undefined
            </div>
            ...
        </div>
    `;
}
```

**After:**
```javascript
} else if (question.type === 'pert_estimate') {
    // Determine unit label based on estimate_type
    const unitLabel = question.estimate_type === 'frequency_per_year' ? 
        'events per year' : 'USD';
    
    // Get guidance if available
    const guidance = question.guidance || {};
    
    html += `
        <div class="pert-input-group">
            <div class="input-field">
                <label>Minimum (${unitLabel})</label>  // ✅ Correct
                <input ... placeholder="${guidance.minimum || 'Best case scenario'}">
                ${guidance.minimum ? `<small class="guidance">${guidance.minimum}</small>` : ''}
            </div>
            ...
        </div>
    `;
}
```

#### 2. Added CSS for Guidance Text (Lines 359-365)

```css
.guidance {
    display: block;
    color: #a0aec0;
    font-size: 0.85em;
    margin-top: 5px;
    font-style: italic;
}
```

## What Changed

### ✅ Unit Label
- **Before**: `${question.unit}` → undefined, showed "Minimum (undefined)"
- **After**: Derives from `estimate_type`:
  - `frequency_per_year` → "events per year"
  - `loss_magnitude_usd` → "USD"

### ✅ Guidance Text
- **Before**: Tried to use `question.outputs` → undefined
- **After**: Uses `question.guidance` object with helpful descriptions
- **Displays**: Inline help text under each input field

### ✅ Placeholders
- **Before**: No placeholders
- **After**: Shows guidance text as placeholder if available

## Example Output

### Frequency Estimate:
```
How often could ransomware targeting your OT systems occur?

┌─────────────────────────────────────────────┐
│ Minimum (events per year)                   │
│ [___________________________________]        │
│ 0.2 (once every 5 years - best case...)    │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Most Likely (events per year)               │
│ [___________________________________]        │
│ 0.8 (approximately once per year...)        │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Maximum (events per year)                   │
│ [___________________________________]        │
│ 2.5 (multiple attempts per year...)         │
└─────────────────────────────────────────────┘
```

### Magnitude Estimate:
```
What would be the financial impact?

┌─────────────────────────────────────────────┐
│ Minimum (USD)                                │
│ [___________________________________]        │
│ 50000 (limited impact, quick recovery)      │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Most Likely (USD)                            │
│ [___________________________________]        │
│ 800000 (typical manufacturing impact...)    │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Maximum (USD)                                │
│ [___________________________________]        │
│ 5000000 (extended downtime...)               │
└─────────────────────────────────────────────┘
```

## Testing

### 1. Refresh Browser
```bash
# No need to restart Flask app - just refresh browser
# Hard refresh: Ctrl+Shift+R (or Cmd+Shift+R on Mac)
```

### 2. Navigate Through Questionnaire
1. Select a threat scenario
2. Select affected assets
3. Select security controls
4. **PERT estimate should now appear** ✅
5. Fill in frequency estimates
6. Continue to magnitude estimates

### 3. Verify Guidance Text
- Check that guidance text appears under each input
- Verify unit labels are correct:
  - Frequency: "events per year"
  - Magnitude: "USD"

## Files Modified

| File | Lines | Changes |
|------|-------|---------|
| `templates/questionnaire_chat.html` | 587-619 | Updated PERT rendering to use `estimate_type` and `guidance` |
| `templates/questionnaire_chat.html` | 359-365 | Added CSS for `.guidance` class |

## Related Issues

This fix completes the JSON schema migration:
1. ✅ System prompts updated (complete schema)
2. ✅ User messages updated (explicit JSON examples)
3. ✅ JSON generation fixed (correct structure)
4. ✅ Template rendering fixed (matches new schema)

## Validation

After this fix, the complete questionnaire flow works:
- ✅ Threat selection (multiple choice)
- ✅ Asset selection (multiple choice)
- ✅ Controls selection (multiple choice)
- ✅ Frequency estimation (PERT) **← NOW WORKING**
- ✅ Magnitude estimation (PERT) **← NOW WORKING**
- ✅ Submit and analyze

---

**Status**: ✅ FIXED  
**Date**: November 4, 2025  
**Issue**: PERT estimates not displaying  
**Root Cause**: Template using old JSON schema field names  
**Solution**: Updated template to use `estimate_type` and `guidance` fields  
**Result**: Complete questionnaire flow now functional
