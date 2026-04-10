"""Backtest result value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from portfolio_simulator.domain.simulation import SimulationConfig


@dataclass(frozen=True)
class BacktestResult:
    """Immutable output from a backtest run."""

    portfolio_name: str
    config: SimulationConfig
    portfolio_value: pd.Series  # Daily portfolio value (DatetimeIndex)
    daily_returns: pd.Series  # Daily percentage returns
    asset_weights_over_time: pd.DataFrame  # Actual weights at each date
    rebalance_dates: tuple[date, ...] = ()
    total_invested: float = 0.0
    total_fees_paid: float = 0.0
    total_taxes_paid: float = 0.0


@dataclass(frozen=True)
class MonteCarloResult:
    """Output from Monte Carlo simulation."""

    median: pd.Series
    percentile_5: pd.Series
    percentile_25: pd.Series
    percentile_75: pd.Series
    percentile_95: pd.Series
    all_scenarios: pd.DataFrame  # Each column is one scenario
    n_scenarios: int = 0
    n_years: int = 0
