# Layered Controls Toggle Feature

| Field | Value |
|-------|-------|
| **Document ID** | OIC-DOC-LCTL-001 |
| **Status** | Implemented (beta) |
| **Date** | 2026-06-13 |
| **Supersedes** | `documentation/historical/LAYERED_CONTROLS_FEATURE.md` |

---

## Overview

The layered controls toggle allows users to indicate that secondary defensive controls are in place beyond their primary control tier selection. When enabled, it applies a conservative 25% vulnerability reduction to the FAIR calculation, producing a lower Loss Event Frequency (LEF) estimate that better reflects a defense-in-depth posture.

The feature is transparent about its limitations: a single fixed adjustment factor cannot capture the full complexity of multi-layer control interactions, and the UI says so clearly. Rather than using this limitation as sales friction, the messaging invites users to share what a more precise model would need to do — feeding the feature roadmap based on actual user need.

---

## User Experience

### When It Appears

After the user selects a control strength option (e.g., "Basic — Antivirus + some email security"), a toggle appears below the selected choice.

### Visual Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ ☐ Secondary/layered controls in place?                          │
│   Examples: Network segmentation, offline backups, EDR/XDR,     │
│   SIEM, incident response plan, security awareness training     │
│                                                                  │
│   ✓ Reduces vulnerability by 25% (simplified single-factor      │
│     model)                                                       │
│                                                                  │
│   ⚠ Note: This is a basic adjustment. A more precise model      │
│     would score each control layer individually. If that        │
│     matters for your use case, we'd like to hear about it.      │
│     [Share feedback →]                                          │
│                                                                  │
│ Adjusted Vulnerability: 34% (reduced from 45%)                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technical Implementation

### Variables

```javascript
let vulnerability = null;           // Current vulnerability (may be adjusted)
let baseVulnerability = null;       // Original vulnerability before adjustment
let layeredControlsApplied = false; // Tracking flag
```

### Functions

#### `showLayeredControlsToggle(selectedElement)`
Displays the toggle UI after a control choice is made. Removes any existing toggle instance before inserting a new one to avoid duplication when the user changes their selection.

#### `applyLayeredControlsAdjustment(isChecked)`
- Applies 25% reduction when checked: `vulnerability = baseVulnerability * 0.75`
- Reverts to base value when unchecked: `vulnerability = baseVulnerability`
- Updates the displayed adjusted value
- Sends adjustment data to backend via `updateBackendContext()`

### Adjustment Factor

**Constant**: `ADJUSTMENT_FACTOR = 0.75` (25% reduction)

**Rationale**: Conservative enough to be credible, large enough to have a material effect on the LEF output, and simple enough that users can verify it by inspection. The fixed factor is an acknowledged simplification of the underlying AND-gate probability math — see the `about_layered_controls.html` explanation page for the full mathematical background.

### Integration with LEF Calculation

The LEF calculation automatically picks up the adjusted vulnerability:

```javascript
// LEF = TEF × Vulnerability
const calc_lef_min = (tef_min * vuln).toFixed(2);
const calc_lef_mle = (tef_mle * vuln).toFixed(2);
const calc_lef_max = (tef_max * vuln).toFixed(2);
```

If the toggle is checked with a base vulnerability of 45%:
- Adjusted vulnerability: 34% (45% × 0.75)
- LEF uses 34% throughout the simulation

---

## Impact Example

### Scenario: Healthcare Ransomware

| Condition | TEF | Vulnerability | LEF | Loss Magnitude | Expected Annual Loss |
|-----------|-----|--------------|-----|----------------|---------------------|
| Without layered controls | 1.0/yr | 45% | 0.45/yr | $50,000 | $22,500 |
| With layered controls (toggle on) | 1.0/yr | 34% | 0.34/yr | $50,000 | $17,000 |

Reduction in expected annual loss: approximately 24%.

---

## What the Feature Does Not Model

The 25% blanket adjustment is a rough heuristic. It does not account for:

- Different effectiveness rates per individual control layer
- Partial dependencies between controls (not fully independent failures)
- Attack paths that bypass specific control combinations
- Common-mode failures (correlated control failures)
- Control effectiveness variation by threat type or attacker capability

This is stated plainly in the UI. Users who need per-control precision are encouraged to share that need via the feedback link — the goal is to understand whether and how to build it, not to present it as a pre-existing product.

---

## Feature Request Messaging

The UI replaces any commercial call-to-action with a feature request prompt:

> "A more precise model would score each control layer individually. If that matters for your use case, we'd like to hear about it."

Link target: `mailto:info@impactcascade.ca?subject=Feature%20Request%3A%20Per-Control%20Effectiveness%20Scoring`

This approach:
- Respects users' time by not promoting products that don't exist yet
- Generates genuine signal about whether per-control modeling is worth building
- Maintains transparency about the tool's current state
- Rewards early users who take the time to share their perspective

---

## Backend Context Tracking

When the toggle state changes, the following is sent to the backend:

```javascript
updateBackendContext('layered_controls_adjustment', {
    applied: true/false,
    base_vulnerability: 0.45,
    adjusted_vulnerability: 0.34,
    adjustment_factor: 0.75
});
```

This data is stored in `context_storage.py` (SQLite) per session. It is used for:
- Understanding how often the feature is used
- Informing whether per-control precision is a genuine user need
- Session context for the chat assistant

---

## Design Principles

### Transparency
The feature states clearly that it is a simplified model, shows the exact adjustment factor (25%), and displays both the original and adjusted vulnerability values side by side.

### Simplicity
Single checkbox, fixed factor, binary yes/no. There is no configuration surface that would require the user to understand the underlying math to get a reasonable result.

### Honest Limitation Framing
The limitation is not a selling point for a separate product; it is a genuine description of where the model falls short. Users who need more precision are invited to say so.

### User Respect
The feature provides real, usable value (a calibrated adjustment that affects simulation output) while being honest that it is not a substitute for per-control analysis.

---

## Capability Gaps (Potential Future Work)

The following capabilities are not present in the current implementation. They are tracked here as potential future directions, not commitments. User feedback via the feature request link is the intended input to prioritization.

1. **Per-control effectiveness scoring** — Individual failure rates for each named control layer
2. **AND/OR gate modeling** — Explicit logic for parallel vs. serial control dependencies
3. **Attack path analysis** — Which control combinations a given attack scenario bypasses
4. **Scenario comparison** — Side-by-side results across different control configurations
5. **Control investment ROI** — Change in expected loss per dollar of control improvement
6. **Compliance framework mapping** — Linking control selections to NIST CSF, CIS Controls, etc.

---

## Files Modified

- `app/templates/questionnaire_chat_rationale.html`:
  - Added `baseVulnerability` and `layeredControlsApplied` variables
  - Added `showLayeredControlsToggle()` function
  - Added `applyLayeredControlsAdjustment()` function
  - Modified `selectChoice()` to trigger toggle display
  - Existing LEF calculation unchanged (uses `vulnerability` variable, which is now adjusted when toggle is active)

- `app/templates/about_layered_controls.html`:
  - Explanation page linked from the toggle UI
  - Describes the defense-in-depth principle and AND-gate mathematics
  - Replaces commercial CTA with feature request prompt

---

## Testing Checklist

- [x] Toggle appears after control selection
- [x] Checkbox can be checked and unchecked
- [x] Adjusted value displays when checked
- [x] Adjusted value hides when unchecked
- [x] LEF calculation uses adjusted vulnerability
- [x] Backend context tracking records adjustment data
- [x] Feature request link opens correctly pre-filled email
- [x] Toggle is removed and re-rendered when user changes control selection
- [x] Console logging reflects adjustments
