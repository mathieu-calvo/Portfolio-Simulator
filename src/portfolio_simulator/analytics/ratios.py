"""Risk-adjusted performance ratios."""

from __future__ import annotations

import numpy as np
import pandas as pd

from portfolio_simulator.analytics.returns import annualized_return
from portfolio_simulator.analytics.risk import annualized_volatility, max_drawdown
from portfolio_simulator.config import settings


def sharpe_ratio(
    prices: pd.Series,
    risk_free_rate: float | None = None,
    trading_days: int | None = None,
) -> float:
    """Annualized Sharpe ratio.

    Sharpe = (annualized_return - risk_free_rate) / annualized_volatility
    """
    rf = risk_free_rate if risk_free_rate is not None else settings.risk_free_rate
    td = trading_days or settings.trading_days_per_year
    ann_ret = annualized_return(prices, td)
    ann_vol = annualized_volatility(prices, td)
    if ann_vol == 0:
        return 0.0
    return (ann_ret - rf) / ann_vol


def sortino_ratio(
    prices: pd.Series,
    risk_free_rate: float | None = None,
    trading_days: int | None = None,
) -> float:
    """Annualized Sortino ratio (penalizes only downside volatility).

    Sortino = (annualized_return - risk_free_rate) / downside_deviation
    """
    rf = risk_free_rate if risk_free_rate is not None else settings.risk_free_rate
    td = trading_days or settings.trading_days_per_year
    ann_ret = annualized_return(prices, td)
    daily_ret = prices.pct_change().dropna()
    daily_rf = (1 + rf) ** (1 / td) - 1
    downside = daily_ret[daily_ret < daily_rf] - daily_rf
    downside_dev = float(np.sqrt((downside**2).mean()) * np.sqrt(td))
    if downside_dev == 0:
        return 0.0
    return (ann_ret - rf) / downside_dev


def calmar_ratio(
    prices: pd.Series,
    trading_days: int | None = None,
) -> float:
    """Calmar ratio: annualized return / abs(max drawdown).

    Higher is better. Undefined (returns 0) if no drawdown.
    """
    td = trading_days or settings.trading_days_per_year
    ann_ret = annualized_return(prices, td)
    dd = max_drawdown(prices)
    if dd.max_drawdown == 0:
        return 0.0
    return ann_ret / abs(dd.max_drawdown)


def information_ratio(
    prices: pd.Series,
    benchmark_prices: pd.Series,
    trading_days: int | None = None,
) -> float:
    """Information ratio: excess return over benchmark / tracking error.

    Args:
        prices: Portfolio price series.
        benchmark_prices: Benchmark price series (same date range).
        trading_days: Trading days per year.
    """
    td = trading_days or settings.trading_days_per_year
    port_ret = prices.pct_change().dropna()
    bench_ret = benchmark_prices.pct_change().dropna()

    # Align
    common = port_ret.index.intersection(bench_ret.index)
    excess = port_ret.loc[common] - bench_ret.loc[common]

    tracking_error = float(excess.std() * np.sqrt(td))
    if tracking_error == 0:
        return 0.0
    return float(excess.mean() * td) / tracking_error
