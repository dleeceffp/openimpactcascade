import numpy as np
from scipy.stats import beta

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
    def get_pert_samples(min_val, mle_val, max_val, n_samples, gamma=4):
        """Generates samples from a PERT distribution."""
        # Handle edge cases
        if min_val == mle_val == max_val:
            return np.full(n_samples, min_val)
        if min_val >= max_val:
            return np.full(n_samples, mle_val)

        # Calculate alpha and beta parameters for the Beta distribution
        alpha = 1 + gamma * (mle_val - min_val) / (max_val - min_val)
        beta_param = 1 + gamma * (max_val - mle_val) / (max_val - min_val)

        # Generate samples from the Beta distribution and scale them
        beta_samples = beta.rvs(alpha, beta_param, size=n_samples)
        pert_samples = min_val + beta_samples * (max_val - min_val)
        return pert_samples

    # Generate random samples for frequency and magnitude
    lef_samples = get_pert_samples(lef_min, lef_mle, lef_max, n_simulations)
    lm_samples = get_pert_samples(lm_min, lm_mle, lm_max, n_simulations)

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
