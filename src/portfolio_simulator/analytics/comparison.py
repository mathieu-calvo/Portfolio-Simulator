"""Multi-portfolio comparison analytics."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from portfolio_simulator.analytics.ratios import calmar_ratio, sharpe_ratio, sortino_ratio
from portfolio_simulator.analytics.returns import (
    annualized_return,
    cumulative_return,
    quarterly_returns,
)
from portfolio_simulator.analytics.risk import (
    annualized_volatility,
    max_drawdown,
    value_at_risk,
)
from portfolio_simulator.domain.results import BacktestResult


def align_results(results: list[BacktestResult]) -> list[BacktestResult]:
    """Truncate and renormalize results to a common start date.

    For visual comparison: drops history before the latest first-trading-date
    across all results, then rescales each portfolio_value so it starts at the
    initial investment again. Daily returns, weights, and rebalance dates are
    all sliced to the same window.
    """
    if not results:
        return results

    common_start = max(r.portfolio_value.index[0] for r in results)
    aligned: list[BacktestResult] = []
    for r in results:
        v = r.portfolio_value[r.portfolio_value.index >= common_start]
        if v.empty or len(v) < 2:
            aligned.append(r)
            continue
        scale = float(r.config.initial_investment) / float(v.iloc[0])
        v_norm = v * scale
        v_norm.name = r.portfolio_value.name
        ret = v_norm.pct_change().fillna(0)
        ret.name = r.daily_returns.name
        weights = r.asset_weights_over_time[r.asset_weights_over_time.index >= common_start]
        rebal = tuple(d for d in r.rebalance_dates if pd.Timestamp(d) >= common_start)
        aligned.append(
            replace(
                r,
                portfolio_value=v_norm,
                daily_returns=ret,
                asset_weights_over_time=weights,
                rebalance_dates=rebal,
            )
        )
    return aligned


def comparison_table(results: list[BacktestResult]) -> pd.DataFrame:
    """Build a side-by-side comparison table for multiple portfolio backtests.

    Returns a DataFrame with metrics as rows and portfolio names as columns.
    """
    rows: dict[str, dict[str, object]] = {}

    for r in results:
        pv = r.portfolio_value
        name = r.portfolio_name

        cum_ret = cumulative_return(pv)
        ann_ret = annualized_return(pv)
        ann_vol = annualized_volatility(pv)
        dd = max_drawdown(pv)

        q_ret = quarterly_returns(pv)
        best_q = float(q_ret.max()) if len(q_ret) > 0 else 0.0
        worst_q = float(q_ret.min()) if len(q_ret) > 0 else 0.0

        rows[name] = {
            "Cumulative Return": cum_ret,
            "Annualized Return": ann_ret,
            "Annualized Volatility": ann_vol,
            "Max Drawdown": dd.max_drawdown,
            "Sharpe Ratio": sharpe_ratio(pv),
            "Sortino Ratio": sortino_ratio(pv),
            "Calmar Ratio": calmar_ratio(pv),
            "VaR (95%)": value_at_risk(pv, 0.95),
            "Best Quarter": best_q,
            "Worst Quarter": worst_q,
            "Total Invested": r.total_invested,
            "Final Value": float(pv.iloc[-1]),
            "Total Fees Paid": r.total_fees_paid,
            "Total Taxes Paid": r.total_taxes_paid,
        }

    return pd.DataFrame(rows)


def relative_performance(
    results: list[BacktestResult],
    base_index: int = 0,
) -> pd.DataFrame:
    """Compute relative performance of portfolios vs a base portfolio.

    Returns DataFrame of cumulative excess returns (base portfolio = 0).
    """
    base = results[base_index].portfolio_value
    base_ret = base.pct_change().fillna(0)

    relative = pd.DataFrame()
    for r in results:
        port_ret = r.portfolio_value.pct_change().fillna(0)
        # Align
        common = base_ret.index.intersection(port_ret.index)
        excess = (1 + port_ret.loc[common]).cumprod() - (1 + base_ret.loc[common]).cumprod()
        relative[r.portfolio_name] = excess

    return relative
