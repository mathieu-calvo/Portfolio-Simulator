"""Optimizer page -- efficient frontier and Monte Carlo projections."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st


def _get_services():
    from portfolio_simulator.config import settings
    from portfolio_simulator.providers.yahoo import YahooFinanceProvider
    from portfolio_simulator.services.data_service import DataService
    from portfolio_simulator.services.portfolio_store import PortfolioStore

    provider = YahooFinanceProvider()
    data_service = DataService(provider)
    store = PortfolioStore(settings.db_path)
    return data_service, store


def render() -> None:
    st.header("Portfolio Optimizer")

    data_service, store = _get_services()
    portfolios = store.list_all()

    if not portfolios:
        st.info("Save a portfolio first to run optimization and projections.")
        return

    tab1, tab2 = st.tabs(["Efficient Frontier", "Monte Carlo Projection"])

    # --- Efficient Frontier ---
    with tab1:
        st.subheader("Efficient Frontier Analysis")
        portfolio_names = [p.name for p in portfolios]
        selected_name = st.selectbox("Select portfolio", portfolio_names, key="opt_select")
        portfolio = next(p for p in portfolios if p.name == selected_name)

        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start date", value=date(2015, 1, 1), key="opt_start")
        with col2:
            end_date = st.date_input("End date", value=date.today() - timedelta(days=1), key="opt_end")

        if st.button("Compute Frontier", type="primary"):
            with st.spinner("Computing efficient frontier..."):
                try:
                    prices = data_service.get_prices_bulk(
                        portfolio.tickers, start_date, end_date
                    ).dropna()

                    from portfolio_simulator.analytics.efficient_frontier import (
                        compute_efficient_frontier,
                    )
                    from portfolio_simulator.visualization.charts import (
                        efficient_frontier_chart,
                    )

                    result = compute_efficient_frontier(prices)
                    st.session_state.frontier_result = result
                except Exception as e:
                    st.error(f"Optimization failed: {e}")
                    return

        if "frontier_result" in st.session_state:
            result = st.session_state.frontier_result
            from portfolio_simulator.visualization.charts import efficient_frontier_chart

            st.plotly_chart(efficient_frontier_chart(result), width="stretch")

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Max Sharpe Portfolio")
                ms = result.max_sharpe_portfolio
                st.metric("Expected Return", f"{ms.expected_return:.2%}")
                st.metric("Volatility", f"{ms.volatility:.2%}")
                st.metric("Sharpe Ratio", f"{ms.sharpe_ratio:.2f}")
                for name, w in zip(result.asset_names, ms.weights):
                    st.text(f"  {name}: {w:.1%}")

            with col2:
                st.subheader("Min Volatility Portfolio")
                mv = result.min_volatility_portfolio
                st.metric("Expected Return", f"{mv.expected_return:.2%}")
                st.metric("Volatility", f"{mv.volatility:.2%}")
                for name, w in zip(result.asset_names, mv.weights):
                    st.text(f"  {name}: {w:.1%}")

    # --- Monte Carlo ---
    with tab2:
        st.subheader("Monte Carlo Projection")

        if "backtest_result" not in st.session_state:
            st.info("Run a backtest first to generate Monte Carlo projections.")
            return

        from portfolio_simulator.domain.results import BacktestResult

        bt_result: BacktestResult = st.session_state.backtest_result

        col1, col2, col3 = st.columns(3)
        with col1:
            n_years = st.slider("Projection horizon (years)", 1, 30, 10, key="mc_years")
        with col2:
            n_scenarios = st.number_input("Number of scenarios", 1000, 50000, 5000, step=1000, key="mc_n")
        with col3:
            monthly_contrib = st.number_input("Monthly contribution ($)", 0, 10000, 0, step=100, key="mc_contrib")

        if st.button("Run Monte Carlo", type="primary"):
            with st.spinner(f"Running {n_scenarios} scenarios..."):
                try:
                    from portfolio_simulator.analytics.monte_carlo import run_monte_carlo
                    from portfolio_simulator.visualization.charts import monte_carlo_chart

                    mc_result = run_monte_carlo(
                        bt_result.daily_returns,
                        n_scenarios=n_scenarios,
                        n_years=n_years,
                        initial_value=float(bt_result.portfolio_value.iloc[-1]),
                        monthly_contribution=float(monthly_contrib),
                    )
                    st.session_state.mc_result = mc_result
                except Exception as e:
                    st.error(f"Monte Carlo failed: {e}")
                    return

        if "mc_result" in st.session_state:
            mc_result = st.session_state.mc_result
            from portfolio_simulator.visualization.charts import monte_carlo_chart

            st.plotly_chart(monte_carlo_chart(mc_result), width="stretch")

            col1, col2, col3, col4, col5 = st.columns(5)
            final = mc_result.all_scenarios.iloc[-1]
            col1.metric("P5 (Very Bad)", f"${mc_result.percentile_5.iloc[-1]:,.0f}")
            col2.metric("P25 (Bad)", f"${mc_result.percentile_25.iloc[-1]:,.0f}")
            col3.metric("Median", f"${mc_result.median.iloc[-1]:,.0f}")
            col4.metric("P75 (Good)", f"${mc_result.percentile_75.iloc[-1]:,.0f}")
            col5.metric("P95 (Great)", f"${mc_result.percentile_95.iloc[-1]:,.0f}")
