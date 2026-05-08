"""Monte Carlo simulation for portfolio projections."""

from __future__ import annotations

import numpy as np
import pandas as pd

from portfolio_simulator.config import settings
from portfolio_simulator.domain.results import MonteCarloResult


def run_monte_carlo(
    daily_returns: pd.Series,
    n_scenarios: int = 5000,
    n_years: int = 10,
    initial_value: float = 10_000.0,
    monthly_contribution: float = 0.0,
    trading_days: int | None = None,
) -> MonteCarloResult:
    """Run Monte Carlo simulation using historical return distribution.

    Generates future scenarios by sampling from the empirical return distribution
    (parametric approach using fitted mean and std of log returns).

    Args:
        daily_returns: Historical daily percentage returns.
        n_scenarios: Number of simulation paths.
        n_years: Projection horizon in years.
        initial_value: Starting portfolio value.
        monthly_contribution: Monthly DCA amount (0 for lump sum).
        trading_days: Trading days per year.

    Returns:
        MonteCarloResult with percentile bands and all scenarios.
    """
    td = trading_days or settings.trading_days_per_year
    n_days = int(n_years * td)

    # Fit parameters from historical returns (log returns for GBM)
    clean_returns = daily_returns.dropna()
    log_returns = np.log(1 + clean_returns)
    mu = float(log_returns.mean())
    sigma = float(log_returns.std())

    # Generate random returns: (n_days, n_scenarios)
    rng = np.random.default_rng()
    random_log_returns = rng.normal(mu, sigma, size=(n_days, n_scenarios))

    # Simulate paths
    values = np.empty((n_days + 1, n_scenarios))
    values[0, :] = initial_value

    # Monthly contribution schedule (every ~21 trading days)
    contrib_interval = td // 12

    for i in range(n_days):
        daily_factor = np.exp(random_log_returns[i])
        values[i + 1] = values[i] * daily_factor
        # Apply monthly cashflow (positive = contribution, negative = withdrawal)
        if monthly_contribution != 0 and (i + 1) % contrib_interval == 0:
            values[i + 1] += monthly_contribution

    # Build time index (business days starting from tomorrow-ish)
    start = pd.Timestamp.now().normalize() + pd.tseries.offsets.BDay(1)
    idx = pd.bdate_range(start=start, periods=n_days + 1)[:n_days + 1]
    # Trim to match if business day count differs slightly
    if len(idx) > n_days + 1:
        idx = idx[: n_days + 1]
    elif len(idx) < n_days + 1:
        extra = pd.bdate_range(start=idx[-1] + pd.tseries.offsets.BDay(1), periods=n_days + 1 - len(idx))
        idx = idx.append(extra)

    scenarios_df = pd.DataFrame(values, index=idx)

    # Compute percentiles
    p5 = pd.Series(np.percentile(values, 5, axis=1), index=idx, name="P5")
    p25 = pd.Series(np.percentile(values, 25, axis=1), index=idx, name="P25")
    p50 = pd.Series(np.percentile(values, 50, axis=1), index=idx, name="P50")
    p75 = pd.Series(np.percentile(values, 75, axis=1), index=idx, name="P75")
    p95 = pd.Series(np.percentile(values, 95, axis=1), index=idx, name="P95")

    return MonteCarloResult(
        median=p50,
        percentile_5=p5,
        percentile_25=p25,
        percentile_75=p75,
        percentile_95=p95,
        all_scenarios=scenarios_df,
        n_scenarios=n_scenarios,
        n_years=n_years,
    )
