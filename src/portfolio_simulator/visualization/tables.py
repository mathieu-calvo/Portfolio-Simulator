"""Formatted summary tables for display."""

from __future__ import annotations

import pandas as pd

from portfolio_simulator.analytics.comparison import comparison_table
from portfolio_simulator.analytics.returns import (
    calendar_year_returns,
    multi_horizon_returns,
)
from portfolio_simulator.analytics.risk import multi_horizon_volatility
from portfolio_simulator.domain.results import BacktestResult
from portfolio_simulator.utils.currency import currency_symbol


def summary_stats_table(
    results: list[BacktestResult],
    base_currency: str | None = None,
) -> pd.DataFrame:
    """Key statistics table formatted for display.

    Returns a DataFrame with percentage-formatted values.

    `base_currency` selects the symbol used for monetary rows. When omitted,
    falls back to the currency stored on each result, then USD.
    """
    df = comparison_table(results).astype(object)

    # Format percentages
    pct_rows = [
        "Cumulative Return",
        "Annualized Return",
        "Annualized Volatility",
        "Max Drawdown",
        "VaR (95%)",
        "Best Quarter",
        "Worst Quarter",
    ]
    for row in pct_rows:
        if row in df.index:
            df.loc[row] = df.loc[row].apply(lambda x: f"{x:.2%}" if isinstance(x, (int, float)) else x)

    # Format ratios
    ratio_rows = ["Sharpe Ratio", "Sortino Ratio", "Calmar Ratio"]
    for row in ratio_rows:
        if row in df.index:
            df.loc[row] = df.loc[row].apply(lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else x)

    # Format currency — per-portfolio so mixed-currency comparisons stay correct.
    name_to_currency = {
        r.portfolio_name: (base_currency or getattr(r, "base_currency", None) or "USD")
        for r in results
    }
    currency_rows = ["Total Invested", "Final Value", "Total Fees Paid", "Total Taxes Paid"]
    for row in currency_rows:
        if row not in df.index:
            continue
        for col in df.columns:
            x = df.at[row, col]
            if isinstance(x, (int, float)):
                sym = currency_symbol(name_to_currency.get(col, "USD"))
                df.at[row, col] = f"{sym}{x:,.2f}"

    return df


def calendar_year_returns_table(results: list[BacktestResult]) -> pd.DataFrame:
    """Per-portfolio calendar-year returns, formatted as percentages.

    Rows are calendar years (descending), columns are portfolio names. Years
    where a portfolio has no data show as "—".
    """
    series_by_name: dict[str, pd.Series] = {}
    for r in results:
        s = calendar_year_returns(r.portfolio_value)
        series_by_name[r.portfolio_name] = s

    if not series_by_name:
        return pd.DataFrame()

    df = pd.DataFrame(series_by_name)
    df = df.sort_index(ascending=False)
    df.index.name = "Year"

    def _fmt(x):
        if isinstance(x, (int, float)) and pd.notna(x):
            return f"{x:.2%}"
        return "—"

    return df.map(_fmt)


def multi_horizon_table(results: list[BacktestResult]) -> pd.DataFrame:
    """Multi-horizon return and volatility table, formatted as percentages.

    Rows are horizons (YTD, 1Y, 3Y, 5Y, 10Y, Full Period).
    Columns are multi-level: (portfolio_name, metric).
    Numeric cells are formatted as percentage strings (e.g. "12.34%").
    """
    all_data = {}
    for r in results:
        pv = r.portfolio_value
        ret_data = multi_horizon_returns(pv)
        vol_data = multi_horizon_volatility(pv)

        for horizon in ret_data:
            if horizon not in all_data:
                all_data[horizon] = {}
            all_data[horizon][(r.portfolio_name, "Ann. Return")] = ret_data[horizon]["annualized"]
            all_data[horizon][(r.portfolio_name, "Cum. Return")] = ret_data[horizon]["cumulative"]
            if horizon in vol_data:
                all_data[horizon][(r.portfolio_name, "Ann. Volatility")] = vol_data[horizon]

    df = pd.DataFrame(all_data).T
    df.columns = pd.MultiIndex.from_tuples(df.columns)

    # Format numeric values as percentages for consistent display with
    # the summary stats table. NaN / None stays as "—".
    def _fmt(x):
        if isinstance(x, (int, float)) and pd.notna(x):
            return f"{x:.2%}"
        return "—"

    return df.map(_fmt)
