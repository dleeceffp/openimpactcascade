"""
Test suite for severity recalibration — Loss-Magnitude Hubbard/Seiersen method.

These tests verify that generate_lognormal_samples:
1. Calibrates to a 90% confidence interval (min/max as 5th/95th percentiles)
2. Ignores mode_val (most-likely is advisory only)
3. Produces controlled tails (p99 ~ 2x max, not unbounded)
4. Handles degenerate cases correctly

Run with: pytest tests/test_severity_recalibration.py -v
"""

import numpy as np
import sys
import os

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from simulation import generate_lognormal_samples


class TestSeverityRecalibration:
    """Test suite for severity calibration correctness."""

    def test_severity_calibration_levels(self):
        """
        Verify calibration matches Hubbard/Seiersen 90% CI method.

        For inputs min=$2M, max=$50M:
        - mu = (ln(2M) + ln(50M)) / 2 = 16.1181
        - sigma = (ln(50M) - ln(2M)) / 3.29 = 0.9784

        Expected:
        - Median = exp(mu) = ~$10M (geometric mean of min and max)
        - Mean = exp(mu + sigma²/2) = ~$16.1M
        - p95 = ~$50M (by construction, equals max)
        - p99 = ~$97.4M (~2x max for this spread)
        """
        np.random.seed(42)
        s = generate_lognormal_samples(2_000_000, 8_000_000, 50_000_000, 500_000)

        # Assert within 5% tolerance for all key statistics
        assert abs(np.median(s) - 10.0e6) / 10.0e6 < 0.05, \
            f"Median {np.median(s):,.0f} should be ~$10M"
        assert abs(np.mean(s) - 16.1e6) / 16.1e6 < 0.05, \
            f"Mean {np.mean(s):,.0f} should be ~$16.1M"
        assert abs(np.percentile(s, 95) - 50.0e6) / 50.0e6 < 0.05, \
            f"p95 {np.percentile(s, 95):,.0f} should be ~$50M"
        assert abs(np.percentile(s, 99) - 97.4e6) / 97.4e6 < 0.10, \
            f"p99 {np.percentile(s, 99):,.0f} should be ~$97.4M"

    def test_min_is_soft_floor_not_hard(self):
        """
        Verify min_val is a soft 5th percentile, not a hard floor.

        With min=$2M as the 5th percentile, approximately 5% of samples
        should fall below this value (within statistical tolerance).
        """
        np.random.seed(1)
        s = generate_lognormal_samples(2_000_000, 8_000_000, 50_000_000, 500_000)

        frac_below_min = float((s < 2_000_000).mean())

        # Accept 3-7% below min (target is ~5% with some statistical variance)
        assert 0.03 < frac_below_min < 0.07, \
            f"Fraction below min should be ~5%, got {frac_below_min*100:.1f}%"

    def test_most_likely_is_advisory_only(self):
        """
        Verify mode_val does NOT affect the output distribution.

        The calibration uses only min/max (the 90% CI). Changing mode_val
        should produce identical samples when min/max are held constant.
        """
        # Same seed, same min/max, wildly different modes
        np.random.seed(7)
        a = generate_lognormal_samples(2e6, 3e6, 50e6, 200_000)   # mode=$3M

        np.random.seed(7)
        b = generate_lognormal_samples(2e6, 49e6, 50e6, 200_000)  # mode=$49M

        assert np.allclose(a, b), \
            "Changing mode_val should not affect output distribution"

    def test_degenerate_equal_min_max(self):
        """
        Verify flat distribution when min equals max.

        If there's no spread to calibrate against, all samples should equal
        the input value (returned as a constant array).
        """
        s = generate_lognormal_samples(5e6, 5e6, 5e6, 1000)

        assert np.all(s == 5e6), \
            f"All samples should equal $5M when min=max=mode=$5M, got unique values: {np.unique(s)}"

    def test_max_is_95th_percentile_by_construction(self):
        """
        Verify max_val lands at approximately the 95th percentile.

        This is the defining property of the Hubbard/Seiersen calibration.
        """
        np.random.seed(123)
        max_val = 10_000_000
        s = generate_lognormal_samples(1_000_000, 3_000_000, max_val, 200_000)

        p95 = np.percentile(s, 95)
        assert abs(p95 - max_val) / max_val < 0.05, \
            f"p95 {p95:,.0f} should approximate max_val {max_val:,.0f}"

    def test_tail_controlled_not_unbounded(self):
        """
        Verify tail is bounded and reasonable (p99 ~ 2x max for typical spreads).

        This contrasts with the old "fat tail" implementation where p99 could
        be 10-20x max, leading to catastrophic overestimation of risk.
        """
        np.random.seed(456)
        min_val = 1_000_000
        max_val = 20_000_000
        s = generate_lognormal_samples(min_val, 5_000_000, max_val, 200_000)

        p99 = np.percentile(s, 99)

        # p99 should be roughly 2x max for this spread (within tolerance)
        # For min=$1M, max=$20M: expected p99 ~ $40M (2x max)
        assert p99 < max_val * 4, \
            f"p99 {p99:,.0f} should be < 4x max ({max_val*4:,.0f}), got {p99/max_val:.1f}x"

        # Key assertion: p99 is controlled (for this spread, should be ~$40M)
        # Old implementation had p99 ~ 10-20x max; new should be ~2x
        assert 25_000_000 < p99 < 60_000_000, \
            f"p99 {p99:,.0f} should be ~$40M (2x max=$20M), indicating controlled tail"


class TestWorkedExampleFromSpec:
    """
    Test the exact worked example from the corrective instruction.

    Production inputs: min=$2M, most_likely=$8M, max=$50M
    Expected statistics from §5 of the instruction.
    """

    def test_worked_example_statistics(self):
        """
        Verify the exact numbers from §5 of the corrective instruction.

        mu    = (ln 2,000,000 + ln 50,000,000) / 2 = 16.1181
        sigma = (ln 50,000,000 - ln 2,000,000) / 3.29 = 0.9784

        | Statistic | Current (broken) | After this change |
        | Mode | $8.0M | ~$3.8M |
        | Median | ~$123M | ~$10.0M  (= √(2M·50M)) |
        | Mean | ~$543M | ~$16.1M |
        | p95 | ~$2.1B | ~$50.0M  (= max, by construction) |
        | p99 | ~$6.8B | ~$97.4M  (≈ 2× max) |
        | p5 | n/a | ~$2.0M   (= min, by construction) |
        """
        np.random.seed(42)
        s = generate_lognormal_samples(2_000_000, 8_000_000, 50_000_000, 500_000)

        stats = {
            'mode': self._estimate_mode(s),
            'median': np.median(s),
            'mean': np.mean(s),
            'p5': np.percentile(s, 5),
            'p95': np.percentile(s, 95),
            'p99': np.percentile(s, 99),
        }

        # Verify against expected values from spec
        assert abs(stats['median'] - 10_000_000) / 10_000_000 < 0.05, \
            f"Median should be ~$10M, got ${stats['median']:,.0f}"
        assert abs(stats['mean'] - 16_100_000) / 16_100_000 < 0.05, \
            f"Mean should be ~$16.1M, got ${stats['mean']:,.0f}"
        assert abs(stats['p95'] - 50_000_000) / 50_000_000 < 0.05, \
            f"p95 should be ~$50M, got ${stats['p95']:,.0f}"
        assert abs(stats['p99'] - 97_400_000) / 97_400_000 < 0.10, \
            f"p99 should be ~$97.4M, got ${stats['p99']:,.0f}"

        # Mode should be around $3.8M (not the input $8M - it's advisory only)
        # Note: mode estimation is noisy, so we use a wider tolerance
        assert 2_000_000 < stats['mode'] < 6_000_000, \
            f"Mode should be ~$3.8M (not input $8M), got ${stats['mode']:,.0f}"

    @staticmethod
    def _estimate_mode(samples, bins=1000):
        """Estimate mode from histogram peak."""
        hist, bin_edges = np.histogram(samples, bins=bins)
        max_idx = np.argmax(hist)
        return (bin_edges[max_idx] + bin_edges[max_idx + 1]) / 2


if __name__ == "__main__":
    # Run tests directly if executed as script
    import pytest
    pytest.main([__file__, "-v"])
