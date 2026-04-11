"""Comparison page -- compare multiple portfolios side by side."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from portfolio_simulator.domain.enums import RebalanceFrequency, RebalanceStrategy
from portfolio_simulator.domain.simulation import SimulationConfig


def _get_services():
    from portfolio_simulator.config import settings
    from portfolio_simulator.providers.yahoo import YahooFinanceProvider
    from portfolio_simulator.services.backtest_engine import BacktestEngine
    from portfolio_simulator.services.data_service import DataService
    from portfolio_simulator.services.portfolio_store import PortfolioStore

    provider = YahooFinanceProvider()
    data_service = DataService(provider)
    engine = BacktestEngine(data_service)
    store = PortfolioStore(settings.db_path)
    return engine, store


def render() -> None:
    st.header("Portfolio Comparison")

    engine, store = _get_services()
    portfolios = store.list_all()

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
