"""Comparison page -- compare multiple portfolios side by side."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from portfolio_simulator.domain.enums import RebalanceFrequency, RebalanceStrategy
from portfolio_simulator.domain.simulation import SimulationConfig


def _get_services():
    from portfolio_simulator.providers.yahoo import YahooFinanceProvider
    from portfolio_simulator.services import get_portfolio_store
    from portfolio_simulator.services.backtest_engine import BacktestEngine
    from portfolio_simulator.services.data_service import DataService

    provider = YahooFinanceProvider()
    data_service = DataService(provider)
    engine = BacktestEngine(data_service)
    store = get_portfolio_store()
    return engine, store


def render() -> None:
    st.header("Portfolio Comparison")

    st.caption(
        "Run multiple portfolios through the same backtest configuration and compare "
        "their risk/return profiles side by side."
    )
    with st.expander("How Comparison works"):
        st.markdown(
            """
            **What it does:** Backtests 2 to 5 saved portfolios over the same time period
            with the same simulation parameters, then presents their performance on a
            common basis. Use it to answer "is portfolio A better than portfolio B?"

            **How it works:**
            1. Each portfolio is backtested independently using identical start/end dates,
               initial investment, and rebalancing rule.
            2. Results are aligned to a common date axis — a portfolio is only evaluated
               from its first fully-available trading day.
            3. Performance is reported on both an absolute and a risk-adjusted basis.

            **Tabs:**
            - **Evolution:** Equity curves overlaid on the same chart — visual winner is
              the one that ends highest.
            - **Summary:** Full comparison table with all key metrics (returns,
              volatility, Sharpe, drawdown, etc.).
            - **Multi-Horizon:** Returns and volatility broken out by standard lookback
              windows (YTD, 1Y, 3Y, 5Y, 10Y, full period). Useful for spotting whether
              a portfolio's edge is recent or durable.
            - **Drawdown:** Drawdown curves overlaid — the shallower the drawdowns, the
              better the downside protection.

            **How to interpret:**
            - A higher annualized return isn't better if it comes with disproportionately
              more volatility. Use the **Sharpe ratio** to compare risk-adjusted returns.
            - A portfolio with lower max drawdown may be preferable for investors with
              lower risk tolerance, even at a small cost to return.
            - The multi-horizon view reveals whether a "winner" is consistent across
              market regimes or just benefited from a single strong period.
            """
        )

    engine, store = _get_services()
    user_id = st.session_state.get("user_id", "local")
    portfolios = store.list_all(user_id)

    if len(portfolios) < 2:
        st.info("Save at least 2 portfolios to compare. Go to Portfolio Builder.")
        return

    # --- Select Portfolios ---
    names = [p.name for p in portfolios]
    selected = st.multiselect("Select portfolios to compare (2-5)", names, max_selections=5)

    if len(selected) < 2:
        st.info("Select at least 2 portfolios.")
        return

    selected_portfolios = [p for p in portfolios if p.name in selected]

    # --- Shared Config ---
    st.subheader("Simulation Parameters")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start date", value=date(2015, 1, 1), key="cmp_start")
        end_date = st.date_input("End date", value=date.today() - timedelta(days=1), key="cmp_end")
        initial = st.number_input("Initial investment ($)", value=10000, min_value=0, step=1000, key="cmp_init")
    with col2:
        rebal = st.selectbox(
            "Rebalancing",
            [s.value for s in RebalanceStrategy],
            format_func=lambda x: x.replace("_", " ").title(),
            key="cmp_rebal",
        )
        freq = st.selectbox(
            "Frequency",
            [f.value for f in RebalanceFrequency],
            format_func=lambda x: x.replace("_", " ").title(),
            key="cmp_freq",
        )

    config = SimulationConfig(
        start_date=start_date,
        end_date=end_date,
        initial_investment=float(initial),
        rebalance_strategy=rebal,
        rebalance_frequency=freq,
    )

    # --- Run ---
    if st.button("Compare", type="primary"):
        with st.spinner("Running backtests..."):
            try:
                results = engine.run_comparison(selected_portfolios, config)
                st.session_state.comparison_results = results
            except Exception as e:
                st.error(f"Comparison failed: {e}")
                return

    # --- Results ---
    if "comparison_results" in st.session_state:
        results = st.session_state.comparison_results

        from portfolio_simulator.visualization.charts import (
            drawdown_chart,
            portfolio_evolution_chart,
            rolling_volatility_chart,
        )
        from portfolio_simulator.visualization.tables import (
            multi_horizon_table,
            summary_stats_table,
        )

        tab1, tab2, tab3, tab4 = st.tabs(
            ["Evolution", "Summary", "Multi-Horizon", "Drawdown"]
        )

        with tab1:
            st.plotly_chart(
                portfolio_evolution_chart(results),
                width="stretch",
            )
        with tab2:
            st.dataframe(summary_stats_table(results), width="stretch")
        with tab3:
            st.dataframe(multi_horizon_table(results), width="stretch")
        with tab4:
            st.plotly_chart(
                drawdown_chart(results),
                width="stretch",
            )
