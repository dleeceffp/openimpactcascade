# OIC Corrective Instruction — Loss-Magnitude Severity Recalibration

**Target agent:** Windsurf (Claude)
**Files in scope:** `simulation.py`, `main.py` — no other files.
**Change class:** Corrective + additive. Function **signatures and call sites are unchanged**. **No new env flags.**
**Status:** `[REVIEW]` — all acceptance tests in §6 must pass and a human must confirm the §5 figures before merge.

---

## 1. Problem

During the FAIR probability work, `generate_lognormal_samples` was re-tuned to treat `max_val` as the ~85th percentile and deliberately let the tail run past it, and the prior max-loss failsafe was removed. The current formula (`sigma = (ln(p85) - ln(mode)) / 1.2`, `mu = ln(mode) + sigma**2`) anchors the **mode** but drives the median and mean far above it.

Worked example, production inputs `min=$2M, most_likely=$8M, max=$50M`:

- mode preserved at **$8M**
- median ≈ **$123M** (≈15× the mode)
- mean ≈ **$545M**
- the user's `$50M` max lands at ≈ the **30th percentile** of severity (i.e. ~70% of modeled single events exceed the stated worst case)

Through the `/analyze` roll-up this yielded mean annual loss ≈ **$68M**, median ≈ **$13.6M**, p95 ≈ **$248M** for a 1-in-10-year scenario — roughly 30–60× expected.

Two distinct defects:

1. **Severity miscalibration** in `generate_lognormal_samples`.
2. **Model inconsistency:** `/analyze` (main.py:1234) omits `compound_mode`, so it defaults to the **product** model, while `/recalculate` (main.py:1342) passes `compound_mode=OIC_MC_COMPOUND` (default ON, the **compound** model). The two screens use different aggregation models, so figures jump discontinuously the first time a user moves a control.

---

## 2. Decisions (confirmed — do not relitigate)

1. Keep lognormal. Calibrate it the actuarial / Hubbard–Seiersen way: interpret the user's **low and high as a 90% confidence interval** (5th and 95th percentiles).
2. **Most-likely is advisory** — it must NOT enter the calibration. Rationale: preserve the familiar small/medium/large input model; adoption over absolute math defensibility. (A future rev may warn when most-likely and the fitted median diverge beyond a threshold — explicitly out of scope here.)
3. **Unify** every generation entry point on the compound (collective-risk) model so behavior is identical no matter which path the user takes.
4. Tail control comes from the calibration itself (p99 ≈ 2× max for typical spreads). The enterprise-value policy-limit cap is a **separate, later change** — do not add it in this task.

---

## 3. Change 1 — `simulation.py`: replace the body **and docstring** of `generate_lognormal_samples`

The existing docstring asserts the old (wrong) "tail exceeds max is intentional" design and must be replaced too, so the file stays self-documenting for audit. Keep the existing `def generate_lognormal_samples(min_val, mode_val, max_val, n_samples):` line exactly as-is. Replace everything from the docstring through the `return` with:

```python
def generate_lognormal_samples(min_val, mode_val, max_val, n_samples):
    """
    Generate lognormal severity samples calibrated from a 90% confidence interval.

    Method: Hubbard/Seiersen calibrated-estimate approach, standard in cyber-risk
    quantification and consistent with actuarial loss-severity fitting. The
    expert's low/high estimates are read as the 5th and 95th percentiles:

        mu    = (ln(min_val) + ln(max_val)) / 2
        sigma = (ln(max_val) - ln(min_val)) / 3.29      # 3.29 = 2 * 1.645

    Properties, by construction:
      - min_val  -> ~5th percentile  (SOFT floor, not a hard bound)
      - max_val  -> ~95th percentile
      - median   = geometric mean of min_val and max_val
      - tail is controlled: p99 ~= 2x max_val for typical spreads (not unbounded)

    mode_val (most-likely) is ADVISORY ONLY and intentionally does NOT enter the
    calibration. The min/max interval drives the fit. This preserves the familiar
    small/medium/large input model for users while producing a defensible severity
    curve. (A future revision may warn when mode_val and the fitted median diverge
    beyond a threshold; out of scope here.)

    Args:
        min_val:  Low estimate, treated as ~5th percentile (dollars per event)
        mode_val: Most-likely estimate. ADVISORY — not used in calibration.
        max_val:  High estimate, treated as ~95th percentile (dollars per event)
        n_samples: Number of samples to generate

    Returns:
        numpy.ndarray: Lognormal severity samples (dollars per event)
    """
    # Degenerate case: no spread to calibrate against.
    if min_val == max_val:
        return np.full(n_samples, float(max_val))

    # Lognormal domain is strictly positive; floor inputs at $1 so ln() is
    # defined. Magnitude inputs are dollars, so this is a no-op in practice.
    lo = max(float(min_val), 1.0)
    hi = max(float(max_val), lo * (1.0 + 1e-9))

    mu = (np.log(lo) + np.log(hi)) / 2.0
    sigma = (np.log(hi) - np.log(lo)) / 3.29   # 3.29 = 2 * 1.645 (90% CI z-span)
    sigma = max(sigma, 1e-6)                   # guard against degenerate spread

    return np.random.lognormal(mu, sigma, n_samples)
```

**Intentional behavior changes (these are corrections, not regressions — note them for the reviewer):**

- **No shift.** `min_val` is now a soft 5th percentile; ~5% of samples fall below it. The old hard floor at `min_val` is removed by design.
- **No ceiling clamp.** The tail is bounded by the calibration (p99 ≈ 2× max), not by a hard cap.
- **`mode_val` is accepted but unused.** Do not delete it from the signature.

**Do not** change the signature. Both call sites — the LM branch in `run_monte_carlo` (≈ simulation.py:99) and the `_draw_lm` closure used by compound mode (≈ simulation.py:108) — pass positional args and must keep working untouched.

---

## 4. Change 2 — `main.py`: unify `/analyze` onto the compound model

**4a.** At main.py:1175, immediately after the existing import inside the analyze route:

```python
        from simulation import run_monte_carlo
```

add:

```python
        from config import OIC_MC_COMPOUND
```

**4b.** At the `run_monte_carlo(...)` call at main.py:1234, add the `compound_mode` kwarg so the call reads:

```python
        results = run_monte_carlo(
            **original_inputs,
            n_simulations=n_simulations,
            lef_distribution='pert',
            lm_distribution='lognormal',
            compound_mode=OIC_MC_COMPOUND,
        )
```

That is the entire model-unification change. The recalibration in §3 flows through the compound path automatically via `_draw_lm`; `run_monte_carlo` itself needs no edits.

**Before editing, verify** there are exactly two `run_monte_carlo` call sites (`grep -n run_monte_carlo main.py` → 1234 analyze, 1330 recalculate) and that all generation modes (Path A / Path B / cascade) funnel through `/analyze`. If a third call site exists, stop and report it rather than guessing.

---

## 5. Worked numbers for audit (production inputs: min $2M, max $50M)

```
mu    = (ln 2,000,000 + ln 50,000,000) / 2 = (14.5087 + 17.7275)/2 = 16.1181
sigma = (ln 50,000,000 - ln 2,000,000) / 3.29 = 3.2188 / 3.29       = 0.9784
```

| Statistic | Current (broken) | After this change |
|---|---|---|
| Mode | $8.0M | ~$3.8M |
| Median | ~$123M | ~$10.0M  (= √(2M·50M)) |
| Mean | ~$543M | ~$16.1M |
| p95 | ~$2.1B | ~$50.0M  (= max, by construction) |
| p99 | ~$6.8B | ~$97.4M  (≈ 2× max) |
| p5 | n/a | ~$2.0M   (= min, by construction) |

Compound annual roll-up for the scenario (LEF PERT 0.01/0.1/0.3, no reductions): expected annual loss (mean) drops from ~$68M to **~$2M**; the **typical year (median) is $0** because events are rare (λ≈0.1, ~89% of years have zero events); the tail (p95–p99) lands in the tens of millions, not hundreds. The $0 median year is correct and intended, not a bug.

---

## 6. Acceptance tests (must pass)

Add as a test module (e.g. `test_severity_recalibration.py`) alongside the existing suite.

```python
import numpy as np
from simulation import generate_lognormal_samples

def test_severity_calibration_levels():
    np.random.seed(42)
    s = generate_lognormal_samples(2_000_000, 8_000_000, 50_000_000, 500_000)
    assert abs(np.median(s)        - 10.0e6) / 10.0e6 < 0.05   # median ~ geo-mean
    assert abs(np.mean(s)          - 16.1e6) / 16.1e6 < 0.05   # mean
    assert abs(np.percentile(s,95) - 50.0e6) / 50.0e6 < 0.05   # p95 ~ max
    assert abs(np.percentile(s,99) - 97.4e6) / 97.4e6 < 0.10   # p99 ~ 2x max

def test_min_is_soft_floor_not_hard():
    np.random.seed(1)
    s = generate_lognormal_samples(2_000_000, 8_000_000, 50_000_000, 500_000)
    frac_below_min = float((s < 2_000_000).mean())
    assert 0.03 < frac_below_min < 0.07               # ~5% below min by design

def test_most_likely_is_advisory_only():
    # mu/sigma depend only on min & max; mode_val must not affect output.
    np.random.seed(7); a = generate_lognormal_samples(2e6,  3e6, 50e6, 200_000)
    np.random.seed(7); b = generate_lognormal_samples(2e6, 49e6, 50e6, 200_000)
    assert np.allclose(a, b)

def test_degenerate_equal_min_max():
    s = generate_lognormal_samples(5e6, 5e6, 5e6, 1000)
    assert np.all(s == 5e6)
```

**Integration check (manual or scripted):** POST the scenario to `/analyze` and confirm mean annual loss is single-digit millions (~$2M), p50 ≈ $0, and p95 is in the tens of millions. Confirm `/analyze` and `/recalculate` now use the **same model** (both compound). Note: with `likelihood_reduction=0`, `/recalculate` still applies the baseline 25% vulnerability credit (main.py:1318), so the two routes will not produce *identical* numbers — that gap is expected and is not to be "fixed."

---

## 7. Explicitly out of scope — do not touch

- `generate_pert_samples`, `generate_poisson_samples`, and the `lm_distribution='pert'` branch.
- The `run_monte_carlo` body (product/compound logic, lever routing, validation).
- The questionnaire LEF preview / two-value likelihood override on the card — that is a deliberate "second chance" feature, not a bug.
- The 25% baseline vulnerability credit in `/recalculate`.
- Enterprise-value / policy-limit cap (deferred to a separate change).
- Most-likely-vs-fitted-median divergence alert (deferred).
- No new environment flags. No signature or call-site changes.

---

## 8. Rollback

- **Model unification:** set `OIC_MC_COMPOUND=0` to revert both routes to the product model (no code change needed).
- **Calibration:** `git revert` of the §3 function. There is no flag for it — it is a strict correction, not an optional mode.
