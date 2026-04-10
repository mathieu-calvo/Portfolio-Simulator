"""Return calculations for portfolio analysis."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from portfolio_simulator.config import settings


def cumulative_return(prices: pd.Series) -> float:
    """Total return over the entire series: (final / initial) - 1."""
    return prices.iloc[-1] / prices.iloc[0] - 1


def annualized_return(prices: pd.Series, trading_days: int | None = None) -> float:
    """Annualized return using CAGR formula.

    CAGR = (final / initial) ^ (trading_days_per_year / n_days) - 1
    """
    td = trading_days or settings.trading_days_per_year
    n = len(prices)
    if n < 2:
        return 0.0
    total = prices.iloc[-1] / prices.iloc[0]
    return total ** (td / (n - 1)) - 1


def daily_returns(prices: pd.Series) -> pd.Series:
    """Simple daily percentage returns."""
    ret = prices.pct_change().iloc[1:]
    ret.name = prices.name
    return ret


def calendar_year_returns(prices: pd.Series) -> pd.Series:
    """Return per calendar year.

    Returns:
        Series indexed by year (int), values are yearly returns.
    """
    first = prices.iloc[[0]]
    yearly = pd.concat([first, prices.resample("YE").last()])
    yearly = yearly[~yearly.index.duplicated(keep="last")].sort_index()
    returns = yearly.pct_change().dropna()
    returns.index = returns.index.year
    returns.name = prices.name
    return returns


def quarterly_returns(prices: pd.Series) -> pd.Series:
    """Return per calendar quarter.

    Returns:
        Series indexed by PeriodIndex (quarters), values are quarterly returns.
    """
    first = prices.iloc[[0]]
    quarterly = pd.concat([first, prices.resample("QE").last()])
    quarterly = quarterly[~quarterly.index.duplicated(keep="last")].sort_index()
    returns = quarterly.pct_change().dropna()
    returns.index = returns.index.to_period("Q")
    returns.name = prices.name
    return returns


def monthly_returns(prices: pd.Series) -> pd.Series:
    """Return per calendar month.

    Returns:
        Series indexed by PeriodIndex (months).
    """
    first = prices.iloc[[0]]
    monthly = pd.concat([first, prices.resample("ME").last()])
    monthly = monthly[~monthly.index.duplicated(keep="last")].sort_index()
    returns = monthly.pct_change().dropna()
    returns.index = returns.index.to_period("M")
    returns.name = prices.name
    return returns


def rolling_returns(prices: pd.Series, window_days: int = 252) -> pd.Series:
    """Rolling return over a fixed window.

    Args:
        prices: Daily price series.
        window_days: Lookback window in trading days (default 252 = ~1 year).

    Returns:
        Series of rolling returns.
    """
    return prices.pct_change(periods=window_days).dropna()


def monthly_return_histogram_data(prices: pd.Series) -> pd.Series:
    """Monthly returns suitable for histogram plotting.

    Returns a Series of monthly returns as decimals.
    """
    return monthly_returns(prices)


def multi_horizon_returns(prices: pd.Series) -> dict[str, dict[str, float]]:
    """Compute annualized and cumulative returns over standard horizons.

    Horizons: YTD, 1Y, 3Y, 5Y, 10Y, Full Period.

    Returns:
        Dict mapping horizon name -> {"annualized": float, "cumulative": float}.
    """
    td = settings.trading_days_per_year
    results: dict[str, dict[str, float]] = {}
    end = prices.index[-1]

    # YTD
    year_start = pd.Timestamp(date(end.year, 1, 1))
    ytd_prices = prices[prices.index >= year_start]
    if len(ytd_prices) >= 2:
        cum = ytd_prices.iloc[-1] / ytd_prices.iloc[0] - 1
        results["YTD"] = {"annualized": cum, "cumulative": cum}

    # Standard periods
    for years in [1, 3, 5, 10]:
        start = end - pd.DateOffset(years=years)
        # Only include if we have data going back far enough
        if prices.index[0] > start:
            continue
        period_prices = prices[prices.index >= start]
        if len(period_prices) < 2:
            continue
        cum = period_prices.iloc[-1] / period_prices.iloc[0] - 1
        ann = (1 + cum) ** (1 / years) - 1
        results[f"{years}Y"] = {"annualized": ann, "cumulative": cum}

    # Full period
    cum = prices.iloc[-1] / prices.iloc[0] - 1
    n_days = (prices.index[-1] - prices.index[0]).days
    n_years = n_days / 365.25
    ann = (1 + cum) ** (1 / n_years) - 1 if n_years > 0 else 0.0
    results["Full Period"] = {"annualized": ann, "cumulative": cum}

    return results
