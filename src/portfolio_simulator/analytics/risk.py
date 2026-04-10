"""Risk metrics for portfolio analysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from portfolio_simulator.config import settings


def annualized_volatility(
    prices: pd.Series,
    trading_days: int | None = None,
) -> float:
    """Annualized standard deviation of daily returns."""
    td = trading_days or settings.trading_days_per_year
    daily_ret = prices.pct_change().dropna()
    return float(daily_ret.std() * np.sqrt(td))


def rolling_volatility(
    prices: pd.Series,
    window_days: int = 63,
    trading_days: int | None = None,
) -> pd.Series:
    """Rolling annualized volatility.

    Args:
        prices: Daily price series.
        window_days: Rolling window in trading days (default 63 = ~1 quarter).
        trading_days: Trading days per year for annualization.
    """
    td = trading_days or settings.trading_days_per_year
    daily_ret = prices.pct_change().dropna()
    return daily_ret.rolling(window_days).std() * np.sqrt(td)


@dataclass(frozen=True)
class DrawdownInfo:
    """Maximum drawdown details."""

    max_drawdown: float  # Negative value (e.g., -0.25 for -25%)
    peak_date: date
    trough_date: date
    recovery_date: date | None  # None if not yet recovered


def drawdown_series(prices: pd.Series) -> pd.Series:
    """Daily drawdown from running maximum.

    Returns series of non-positive values (0 = at peak, -0.1 = 10% below peak).
    """
    cummax = prices.cummax()
    dd = prices / cummax - 1
    dd.name = prices.name
    return dd


def max_drawdown(prices: pd.Series) -> DrawdownInfo:
    """Calculate maximum drawdown with peak, trough, and recovery dates."""
    dd = drawdown_series(prices)
    trough_idx = dd.idxmin()
    trough_val = dd.loc[trough_idx]

    # Peak is the cummax at the trough
    peak_idx = prices.loc[:trough_idx].idxmax()

    # Recovery: first date after trough where price >= peak price
    peak_price = prices.loc[peak_idx]
    post_trough = prices.loc[trough_idx:]
    recovered = post_trough[post_trough >= peak_price]
    recovery_date = recovered.index[0].date() if len(recovered) > 0 else None

    return DrawdownInfo(
        max_drawdown=float(trough_val),
        peak_date=peak_idx.date() if hasattr(peak_idx, "date") else peak_idx,
        trough_date=trough_idx.date() if hasattr(trough_idx, "date") else trough_idx,
        recovery_date=recovery_date,
    )


def value_at_risk(
    prices: pd.Series,
    confidence: float = 0.95,
) -> float:
    """Historical Value at Risk (VaR) at the given confidence level.

    Returns the loss threshold as a negative number.
    E.g., VaR(95%) = -0.02 means 5% of days had losses exceeding 2%.
    """
    daily_ret = prices.pct_change().dropna()
    return float(np.percentile(daily_ret, (1 - confidence) * 100))


def conditional_value_at_risk(
    prices: pd.Series,
    confidence: float = 0.95,
) -> float:
    """Conditional VaR (Expected Shortfall): mean return in the worst (1-confidence) tail."""
    daily_ret = prices.pct_change().dropna()
    var = np.percentile(daily_ret, (1 - confidence) * 100)
    tail = daily_ret[daily_ret <= var]
    return float(tail.mean()) if len(tail) > 0 else float(var)


def multi_horizon_volatility(prices: pd.Series) -> dict[str, float]:
    """Annualized volatility over standard horizons (YTD, 1Y, 3Y, 5Y, 10Y, Full).

    Returns:
        Dict mapping horizon name -> annualized volatility.
    """
    results: dict[str, float] = {}
    end = prices.index[-1]
    td = settings.trading_days_per_year

    # YTD
    year_start = pd.Timestamp(date(end.year, 1, 1))
    ytd = prices[prices.index >= year_start]
    if len(ytd) > 2:
        results["YTD"] = float(ytd.pct_change().dropna().std() * np.sqrt(td))

    for years in [1, 3, 5, 10]:
        start = end - pd.DateOffset(years=years)
        period = prices[prices.index >= start]
        if len(period) > 2:
            results[f"{years}Y"] = float(period.pct_change().dropna().std() * np.sqrt(td))

    # Full
    if len(prices) > 2:
        results["Full Period"] = float(prices.pct_change().dropna().std() * np.sqrt(td))

    return results
