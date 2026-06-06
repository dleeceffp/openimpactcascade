# OIC — Lever-Aware Monte Carlo Patch (Coding Agent Instructions)

**Doc:** OIC-PROC-SIM-001 · **Status:** draft · **Targets:** `simulation.py` (`run_monte_carlo`),
`main.py` (`/recalculate`). Additive and backward-compatible; defaults reproduce current numbers.

## 0. Objective

Replace the single flat multiplier on annual loss with **two bounded factors that act on the two
FAIR variables separately**: the **odds** lever (likelihood) acts on **frequency/vulnerability**;
the **size** lever (impact) acts on **magnitude**. Add an **optional compound mode** that makes the
two levers genuinely diverge in distribution shape (the version that withstands scrutiny). Never let
risk reduce to zero — keep a residual-risk floor.

**Honesty note for the implementer:** on the existing `annual = lef * lm` product, splitting the
factor across the two variables is mathematically the same as one combined multiplier. The split is
worth doing for correct attribution and auditability, but the *distribution-shape* divergence only
appears in compound mode. Do not claim otherwise in code comments or UI.

## 1. `simulation.py` — extend `run_monte_carlo`

Add parameters (all defaulted so current callers are unaffected):

```python
def run_monte_carlo(
    lef_min, lef_mle, lef_max,
    lm_min, lm_mle, lm_max,
    n_simulations=10000,
    lef_distribution='pert',
    lm_distribution='lognormal',
    lef_lambda=4, lm_lambda=2,
    odds_reduction=0.0,      # likelihood lever -> frequency/vulnerability factor
    size_reduction=0.0,      # impact lever     -> magnitude factor
    max_reduction=0.95,      # residual-risk floor: reductions clamp here, never 1.0
    compound_mode=False,     # False = current product model; True = frequency-severity sum
    seed=None,
):
```

After the existing input validation, clamp the reductions and build the factors:

```python
odds_reduction = min(max(float(odds_reduction), 0.0), max_reduction)
size_reduction = min(max(float(size_reduction), 0.0), max_reduction)
freq_factor = 1.0 - odds_reduction   # acts on LEF (how often)
mag_factor  = 1.0 - size_reduction   # acts on LM  (how bad)

rng = np.random.default_rng(seed)    # reproducible; see §4
```

Generate `lef_samples` and `lm_samples` exactly as today (reuse the PERT/lognormal/poisson helpers).
Then branch the annual-loss computation:

```python
if not compound_mode:
    # CURRENT model, lever-routed. Behaviour-preserving when reductions are 0.
    lef_adj = lef_samples * freq_factor
    lm_adj  = lm_samples  * mag_factor
    annual_loss = lef_adj * lm_adj
else:
    # COMPOUND model: events occur at the (reduced) rate; each event draws a
    # (reduced) severity; annual loss is the SUM of per-event severities.
    rates  = np.clip(lef_samples * freq_factor, 0.0, None)
    counts = rng.poisson(rates)                      # integer events per trial
    total  = int(counts.sum())
    if total == 0:
        annual_loss = np.zeros(n_simulations)
    else:
        # one severity draw PER EVENT (reuse the LM helper), then segment-sum by trial
        severities = _draw_lm(total) * mag_factor    # _draw_lm wraps the chosen LM helper
        trial_idx  = np.repeat(np.arange(n_simulations), counts)
        annual_loss = np.zeros(n_simulations)
        np.add.at(annual_loss, trial_idx, severities)
```

`_draw_lm(k)` is a tiny local closure that calls the already-selected LM generator
(`generate_lognormal_samples` / `generate_pert_samples`) with `k` samples and the `lm_*` params.
Zero-count trials correctly contribute $0 (a real "nothing happened" year).

Add to the returned `results` dict, under a new key, for transparency/audit:

```python
results['levers'] = {
    'odds_reduction': odds_reduction,
    'size_reduction': size_reduction,
    'max_reduction': max_reduction,
    'compound_mode': compound_mode,
}
```

Everything else (mean/std/percentiles/`samples`/`distribution_info`) is unchanged.

## 2. Multiplicative stacking helper

Multiple controls on the same lever must compound, not add. Add:

```python
def combine_reductions(reductions):
    """Combine independent reductions multiplicatively: 1 - prod(1 - r)."""
    surv = 1.0
    for r in reductions:
        surv *= (1.0 - min(max(float(r), 0.0), 1.0))
    return 1.0 - surv
```

So three 25% likelihood controls give `combine_reductions([.25,.25,.25]) ≈ 0.578`, not 0.75 — and
never exceed 1.0.

## 3. `main.py` — `/recalculate` wiring

- Map the endpoint's existing inputs: `likelihood_reduction -> odds_reduction`,
  `impact_reduction -> size_reduction`.
- **Route the existing 25% vulnerability-management credit into `odds_reduction`** (it's a
  likelihood/vulnerability reduction, not a final-loss haircut). Combine it with any user-selected
  likelihood controls via `combine_reductions`.
- Pass `compound_mode` from a config flag (`OIC_MC_COMPOUND`, default `"0"`); pass a fixed/derived
  `seed` for reproducible recalculation if desired.
- Do **not** change the Monte Carlo aggregation, the percentile outputs, the response schema, the
  sliders UI, or the questionnaire flow.

## 4. Reproducibility

Thread `seed` through `run_monte_carlo` and use `np.random.default_rng(seed)` for the compound
draws. (The legacy helpers use the global `np.random`; leave them for now, but note in a comment
that a later pass should pass the `rng` into them for full determinism.)

## 5. Config

```python
OIC_MC_COMPOUND = os.getenv("OIC_MC_COMPOUND", "0") == "1"   # default off for demo stability
```

Recommend: validate the compound-mode percentile shift against current numbers before enabling in
production. Expected loss (mean) stays comparable; percentiles change (zero-loss years appear).

## 6. Acceptance

1. `odds_reduction=0, size_reduction=0, compound_mode=False` → output identical to current behaviour.
2. Non-compound: setting `odds_reduction=0.4` scales annual loss the same as `size_reduction=0.4`
   (confirms the documented algebraic equivalence — attribution differs, shape does not).
3. Compound: `odds_reduction` increases the share of $0 (zero-event) trials; `size_reduction` shrinks
   the dollar axis without adding zero-loss years — the two levers now reshape the distribution
   differently. Mean annual loss ≈ matches the non-compound mean for the same inputs.
4. Reductions clamp at `max_reduction`; no input produces negative loss or zero total risk.
5. `combine_reductions` compounds multiplicatively and stays in [0,1).
6. `/recalculate` routes the 25% vuln credit through `odds_reduction`; sliders/engine/schema unchanged.
7. Same `seed` reproduces identical compound-mode results.

## 7. Out of scope (next tier)

The per-stage terminal-ladder model (Approach A proper) — where the loss *size* depends on which
chokepoint stopped the attack — is a separate feature reading a cost table from the cascade card.
See the design doc, §2. Do not build it here.
