"""Tests for Monte Carlo simulation."""

import numpy as np
import pandas as pd
import pytest

from portfolio_simulator.analytics.monte_carlo import run_monte_carlo


class TestMonteCarlo:
    @pytest.fixture
    def daily_rets(self, sample_prices):
        return sample_prices["STOCK_A"].pct_change().dropna()

    def test_output_shape(self, daily_rets):
        result = run_monte_carlo(daily_rets, n_scenarios=100, n_years=5)
        assert result.n_scenarios == 100
        assert result.n_years == 5
        assert result.all_scenarios.shape[1] == 100
        # Should have ~252*5 + 1 rows
        assert result.all_scenarios.shape[0] > 1000

    def test_starts_at_initial_value(self, daily_rets):
        result = run_monte_carlo(daily_rets, n_scenarios=50, n_years=1, initial_value=5000)
        # All scenarios start at the initial value
        first_row = result.all_scenarios.iloc[0]
        assert (first_row == 5000).all()

    def test_median_between_percentiles(self, daily_rets):
        result = run_monte_carlo(daily_rets, n_scenarios=500, n_years=5)
        final_p5 = result.percentile_5.iloc[-1]
        final_median = result.median.iloc[-1]
        final_p95 = result.percentile_95.iloc[-1]
        assert final_p5 <= final_median <= final_p95

    def test_with_contributions(self, daily_rets):
        no_contrib = run_monte_carlo(daily_rets, n_scenarios=100, n_years=5, initial_value=10000, monthly_contribution=0)
        with_contrib = run_monte_carlo(daily_rets, n_scenarios=100, n_years=5, initial_value=10000, monthly_contribution=500)
        # With contributions should generally be higher
        assert with_contrib.median.iloc[-1] > no_contrib.median.iloc[-1]
