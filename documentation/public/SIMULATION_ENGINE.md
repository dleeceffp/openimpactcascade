# OIC Simulation Engine — Probability and Distribution Design

| Field | Value |
|-------|-------|
| **Document ID** | OIC-DOC-SIM-001 |
| **Status** | Current |
| **Date** | 2026-06-13 |
| **Implementation** | `app/simulation.py` |
| **Supersedes** | `documentation/historical/DISTRIBUTION_SELECTION_GUIDE.md` |

This document explains the statistical design of the OIC Monte Carlo simulation engine: what distributions are used and why, the two calculation modes, how the calibration methods work, and the control lever model. It is written for readers with a technical or quantitative background who want to understand the mathematics behind the results.

---

## 1. The FAIR Calculation

OIC implements the core FAIR (Factor Analysis of Information Risk) annual loss calculation:

```
Annual Loss = LEF × LM

where:
  LEF  =  Loss Event Frequency  (successful loss events per year)
       =  TEF × Vulnerability
       =  (Threat Event Frequency) × (probability an attempt succeeds given controls)

  LM   =  Loss Magnitude  (financial impact per loss event, dollars)
```

The Monte Carlo simulation runs this calculation 10,000 times. Each iteration draws independent samples for LEF and LM from their respective probability distributions. The resulting 10,000 annual loss values form the output distribution from which all reported statistics (mean, median, percentiles) are computed.

---

## 2. Why Distributions Matter for Cyber Risk

Choosing the wrong distribution for loss magnitude systematically misstates tail risk. The practical effect is significant: with the same inputs, a symmetric distribution and a right-skewed distribution can produce P99 estimates that differ by a factor of 4–5×.

Cyber losses are empirically right-skewed. The dominant pattern across published breach datasets is:

- The large majority of events (80–90%) produce moderate losses
- A small fraction (5–15%) produce substantially larger losses
- Rare events (1–5%) produce losses an order of magnitude above the typical case

This is the classic signature of a **lognormal** (or heavier-tailed) distribution: mean considerably exceeds median, and the tail extends much further than a symmetric model would suggest. The academic literature confirms this:

- Eling & Jung (2018) — 5,000+ cyber insurance claims; lognormal and generalized beta (GB2) fit best; PERT/Beta underestimated tail losses by 40–60%
- Edwards et al. (2016) — 13+ years of breach data; confirmed heavy-tailed distributions; rejected symmetric models
- Maillart & Sornette (2010) — CERT database; power-law distribution for severity; small events 100–1,000× more frequent than large ones
- Romanosky et al. (2019) — insurance industry uses lognormal for loss modeling as standard actuarial practice

The Verizon DBIR data is consistent with this pattern: 83% of breaches below $100K, 2% above $10M. The IBM Cost of a Data Breach data shows mean > median, the defining signature of right skew.

A PERT distribution fit to the same user inputs as a lognormal will produce a P99 estimate roughly 4–5× lower. That is not conservative; it is an understatement of the risk the organization actually faces.

---

## 3. Distribution Roles: LEF vs. LM

The two FAIR inputs serve different statistical purposes and use different distributions.

### 3.1 Loss Event Frequency (LEF) — PERT distribution

LEF measures how many successful loss events occur per year. It is elicited as a three-point estimate: minimum, most likely (mode), maximum.

**Distribution used:** PERT (Program Evaluation and Review Technique), `lef_distribution='pert'`, `lef_lambda=4`

PERT is a Beta distribution parameterized by min/mode/max with a lambda (peakedness) parameter. The standard parameterization (`lambda=4`) produces a distribution that concentrates mass around the mode while allowing values across the full [min, max] range.

**Why PERT for frequency:**
- Frequency is naturally bounded. The physical interpretation of "loss events per year" has a sensible upper bound; users express that bound directly as `max`. PERT respects that bound by construction.
- User three-point estimates for frequency are the primary data available; PERT is the canonical tool for converting them into a distribution.
- Frequency values tend to be more symmetric than magnitude values in practice — catastrophic frequency outliers (an order of magnitude more events than the stated max) are less characteristic of threat event patterns than catastrophic magnitude outliers.

**The lambda parameter:**
The PERT alpha and beta parameters are derived as:

```
alpha = 1 + lambda × (mode - min) / (max - min)
beta  = 1 + lambda × (max - mode) / (max - min)
```

| lambda | Effect |
|--------|--------|
| 2 | Flatter; heavier tails; more probability mass in extremes |
| 4 | Standard PERT; balanced concentration around mode (default for LEF) |
| 6 | More peaked at mode; less probability in tails |

The default `lef_lambda=4` reflects that frequency estimates — grounded in industry incident data — carry reasonable confidence, and the mode should carry substantial weight.

### 3.2 Loss Magnitude (LM) — Lognormal distribution

LM measures the financial impact per loss event. It is elicited as a three-point estimate: minimum, most likely, maximum.

**Distribution used:** Lognormal, `lm_distribution='lognormal'` (default)

**Why lognormal for magnitude:**
- Magnitude is inherently right-skewed; the lognormal distribution captures this property analytically
- It is unbounded above, which is appropriate — financial losses from a major breach are not capped at the user's stated maximum
- It is the actuarial industry standard for cyber loss severity modeling
- It matches empirical breach loss data better than symmetric alternatives

---

## 4. Lognormal Calibration: The Hubbard/Seiersen Method

This is the most consequential implementation decision in the engine and deserves precise documentation.

The lognormal distribution has two parameters: `mu` (log-mean) and `sigma` (log-standard deviation). The engine fits them from the user's min/max estimates using a **calibrated 90% confidence interval** approach:

```python
mu    = (ln(min_val) + ln(max_val)) / 2
sigma = (ln(max_val) - ln(min_val)) / 3.29     # 3.29 = 2 × 1.645
```

The interpretation:
- `min_val` is treated as the **5th percentile** of the severity distribution
- `max_val` is treated as the **95th percentile** of the severity distribution
- The resulting `mu` is the log-mean — equivalently, `exp(mu)` is the **median** of the distribution, equal to the geometric mean of min and max
- `sigma` is derived from the width of the 90% confidence interval (the 1.645 factor comes from the standard normal z-score for the 95th percentile)

This is the Hubbard/Seiersen calibrated-estimate approach, documented in *How to Measure Anything in Cybersecurity Risk* and standard in quantitative cyber risk practice.

**Critical implementation note:** `mode_val` (the most-likely estimate) is **not used** in the lognormal calibration. The fitted distribution is driven entirely by the min/max interval. This is intentional: the interval directly encodes the spread of outcomes, which is the information most relevant to tail risk. The mode advisory input provides context for the questionnaire but does not alter the fitted curve. A future revision may add a warning when the mode and the fitted median diverge substantially.

**Resulting properties:**

| Quantity | Value |
|----------|-------|
| 5th percentile | ≈ min_val (by construction) |
| Median | geometric mean of min and max: exp((ln(min) + ln(max))/2) |
| 95th percentile | ≈ max_val (by construction) |
| P99 | approximately 2× max_val for typical cyber spreads |
| Mean | > median (always, for lognormal with σ > 0) |

The ratio of mean to median is `exp(sigma²/2)`. For a typical cyber scenario where max is 10–30× min, sigma is approximately 0.7–1.0, and the mean exceeds the median by 28–65%.

---

## 5. The Two Simulation Modes

### 5.1 Product Mode (default, `compound_mode=False`)

The standard FAIR product model:

```
annual_loss[i] = lef_sample[i] × lm_sample[i]
```

Each of the 10,000 iterations draws one LEF value and one LM value independently and multiplies them. This is the direct implementation of the FAIR formula and is appropriate when the LEF input represents the expected number of events per year as a continuous quantity.

### 5.2 Compound Mode (`compound_mode=True`, controlled by `OIC_MC_COMPOUND`)

The compound model treats the annual loss as the sum of individual event severities:

```
For each trial i:
  rate[i]   = lef_sample[i] × freq_factor          # adjusted annual rate
  count[i]  = Poisson(rate[i])                      # integer event count
  annual_loss[i] = Σ lm_draw[j]  for j in 1..count[i]
```

Each iteration draws a Poisson-distributed count of events from the LEF rate, then draws a separate lognormal severity for each individual event and sums them. Trials with zero events contribute $0 to the loss distribution.

**Why compound mode is more theoretically sound:**
- LEF in FAIR is a rate (events per year); Poisson is the canonical distribution for counts arising from a rate process
- Aggregating per-event severities is the correct way to compute annual loss when the number of events varies
- It produces a realistic spike at $0 (years with no events) and a heavy upper tail
- It is how cyber insurance actuaries model aggregate annual loss

**Why compound mode is the current default:**
`OIC_MC_COMPOUND=1` in `config.py`. This was set after validating that the percentile outputs are stable and realistic. The environment variable `OIC_MC_COMPOUND=0` reverts to the product model for debugging or comparison.

**Practical difference between modes:**
At moderate to high frequency (LEF mode > ~0.5 events/year), the two modes produce similar means but compound mode generates a heavier tail (higher P90, P95, P99) and a visible spike at zero annual loss. At very low frequency (LEF mode < 0.1), the zero-loss spike becomes prominent and the tail extends further in compound mode.

---

## 6. Control Lever Model

The results page exposes two control levers for what-if analysis without re-running the questionnaire:

| Lever | Parameter | Effect |
|-------|-----------|--------|
| Frequency/vulnerability reduction | `odds_reduction` ∈ [0, max_reduction] | Scales all LEF samples by `(1 - odds_reduction)` |
| Impact/magnitude reduction | `size_reduction` ∈ [0, max_reduction] | Scales all LM samples by `(1 - size_reduction)` |

Both levers are clamped to `max_reduction = 0.95`. This floor is intentional: no control eliminates risk entirely, and allowing a lever to reach 1.0 would produce a trivially zero expected loss, which is not a defensible claim.

**Combining multiple independent reductions:**

When multiple controls each contribute a partial reduction, they compound multiplicatively rather than adding. The `combine_reductions()` utility implements this:

```python
combined = 1 - product(1 - r  for each reduction r)
```

Example: three independent controls each with 25% likelihood reduction produce a combined reduction of:

```
1 - (0.75 × 0.75 × 0.75) = 1 - 0.422 = 0.578    (57.8%, not 75%)
```

This matters because additive stacking of control reductions is a common error that overstates total control effectiveness.

**In compound mode:** the lever is applied to the rate before the Poisson draw, and the magnitude lever is applied to each per-event severity draw. This is the algebraically correct application point.

---

## 7. Output Statistics

Every `run_monte_carlo()` call returns the following statistics computed over the 10,000 annual loss samples:

| Key | Meaning |
|-----|---------|
| `mean` | Expected Annual Loss (EAL) — the average; the appropriate figure for annual budgeting |
| `std` | Standard deviation — spread of the distribution |
| `p10` | 10th percentile — a good year |
| `p25` | 25th percentile |
| `p50` | Median — the typical year; in a right-skewed distribution, meaningfully below the mean |
| `p75` | 75th percentile |
| `p90` | 90th percentile |
| `p95` | 95th percentile — the "bad year" figure; exceeded in only 5% of simulated years |
| `p99` | 99th percentile — the "catastrophic year" figure; exceeded in only 1% of simulated years |
| `min` / `max` | Observed extremes across the 10,000 trials |
| `distribution_info` | Records which distributions were used (for audit/transparency) |
| `levers` | Records lever inputs applied (for audit/transparency) |
| `samples` | Raw arrays (lef, lm, annual_loss) for visualization |

**Interpreting mean vs. median:**
For a right-skewed distribution (lognormal LM), mean > median. The median describes the typical year — half of simulated years fall below it. The mean describes the long-run average, pulled up by the heavy tail. Both figures are meaningful; they answer different questions.

---

## 8. Distribution Comparison: Same Inputs

Using a representative ransomware scenario — LEF: 0.5–2.0–8.0 events/year; LM: $150K–$750K–$5M per event — the four strategies produce:

| Strategy | Median | Mean | P95 | P99 |
|----------|--------|------|-----|-----|
| PERT/PERT (symmetric) | $2.9M | $3.7M | $9.5M | $13.9M |
| PERT/PERT (right-skewed, lambda=2) | $3.1M | $4.2M | $12.1M | $18.4M |
| **PERT/Lognormal (current default)** | **$4.9M** | **$8.8M** | **$29.3M** | **$63.1M** |
| Poisson/Lognormal (compound mode) | $4.5M | $8.8M | $31.1M | $65.2M |

The PERT/PERT P99 of $13.9M is 4.5× the median. The PERT/Lognormal P99 of $63.1M is 12.9× the median — consistent with the empirical evidence that catastrophic cyber events are far rarer but far larger than the typical case. The PERT/PERT figure is not conservative; it systematically understates the tail the organization faces.

---

## 9. Reproducibility

The product mode uses NumPy's global random state. The compound mode uses `numpy.random.default_rng(seed)` and accepts an optional integer `seed` parameter. A fixed seed produces bit-identical output across runs, which is required for stable demonstrations, snapshot tests, and audit-trail reproducibility. In normal operation (no seed provided), each run produces a different draw from the same distributions.

---

## 10. Implementation Reference

All simulation logic is in `app/simulation.py`. The public API surface is:

| Function | Purpose |
|----------|---------|
| `run_monte_carlo(...)` | Primary entry point — runs the full simulation and returns the results dict |
| `generate_pert_samples(min, mode, max, n, lambda)` | PERT/Beta sampler |
| `generate_lognormal_samples(min, mode, max, n)` | Lognormal sampler (Hubbard/Seiersen calibration) |
| `generate_poisson_samples(min, mode, max, n)` | Poisson sampler (rate estimated from three-point input) |
| `combine_reductions(reductions)` | Multiplicative compounding of independent control reductions |
| `compare_distributions(...)` | Runs all four strategies on the same inputs; used for comparison/debugging |
| `format_results(results)` | Formats a single result dict as a readable string |
| `format_comparison(comparison)` | Formats the multi-strategy comparison as a readable string |

The simulation mode is selected at startup via `OIC_MC_COMPOUND` in `app/config.py` and passed to `run_monte_carlo()` as `compound_mode`. All other distribution parameters use their defaults for normal operation; they are exposed as parameters to support debugging and comparison.
