"""Backtest page -- configure and run simulation, view results."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from portfolio_simulator.domain.enums import (
    InvestmentStrategy,
    RebalanceFrequency,
    RebalanceStrategy,
)
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
    st.header("Backtest")

    engine, store = _get_services()
    portfolios = store.list_all()

    if not portfolios:
        st.info("No portfolios saved yet. Go to Portfolio Builder to create one.")
        return

    # --- Portfolio Selection ---
    portfolio_names = [p.name for p in portfolios]
    selected_name = st.selectbox("Select portfolio", portfolio_names)
    portfolio = next(p for p in portfolios if p.name == selected_name)

    # --- Configuration ---
    st.subheader("Simulation Parameters")
    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input("Start date", value=date(2015, 1, 1))
        end_date = st.date_input("End date", value=date.today() - timedelta(days=1))
        initial_investment = st.number_input(
            "Initial investment ($)", value=10000, min_value=0, step=1000
        )

    with col2:
        rebalance_strategy = st.selectbox(
            "Rebalancing strategy",
            [s.value for s in RebalanceStrategy],
            format_func=lambda x: x.replace("_", " ").title(),
        )
        rebalance_freq = st.selectbox(
            "Rebalancing frequency",
            [f.value for f in RebalanceFrequency],
            format_func=lambda x: x.replace("_", " ").title(),
            disabled=rebalance_strategy == "none",
        )
        rebalance_tol = st.slider(
            "Rebalancing tolerance",
            0.01, 0.50, 0.05, 0.01,
            disabled=rebalance_strategy != "tolerance",
        )

    with st.expander("Advanced Settings"):
        col3, col4 = st.columns(2)
        with col3:
            investment_strategy = st.selectbox(
                "Investment strategy",
                [s.value for s in InvestmentStrategy],
                format_func=lambda x: x.replace("_", " ").title(),
            )
            recurring = st.number_input(
                "Monthly contribution ($)",
                value=0, min_value=0, step=100,
                disabled=investment_strategy == "lump_sum",
            )
        with col4:
            transaction_cost = st.number_input(
                "Transaction cost (%)", value=0.0, min_value=0.0, step=0.01, format="%.2f"
            )
            management_fee = st.number_input(
                "Management fee (% p.a.)", value=0.0, min_value=0.0, step=0.01, format="%.2f"
            )
            tax_rate = st.number_input(
                "Tax rate on gains (%)", value=0.0, min_value=0.0, step=1.0, format="%.1f"
            )
            include_ter = st.checkbox("Include TER in simulation", value=True)

    # --- Run Backtest ---
    if st.button("Run Backtest", type="primary"):
        config = SimulationConfig(
            start_date=start_date,
            end_date=end_date,
            initial_investment=float(initial_investment),
            recurring_investment=float(recurring),
            investment_strategy=investment_strategy,
            rebalance_strategy=rebalance_strategy,
            rebalance_frequency=rebalance_freq,
            rebalance_tolerance=rebalance_tol,
            transaction_cost_pct=transaction_cost / 100,
            management_fee_pct=management_fee / 100,
            tax_rate_pct=tax_rate / 100,
            include_ter=include_ter,
        )

        with st.spinner("Running backtest..."):
            try:
                result = engine.run(portfolio, config)
                st.session_state.backtest_result = result
            except Exception as e:
                st.error(f"Backtest failed: {e}")
                return

    # --- Display Results ---
    if "backtest_result" in st.session_state:
        result = st.session_state.backtest_result

        from portfolio_simulator.ui.components.metric_cards import render_metric_cards
        from portfolio_simulator.visualization.charts import (
            drawdown_chart,
            monthly_returns_histogram,
            portfolio_evolution_chart,
            returns_heatmap,
            rolling_volatility_chart,
        )
        from portfolio_simulator.analytics.returns import monthly_returns

        render_metric_cards(result)

        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            ["Evolution", "Drawdown", "Monthly Returns", "Returns Heatmap", "Rolling Volatility"]
        )

        with tab1:
            st.plotly_chart(
                portfolio_evolution_chart([result]),
                width="stretch",
            )
        with tab2:
            st.plotly_chart(
                drawdown_chart([result]),
                width="stretch",
            )
        with tab3:
            m_ret = monthly_returns(result.portfolio_value)
            st.plotly_chart(
                monthly_returns_histogram(m_ret),
                width="stretch",
            )
        with tab4:
            m_ret = monthly_returns(result.portfolio_value)
            st.plotly_chart(
                returns_heatmap(m_ret),
                width="stretch",
            )
        with tab5:
            st.plotly_chart(
                rolling_volatility_chart([result]),
                width="stretch",
            )
