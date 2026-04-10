"""Cost and fee impact analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd

from portfolio_simulator.config import settings


def ter_drag_daily(ter: float, trading_days: int | None = None) -> float:
    """Convert annual TER to a daily return drag.

    A TER of 0.002 (0.2%) becomes a tiny daily deduction applied to returns.
    """
    td = trading_days or settings.trading_days_per_year
    return (1 + ter) ** (1 / td) - 1


def apply_ter_to_returns(
    daily_returns: pd.Series,
    ter: float,
    trading_days: int | None = None,
) -> pd.Series:
    """Reduce daily returns by the daily-prorated TER.

    Args:
        daily_returns: Series of daily percentage returns.
        ter: Annual Total Expense Ratio as decimal.
        trading_days: Trading days per year.

    Returns:
        Adjusted returns series.
    """
    drag = ter_drag_daily(ter, trading_days)
    return daily_returns - drag


def transaction_cost_impact(
    portfolio_value: float,
    turnover_pct: float,
    cost_per_trade_pct: float,
) -> float:
    """Calculate the cost of a single rebalance event.

    Args:
        portfolio_value: Current portfolio value.
        turnover_pct: Fraction of portfolio traded (e.g., 0.1 = 10% turnover).
        cost_per_trade_pct: Transaction cost as fraction of trade value.

    Returns:
        Dollar cost of the rebalance.
    """
    return portfolio_value * turnover_pct * cost_per_trade_pct


def management_fee_daily(annual_fee: float, trading_days: int | None = None) -> float:
    """Convert annual management fee to daily deduction."""
    td = trading_days or settings.trading_days_per_year
    return annual_fee / td


def tax_on_gains(realized_gain: float, tax_rate: float) -> float:
    """Calculate tax owed on realized capital gains during a rebalance.

    Only applies to positive gains (selling winners to rebalance).
    """
    if realized_gain <= 0:
        return 0.0
    return realized_gain * tax_rate


def cumulative_fee_impact(
    portfolio_values: pd.Series,
    annual_fee: float,
) -> pd.Series:
    """Simulate cumulative impact of an annual fee on portfolio value.

    Useful for comparing "with fee" vs "without fee" scenarios.
    """
    td = settings.trading_days_per_year
    daily_fee = annual_fee / td
    n = len(portfolio_values)
    drag_factors = (1 - daily_fee) ** np.arange(n)
    adjusted = portfolio_values * drag_factors
    adjusted.name = portfolio_values.name
    return adjusted
