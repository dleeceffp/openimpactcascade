import numpy as np
from scipy.stats import pert

def run_monte_carlo(lef_min, lef_mle, lef_max, lm_min, lm_mle, lm_max, n_simulations=10000):
    """
    Runs a Monte Carlo simulation for risk analysis based on FAIR principles.

    Args:
        lef_min (float): Minimum Loss Event Frequency.
        lef_mle (float): Most Likely Loss Event Frequency.
        lef_max (float): Maximum Loss Event Frequency.
        lm_min (float): Minimum Loss Magnitude.
        lm_mle (float): Most Likely Loss Magnitude.
        lm_max (float): Maximum Loss Magnitude.
        n_simulations (int): The number of simulations to run.

    Returns:
        dict: A dictionary containing summary statistics of the simulation.
    """
    # For the PERT distribution in SciPy, the shape parameter 'b' is the peak (most likely value)
    # scaled to the interval [0, 1].
    def calculate_b(min_val, mle_val, max_val):
        if max_val == min_val: # Avoid division by zero
            return 0.5
        return (mle_val - min_val) / (max_val - min_val)

    # Create PERT distributions for frequency and magnitude
    lef_b = calculate_b(lef_min, lef_mle, lef_max)
    lm_b = calculate_b(lm_min, lm_mle, lm_max)

    lef_dist = pert(b=lef_b, loc=lef_min, scale=lef_max - lef_min)
    lm_dist = pert(b=lm_b, loc=lm_min, scale=lm_max - lm_min)

    # Generate random samples from the distributions
    lef_samples = lef_dist.rvs(size=n_simulations)
    lm_samples = lm_dist.rvs(size=n_simulations)

    # Calculate the annualized loss for each simulation run
    annualized_loss = lef_samples * lm_samples

    # Return a dictionary of summary statistics
    results = {
        'mean_annualized_loss': np.mean(annualized_loss),
        'median_annualized_loss': np.median(annualized_loss),
        'loss_percentile_5': np.percentile(annualized_loss, 5),
        'loss_percentile_95': np.percentile(annualized_loss, 95),
        'annualized_loss_samples': annualized_loss.tolist() # For future charting
    }

    return results
