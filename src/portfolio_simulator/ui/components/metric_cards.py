"""KPI metric display cards."""

from __future__ import annotations

import streamlit as st

from portfolio_simulator.domain.results import BacktestResult
from portfolio_simulator.analytics.returns import annualized_return, cumulative_return
from portfolio_simulator.analytics.risk import annualized_volatility, max_drawdown
from portfolio_simulator.analytics.ratios import sharpe_ratio
from portfolio_simulator.utils.currency import currency_symbol


def render_metric_cards(result: BacktestResult) -> None:
    """Render a row of key metric cards for a backtest result."""
    pv = result.portfolio_value

    cum_ret = cumulative_return(pv)
    ann_ret = annualized_return(pv)
    ann_vol = annualized_volatility(pv)
    dd = max_drawdown(pv)
    sharpe = sharpe_ratio(pv)
    final_value = float(pv.iloc[-1])
    sym = currency_symbol(getattr(result, "base_currency", None))

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Final Value", f"{sym}{final_value:,.0f}")
    col2.metric("Cumulative Return", f"{cum_ret:.1%}")
    col3.metric("Annualized Return", f"{ann_ret:.1%}")
    col4.metric("Annualized Volatility", f"{ann_vol:.1%}")
    col5.metric("Max Drawdown", f"{dd.max_drawdown:.1%}")
    col6.metric("Sharpe Ratio", f"{sharpe:.2f}")
