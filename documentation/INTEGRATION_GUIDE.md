# OpenImpactCascade - Scatter Plot Visualization Integration Guide

## Overview
This guide shows you how to integrate interactive scatter plot visualizations with control sliders into your existing Flask app.

## Files You Need

### 1. Modified Simulation File
**File**: `simulation_enhanced_with_samples.py`  
**What changed**: Now returns raw sample data (`lef`, `lm`, `annual_loss`) in addition to summary statistics

**Location in your project**: Replace your current `simulation_enhanced.py`

### 2. Updated Results Template  
**File**: `results.html` (to be created - see below)  
**What it does**: Displays interactive charts with control sliders

**Location in your project**: `templates/results.html`

## Installation Steps

### Step 1: Update Simulation File

```bash
# Backup your current simulation file
cp simulation_enhanced.py simulation_enhanced_BACKUP.py

# Replace with the new version that includes sample data
cp simulation_enhanced_with_samples.py simulation_enhanced.py
```

**What this changes**: The `run_monte_carlo()` function now returns:
```python
{
    'mean': ...,
    'std': ...,
    # ... all existing fields ...
    'samples': {
        'lef': [list of 10,000 frequency values],
        'lm': [list of 10,000 magnitude values],
        'annual_loss': [list of 10,000 annual loss values]
    }
}
```

### Step 2: No Flask App Changes Needed!

Your existing Flask app in `flask_app_chat_v21_rag_enhanced.py` already:
- Calls `run_monte_carlo()` correctly ✓
- Passes results to `render_template('results.html', results=results)` ✓
- Handles the recalculate endpoint ✓

**No code changes needed** - the new simulation file is backward compatible.

### Step 3: Update Results Template

Create or replace `templates/results.html` with the new template that includes:
- Interactive control sliders
- Frequency distribution line chart  
- Magnitude distribution line chart
- Real-time updates when controls are applied

## Testing

1. Start your Flask app:
```bash
python flask_app_chat_v21_rag_enhanced.py
```

2. Generate a questionnaire and complete it

3. View results - you should now see:
   - Stats banner at top
   - Control sliders (Likelihood & Impact reduction)
   - Two line charts that update when controls are applied

## How It Works

1. **Data Flow**: 
   ```
   simulation_enhanced.py 
   → returns results with samples 
   → Flask passes to template 
   → JavaScript creates charts
   ```

2. **Control Sliders**:
   - User adjusts sliders
   - JavaScript applies reductions to sample data
   - Charts rebuild with new distributions
   - Summary statistics recalculate
   - All happens client-side (no server calls)

3. **Performance**:
   - Sample data is ~1MB for 10,000 simulations
   - Charts render instantly
   - Control updates are real-time

## Troubleshooting

### Issue: "samples" key not found
**Solution**: Make sure you're using `simulation_enhanced_with_samples.py` as your `simulation_enhanced.py`

### Issue: Charts not rendering
**Solution**: Check browser console for errors. Ensure Chart.js CDN is loading:
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
```

### Issue: Control sliders not working
**Solution**: Check that JavaScript at bottom of template is loading. View page source to verify `{{ results.samples.lef | tojson }}` is populated with data.

## What Your Users See

1. **Top Stats Banner**: Typical Year, Expected Loss, Bad Year, Catastrophic
2. **Control Sliders**: 
   - Likelihood Reduction (0-100%)
   - Impact Reduction (0-100%)
   - Apply/Reset buttons
3. **Results Panel**: Shows new risk levels after controls applied
4. **Frequency Chart**: Line chart showing how often events happen
5. **Magnitude Chart**: Line chart showing loss severity distribution

## Benefits

- **Intuitive**: Users see all 10,000 simulations as data points
- **Interactive**: Sliders let users model "what-if" scenarios
- **Educational**: Charts show why median < mean (right-skewed distribution)
- **Fast**: All calculations happen in browser
- **Professional**: Clean, modern UI that matches OpenImpactCascade branding

## Next Steps

Once integrated, consider:
1. Adding preset control scenarios ("MFA package", "Backup suite", etc.)
2. Saving control scenarios to user's account
3. Exporting charts as images
4. Adding comparison view (before/after side-by-side)

