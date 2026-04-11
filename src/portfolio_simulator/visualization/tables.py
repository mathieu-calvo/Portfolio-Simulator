"""Formatted summary tables for display."""

from __future__ import annotations

import pandas as pd

from portfolio_simulator.analytics.comparison import comparison_table
from portfolio_simulator.analytics.returns import multi_horizon_returns
from portfolio_simulator.analytics.risk import multi_horizon_volatility
from portfolio_simulator.domain.results import BacktestResult


def summary_stats_table(results: list[BacktestResult]) -> pd.DataFrame:
    """Key statistics table formatted for display.

    Returns a DataFrame with percentage-formatted values.
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

    # Format currency
    currency_rows = ["Total Invested", "Final Value", "Total Fees Paid", "Total Taxes Paid"]
    for row in currency_rows:
        if row in df.index:
            df.loc[row] = df.loc[row].apply(lambda x: f"${x:,.2f}" if isinstance(x, (int, float)) else x)

    return df


def multi_horizon_table(results: list[BacktestResult]) -> pd.DataFrame:
    """Multi-horizon return and volatility table.

    Rows are horizons (YTD, 1Y, 3Y, 5Y, 10Y, Full Period).
    Columns are multi-level: (portfolio_name, metric).
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
    return df
