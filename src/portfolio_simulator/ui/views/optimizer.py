"""Optimizer page -- efficient frontier and Monte Carlo projections."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st


def _get_services():
    from portfolio_simulator.services import get_data_service, get_portfolio_store

    provider_name = st.session_state.get("provider_name", "yahoo")
    data_service = get_data_service(provider_name)
    store = get_portfolio_store()
    return data_service, store


def render() -> None:
    st.header("Portfolio Optimizer")

    st.caption(
        "Explore the efficient frontier of your portfolio's assets and project future "
        "outcomes using Monte Carlo simulation."
    )

    data_service, store = _get_services()
    user_id = st.session_state.get("user_id", "local")
    portfolios = store.list_all(user_id)

    if not portfolios:
        st.info("Save a portfolio first to run optimization and projections.")
        return

    tab1, tab2 = st.tabs(["Efficient Frontier", "Monte Carlo Projection"])

    # --- Efficient Frontier ---
    with tab1:
        st.subheader("Efficient Frontier Analysis")
        st.caption(
            "Finds the portfolios with the best possible risk/return trade-off for "
            "your asset universe, based on historical returns and covariances."
        )
        with st.expander("How Efficient Frontier works"):
            st.markdown(
                """
                **What it does:** Computes the set of portfolio weights that achieve the
                lowest possible volatility for each level of expected return — the classic
                Markowitz (1952) efficient frontier. Two special points are highlighted:

                - **Max Sharpe Portfolio:** The tangency portfolio — the mix that
                  maximizes the Sharpe ratio `(return − risk_free) / volatility`. This is
                  the "best" risk-adjusted portfolio under mean-variance assumptions.
                - **Min Volatility Portfolio:** The global minimum variance portfolio —
                  the lowest-risk combination of your assets regardless of return.

                **How it works:**
                1. Daily returns are computed for each asset over the selected date range.
                2. Expected returns are annualized means; the covariance matrix is
                   annualized using 252 trading days.
                3. A quadratic optimizer finds weights that minimize variance subject to
                   `sum(w) = 1`, `w >= 0` (no short selling) for each target return.
                4. The frontier is the envelope of these optimal portfolios.

                **Caveats:**
                - Uses **historical** returns as a proxy for expected future returns —
                  this is noisy and backward-looking.
                - Assumes returns are normally distributed and correlations are stable.
                - Small changes in inputs can produce large weight shifts (classic
                  Markowitz sensitivity problem).
                - No transaction costs, taxes, or constraints beyond long-only.
                """
            )

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
        st.caption(
            "Projects thousands of possible future paths for your portfolio based on "
            "the return distribution observed in the most recent backtest."
        )
        with st.expander("How Monte Carlo projection works"):
            st.markdown(
                """
                **What it does:** Takes the daily return distribution from your latest
                backtest and simulates thousands of possible future paths for the
                portfolio value. It answers: "If the future looks like the past, what
                range of outcomes could I expect?"

                **How it works:**
                1. Daily returns from the backtest are sampled with replacement
                   (bootstrap) to build each future path.
                2. Each scenario is compounded forward for the selected horizon, with
                   optional monthly contributions added.
                3. At every future date, the 5th, 25th, 50th (median), 75th, and 95th
                   percentiles across all scenarios are reported.

                **Interpreting the results:**
                - **P5 (Very Bad):** 5% of scenarios ended at or below this value. A
                  rough "worst plausible case".
                - **Median:** The middle outcome — half of scenarios ended above, half below.
                - **P95 (Great):** Only 5% of scenarios exceeded this. A "best plausible case".

                **Caveats:**
                - Bootstrap assumes historical returns are representative of the future —
                  it cannot predict regime changes, crises, or structural shifts.
                - Daily returns are sampled independently, so some autocorrelation and
                  volatility clustering present in real markets is lost.
                - The projection starts from the **final value** of the backtest, not
                  today's market price.
                """
            )

        if "backtest_result" not in st.session_state:
            st.info("Run a backtest first to generate Monte Carlo projections.")
            return

        from portfolio_simulator.domain.results import BacktestResult

        bt_result: BacktestResult = st.session_state.backtest_result

        # Make the input portfolio explicit — users were confused about which
        # portfolio the projection was based on.
        st.info(
            f"Projecting **{bt_result.portfolio_name}** forward from its final "
            f"backtest value of **${float(bt_result.portfolio_value.iloc[-1]):,.0f}** "
            f"(as of {bt_result.portfolio_value.index[-1].date()}). "
            f"Run a new backtest in the Backtest view to change the source portfolio."
        )

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
