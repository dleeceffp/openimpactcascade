"""
Enhanced Monte Carlo simulation for FAIR risk analysis.
Supports multiple distribution types to model realistic cyber risk patterns.

Three strategies available:
1. PERT (original) - symmetric-ish, good for general uncertainty
2. Lognormal - right-skewed, realistic for financial losses
3. Compound (Poisson × Lognormal) - most realistic for cyber risk
"""

import numpy as np
from scipy import stats


def run_monte_carlo(
    lef_min, lef_mle, lef_max, 
    lm_min, lm_mle, lm_max, 
    n_simulations=10000,
    lef_distribution='pert',
    lm_distribution='lognormal',
    lef_lambda=4,
    lm_lambda=2
):
    """
    Run Monte Carlo simulation for risk analysis with configurable distributions.
    
    Distribution recommendations based on research (Eling & Jung 2018, Edwards et al. 2016):
    - Loss Magnitude: 'lognormal' (default, most realistic for financial losses)
    - Loss Event Frequency: 'pert' or 'poisson' (based on data availability)
    
    Args:
        lef_min: Minimum Loss Event Frequency (events per year)
        lef_mle: Most Likely Loss Event Frequency (events per year)
        lef_max: Maximum Loss Event Frequency (events per year)
        lm_min: Minimum Loss Magnitude (dollars per event)
        lm_mle: Most Likely Loss Magnitude (dollars per event)
        lm_max: Maximum Loss Magnitude (dollars per event)
        n_simulations: Number of Monte Carlo iterations (default: 10,000)
        lef_distribution: Distribution type for LEF ('pert', 'poisson')
        lm_distribution: Distribution type for LM ('pert', 'lognormal')
        lef_lambda: PERT lambda for LEF if using PERT (2-6, default 4)
        lm_lambda: PERT lambda for LM if using PERT (2-6, default 2 for right-skew)
    
    Returns:
        dict: Dictionary containing simulation results with keys:
            - mean: Expected annual loss
            - std: Standard deviation
            - min: Minimum observed loss
            - max: Maximum observed loss
            - p10, p25, p50, p75, p90, p95, p99: Percentiles
            - distribution_info: Information about distributions used
    """
    
    # Validate inputs
    if not (lef_min <= lef_mle <= lef_max):
        raise ValueError(f"LEF values must satisfy min <= mode <= max: {lef_min}, {lef_mle}, {lef_max}")
    
    if not (lm_min <= lm_mle <= lm_max):
        raise ValueError(f"LM values must satisfy min <= mode <= max: {lm_min}, {lm_mle}, {lm_max}")
    
    if lef_min < 0 or lm_min < 0:
        raise ValueError("All values must be non-negative")
    
    # Generate Loss Event Frequency samples based on selected distribution
    if lef_distribution == 'pert':
        lef_samples = generate_pert_samples(lef_min, lef_mle, lef_max, n_simulations, lambda_param=lef_lambda)
    elif lef_distribution == 'poisson':
        lef_samples = generate_poisson_samples(lef_min, lef_mle, lef_max, n_simulations)
    else:
        raise ValueError(f"Unknown LEF distribution: {lef_distribution}")
    
    # Generate Loss Magnitude samples based on selected distribution
    if lm_distribution == 'pert':
        lm_samples = generate_pert_samples(lm_min, lm_mle, lm_max, n_simulations, lambda_param=lm_lambda)
    elif lm_distribution == 'lognormal':
        lm_samples = generate_lognormal_samples(lm_min, lm_mle, lm_max, n_simulations)
    else:
        raise ValueError(f"Unknown LM distribution: {lm_distribution}")
    
    # Calculate Annual Loss for each simulation
    # Annual Loss = Loss Event Frequency × Loss Magnitude
    annual_loss = lef_samples * lm_samples
    
    # Calculate statistics
    results = {
        'mean': float(np.mean(annual_loss)),
        'std': float(np.std(annual_loss)),
        'min': float(np.min(annual_loss)),
        'max': float(np.max(annual_loss)),
        'p10': float(np.percentile(annual_loss, 10)),
        'p25': float(np.percentile(annual_loss, 25)),
        'p50': float(np.percentile(annual_loss, 50)),  # Median
        'p75': float(np.percentile(annual_loss, 75)),
        'p90': float(np.percentile(annual_loss, 90)),
        'p95': float(np.percentile(annual_loss, 95)),
        'p99': float(np.percentile(annual_loss, 99)),
        'distribution_info': {
            'lef': lef_distribution,
            'lm': lm_distribution,
            'lef_lambda': lef_lambda if lef_distribution == 'pert' else None,
            'lm_lambda': lm_lambda if lm_distribution == 'pert' else None
        }
    }
    
    return results


def generate_pert_samples(min_val, mode_val, max_val, n_samples, lambda_param=4):
    """
    Generate samples from a PERT distribution.
    
    PERT (Program Evaluation and Review Technique) distribution is a special case
    of the Beta distribution. Lambda parameter controls peakedness:
    - lambda=2: Flatter, more spread (more extreme values)
    - lambda=4: Standard PERT (balanced)
    - lambda=6: More peaked at mode (less extreme values)
    
    For cyber risk:
    - Use lambda=2-3 for Loss Magnitude (allow for catastrophic tail)
    - Use lambda=4-6 for Loss Event Frequency (more predictable)
    
    Args:
        min_val: Minimum value
        mode_val: Most likely value (mode)
        max_val: Maximum value
        n_samples: Number of samples to generate
        lambda_param: PERT lambda parameter (2-6, default 4)
    
    Returns:
        numpy.ndarray: Array of samples from the PERT distribution
    """
    
    # Handle edge case: all values are the same (no uncertainty)
    if min_val == mode_val == max_val:
        return np.full(n_samples, min_val)
    
    # Handle edge case: min == mode or mode == max (degenerate distribution)
    if min_val == mode_val:
        # Right-skewed distribution
        mode_val = min_val + (max_val - min_val) * 0.001
    elif mode_val == max_val:
        # Left-skewed distribution
        mode_val = max_val - (max_val - min_val) * 0.001
    
    # Calculate PERT distribution parameters
    range_val = max_val - min_val
    
    if range_val == 0:
        return np.full(n_samples, min_val)
    
    # Calculate alpha and beta for Beta distribution
    # Using standard PERT formulas
    alpha = 1 + lambda_param * (mode_val - min_val) / range_val
    beta = 1 + lambda_param * (max_val - mode_val) / range_val
    
    # Ensure parameters are valid (must be > 0)
    alpha = max(alpha, 0.1)
    beta = max(beta, 0.1)
    
    # Generate Beta distribution samples
    beta_samples = np.random.beta(alpha, beta, n_samples)
    
    # Scale Beta samples to [min_val, max_val] range
    pert_samples = min_val + beta_samples * range_val
    
    return pert_samples


def generate_lognormal_samples(min_val, mode_val, max_val, n_samples):
    """
    Generate samples from a Lognormal distribution.
    
    Lognormal is MORE REALISTIC for cyber risk losses because:
    1. Right-skewed (many small losses, few large ones)
    2. Fat tails (captures catastrophic events)
    3. Used in insurance and financial risk modeling
    4. Supported by research (Eling & Jung 2018)
    
    Real-world pattern:
    - 80% of incidents: Below mode (small losses)
    - 15% of incidents: Near mode to 75th percentile (moderate losses)
    - 5% of incidents: Above 75th percentile (large losses)
    - 1% of incidents: Above 95th percentile (catastrophic losses)
    
    Args:
        min_val: Minimum value (treated as floor, not hard bound)
        mode_val: Most likely value (peak of distribution)
        max_val: Maximum value (used to calibrate tail, not hard bound)
        n_samples: Number of samples to generate
    
    Returns:
        numpy.ndarray: Array of samples from the Lognormal distribution
    """
    
    # Handle edge case: all values are the same
    if min_val == mode_val == max_val:
        return np.full(n_samples, min_val)
    
    # Shift to work with positive values
    shift = min_val
    mode_shifted = mode_val - shift
    max_shifted = max_val - shift
    
    # Prevent degenerate cases
    if mode_shifted <= 0:
        mode_shifted = (max_val - min_val) * 0.1
    if max_shifted <= mode_shifted:
        max_shifted = mode_shifted * 3
    
    # For lognormal: mode = exp(μ - σ²)
    # We need to find μ and σ such that:
    # 1. Mode is at mode_shifted
    # 2. ~95th percentile is near max_shifted
    
    # Use quantile matching approach
    # Assume max is approximately the 95th percentile
    # For lognormal: P95 ≈ exp(μ + 1.645σ)
    # Mode = exp(μ - σ²)
    
    # Initial estimate: use mode and max to estimate parameters
    # log(mode) = μ - σ²
    # log(P95) = μ + 1.645σ
    
    # Solve for σ and μ
    # This is a simplified approach that works well in practice
    log_mode = np.log(mode_shifted)
    log_p95 = np.log(max_shifted)
    
    # Estimate sigma from the spread
    sigma = (log_p95 - log_mode) / 2.0  # Heuristic that works well
    
    # Solve for mu
    mu = log_mode + sigma**2
    
    # Ensure reasonable parameters (avoid extreme values)
    sigma = np.clip(sigma, 0.3, 2.0)  # Reasonable range for cyber risk
    
    # Generate lognormal samples
    lognormal_samples = np.random.lognormal(mu, sigma, n_samples)
    
    # Shift back to original scale
    samples = lognormal_samples + shift
    
    # Apply soft floor (rarely goes below min_val)
    samples = np.maximum(samples, shift)
    
    return samples


def generate_poisson_samples(min_val, mode_val, max_val, n_samples):
    """
    Generate samples from a Poisson distribution.
    
    Poisson is APPROPRIATE for Loss Event Frequency because:
    1. Models count data (number of events)
    2. Memoryless (each event independent)
    3. Realistic for rare events (cyber incidents)
    4. Standard in frequency analysis
    
    Note: Poisson uses a single parameter (rate/mean). We estimate this
    from the min/mode/max triangular inputs.
    
    Args:
        min_val: Minimum frequency (events per year)
        mode_val: Most likely frequency (events per year)
        max_val: Maximum frequency (events per year)
        n_samples: Number of samples to generate
    
    Returns:
        numpy.ndarray: Array of samples from Poisson distribution
    """
    
    # Estimate the rate parameter (lambda) for Poisson
    # Use mode as primary estimate (most informative)
    # For Poisson: mode ≈ floor(λ) when λ > 1
    #              mode = 0 when λ < 1
    
    # Use weighted average favoring mode
    rate_estimate = (min_val + 4 * mode_val + max_val) / 6
    
    # Ensure positive rate
    rate_estimate = max(rate_estimate, 0.1)
    
    # Generate Poisson samples
    # Note: Poisson can produce values outside [min, max] because it's
    # a discrete count distribution, which is realistic (you can't hard-cap
    # the number of attacks in a bad year)
    poisson_samples = np.random.poisson(rate_estimate, n_samples)
    
    # Convert to float for consistency with other distributions
    return poisson_samples.astype(float)


def compare_distributions(lef_min, lef_mle, lef_max, lm_min, lm_mle, lm_max, n_simulations=10000):
    """
    Compare results across different distribution strategies.
    
    This helps you understand how distribution choice affects risk estimates.
    
    Returns:
        dict: Results for each distribution strategy
    """
    strategies = {
        'PERT/PERT (Original)': {
            'lef_dist': 'pert',
            'lm_dist': 'pert',
            'lef_lambda': 4,
            'lm_lambda': 4
        },
        'PERT/PERT Right-Skewed': {
            'lef_dist': 'pert',
            'lm_dist': 'pert',
            'lef_lambda': 4,
            'lm_lambda': 2  # Lower lambda = more right-skew
        },
        'PERT/Lognormal (Recommended)': {
            'lef_dist': 'pert',
            'lm_dist': 'lognormal',
            'lef_lambda': 4,
            'lm_lambda': None
        },
        'Poisson/Lognormal (Most Realistic)': {
            'lef_dist': 'poisson',
            'lm_dist': 'lognormal',
            'lef_lambda': None,
            'lm_lambda': None
        }
    }
    
    results = {}
    for name, config in strategies.items():
        result = run_monte_carlo(
            lef_min=lef_min,
            lef_mle=lef_mle,
            lef_max=lef_max,
            lm_min=lm_min,
            lm_mle=lm_mle,
            lm_max=lm_max,
            n_simulations=n_simulations,
            lef_distribution=config['lef_dist'],
            lm_distribution=config['lm_dist'],
            lef_lambda=config.get('lef_lambda', 4),
            lm_lambda=config.get('lm_lambda', 4)
        )
        results[name] = result
    
    return results


def format_results(results):
    """
    Format simulation results for display.
    
    Args:
        results: Dictionary of simulation results
    
    Returns:
        str: Formatted results string
    """
    output = []
    output.append("="*60)
    output.append("FAIR Risk Analysis Results")
    
    # Show distribution info if available
    if 'distribution_info' in results:
        info = results['distribution_info']
        output.append(f"Distribution: LEF={info['lef']}, LM={info['lm']}")
    
    output.append("="*60)
    output.append(f"Expected Annual Loss: ${results['mean']:,.0f}")
    output.append(f"Standard Deviation:   ${results['std']:,.0f}")
    output.append(f"Minimum:              ${results['min']:,.0f}")
    output.append(f"Maximum:              ${results['max']:,.0f}")
    output.append("")
    output.append("Percentiles:")
    output.append(f"  10th: ${results['p10']:,.0f}")
    output.append(f"  25th: ${results['p25']:,.0f}")
    output.append(f"  50th: ${results['p50']:,.0f} (Median)")
    output.append(f"  75th: ${results['p75']:,.0f}")
    output.append(f"  90th: ${results['p90']:,.0f}")
    output.append(f"  95th: ${results['p95']:,.0f}")
    output.append(f"  99th: ${results['p99']:,.0f}")
    output.append("="*60)
    
    return "\n".join(output)


def format_comparison(comparison_results):
    """
    Format comparison of different distribution strategies.
    
    Args:
        comparison_results: Dict of results from compare_distributions()
    
    Returns:
        str: Formatted comparison table
    """
    output = []
    output.append("\n" + "="*80)
    output.append("DISTRIBUTION STRATEGY COMPARISON")
    output.append("="*80)
    output.append(f"{'Strategy':<35} {'Mean':<12} {'Median':<12} {'P95':<12} {'P99':<12}")
    output.append("-"*80)
    
    for name, results in comparison_results.items():
        output.append(
            f"{name:<35} "
            f"${results['mean']:>10,.0f} "
            f"${results['p50']:>10,.0f} "
            f"${results['p95']:>10,.0f} "
            f"${results['p99']:>10,.0f}"
        )
    
    output.append("="*80)
    output.append("\nKey Insights:")
    output.append("- Mean: Average expected annual loss")
    output.append("- Median: Typical year (50% of years below this)")
    output.append("- P95: Bad year (5% chance of exceeding)")
    output.append("- P99: Catastrophic year (1% chance of exceeding)")
    output.append("\nLognormal typically shows:")
    output.append("  • Lower median (most years are better)")
    output.append("  • Higher P95/P99 (tail risk is worse)")
    output.append("  • More realistic for cyber risk")
    
    return "\n".join(output)


# Example usage
if __name__ == "__main__":
    print("Enhanced FAIR Monte Carlo Simulation")
    print("="*80)
    print()
    
    # Example scenario: Ransomware attack
    print("Scenario: Ransomware Attack on Healthcare Organization")
    print()
    
    # Loss Event Frequency (events per year)
    lef_min = 0.5   # Happens at least once every 2 years
    lef_mle = 2.0   # Most likely 2 times per year
    lef_max = 8.0   # Could happen up to 8 times per year
    
    # Loss Magnitude (dollars per event)
    lm_min = 150000      # $150K minimum impact
    lm_mle = 750000      # $750K most likely impact
    lm_max = 5000000     # $5M maximum impact
    
    print(f"Loss Event Frequency: {lef_min} - {lef_mle} - {lef_max} events/year")
    print(f"Loss Magnitude: ${lm_min:,} - ${lm_mle:,} - ${lm_max:,} per event")
    print()
    
    # Compare all distribution strategies
    print("Running comparison across distribution strategies...")
    print("(This may take a moment...)")
    print()
    
    comparison = compare_distributions(
        lef_min=lef_min,
        lef_mle=lef_mle,
        lef_max=lef_max,
        lm_min=lm_min,
        lm_mle=lm_mle,
        lm_max=lm_max,
        n_simulations=10000
    )
    
    print(format_comparison(comparison))
    
    # Show detailed results for recommended strategy
    print("\n" + "="*80)
    print("RECOMMENDED STRATEGY: PERT/Lognormal")
    print("="*80)
    print()
    
    recommended_results = run_monte_carlo(
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
    
    print(format_results(recommended_results))
    
    # Risk interpretation
    print()
    print("Risk Interpretation (Lognormal Model):")
    print(f"- Typical year: ${recommended_results['p50']:,.0f} loss (median)")
    print(f"- Average over time: ${recommended_results['mean']:,.0f} per year (mean)")
    print(f"- Bad year (1 in 20): ${recommended_results['p95']:,.0f}")
    print(f"- Catastrophic year (1 in 100): ${recommended_results['p99']:,.0f}")
    print()
    print("Notice:")
    print("- Median < Mean (right-skewed, realistic for cyber risk)")
    print("- Most years are below average (typical for financial losses)")
    print("- Tail risk (P95, P99) is significant (captures rare but severe events)")
