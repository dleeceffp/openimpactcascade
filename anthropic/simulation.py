"""
Monte Carlo simulation for FAIR risk analysis.
Performs PERT-based simulation of Loss Event Frequency (LEF) and Loss Magnitude (LM).
"""

import numpy as np
from scipy import stats


def run_monte_carlo(lef_min, lef_mle, lef_max, lm_min, lm_mle, lm_max, n_simulations=10000):
    """
    Run Monte Carlo simulation for risk analysis using PERT distributions.
    
    Args:
        lef_min: Minimum Loss Event Frequency (events per year)
        lef_mle: Most Likely Loss Event Frequency (events per year)
        lef_max: Maximum Loss Event Frequency (events per year)
        lm_min: Minimum Loss Magnitude (dollars per event)
        lm_mle: Most Likely Loss Magnitude (dollars per event)
        lm_max: Maximum Loss Magnitude (dollars per event)
        n_simulations: Number of Monte Carlo iterations (default: 10,000)
    
    Returns:
        dict: Dictionary containing simulation results with keys:
            - mean: Expected annual loss
            - std: Standard deviation
            - min: Minimum observed loss
            - max: Maximum observed loss
            - p10, p25, p50, p75, p90, p95: Percentiles
    """
    
    # Validate inputs
    if not (lef_min <= lef_mle <= lef_max):
        raise ValueError(f"LEF values must satisfy min <= mode <= max: {lef_min}, {lef_mle}, {lef_max}")
    
    if not (lm_min <= lm_mle <= lm_max):
        raise ValueError(f"LM values must satisfy min <= mode <= max: {lm_min}, {lm_mle}, {lm_max}")
    
    if lef_min < 0 or lm_min < 0:
        raise ValueError("All values must be non-negative")
    
    # Generate PERT distribution samples for Loss Event Frequency
    # Using Beta distribution with shape parameters derived from PERT
    lef_samples = generate_pert_samples(lef_min, lef_mle, lef_max, n_simulations)
    
    # Generate PERT distribution samples for Loss Magnitude
    lm_samples = generate_pert_samples(lm_min, lm_mle, lm_max, n_simulations)
    
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
        'p99': float(np.percentile(annual_loss, 99))
    }
    
    return results


def generate_pert_samples(min_val, mode_val, max_val, n_samples):
    """
    Generate samples from a PERT distribution.
    
    PERT (Program Evaluation and Review Technique) distribution is a special case
    of the Beta distribution, commonly used in risk analysis.
    
    Args:
        min_val: Minimum value
        mode_val: Most likely value (mode)
        max_val: Maximum value
        n_samples: Number of samples to generate
    
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
    # PERT uses a modified Beta distribution with lambda parameter (typically 4)
    lambda_param = 4
    
    # Calculate mean of PERT distribution
    mean = (min_val + lambda_param * mode_val + max_val) / (lambda_param + 2)
    
    # Calculate shape parameters for Beta distribution
    # These formulas ensure the mode is at the specified location
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


# Example usage
if __name__ == "__main__":
    print("FAIR Monte Carlo Simulation Example")
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
    
    # Run simulation
    results = run_monte_carlo(
        lef_min=lef_min,
        lef_mle=lef_mle,
        lef_max=lef_max,
        lm_min=lm_min,
        lm_mle=lm_mle,
        lm_max=lm_max,
        n_simulations=10000
    )
    
    # Display results
    print(format_results(results))
    
    # Risk interpretation
    print()
    print("Risk Interpretation:")
    print(f"- You can expect to lose about ${results['mean']:,.0f} per year on average")
    print(f"- There's a 10% chance losses will exceed ${results['p90']:,.0f}")
    print(f"- There's a 5% chance losses will exceed ${results['p95']:,.0f}")
    print(f"- In the worst case, losses could reach ${results['max']:,.0f}")
