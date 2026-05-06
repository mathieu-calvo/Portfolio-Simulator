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
    from portfolio_simulator.services import get_data_service, get_portfolio_store
    from portfolio_simulator.services.backtest_engine import BacktestEngine

    provider_name = st.session_state.get("provider_name", "yahoo")
    data_service = get_data_service(provider_name)
    engine = BacktestEngine(data_service)
    store = get_portfolio_store()
    return engine, store, data_service


def render() -> None:
    st.header("Backtest")

    st.caption(
        "Run a historical simulation of a saved portfolio with configurable "
        "rebalancing, contributions, fees, and taxes."
    )
    with st.expander("How Backtest works"):
        st.markdown(
            """
            **What it does:** Replays your portfolio over history using real daily prices,
            applying your chosen rebalancing rule, recurring investment schedule, and
            cost assumptions. Outputs performance metrics and diagnostic charts.

            **How it works:**
            1. Downloads historical daily prices for every asset in the portfolio.
            2. Starts on the selected start date with the initial investment, allocated
               according to the target weights.
            3. Applies **recurring contributions** (if enabled) at the chosen cadence.
            4. **Rebalances** according to the chosen rule:
               - **None:** weights drift freely.
               - **Calendar:** snap back to target at fixed intervals (monthly/quarterly/yearly).
               - **Tolerance:** rebalance only when any asset drifts beyond the tolerance band.
            5. Applies **costs** at each transaction (transaction cost, management fee,
               TER, and tax on realized gains) and produces the final P&L path.

            **Key metrics:**
            - **Annualized Return:** Geometric mean annual return over the period.
            - **Sharpe Ratio:** `(excess return) / volatility`. Risk-adjusted return.
            - **Sortino Ratio:** Same but penalizes only downside volatility.
            - **Max Drawdown:** Largest peak-to-trough loss in the equity curve.
            - **VaR (95%):** 95th-percentile worst daily loss — historical estimate.

            **Caveats:**
            - Past performance is not predictive of future returns.
            - Survivorship bias: only currently-listed tickers are available.
            - Tax treatment is simplified (flat rate on realized gains, not
              jurisdiction-specific).
            """
        )

    engine, store, data_service = _get_services()
    user_id = st.session_state.get("user_id", "local")
    portfolios = store.list_all(user_id)

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
            disabled=rebalance_strategy != "calendar",
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
            weight_drift_chart,
        )
        from portfolio_simulator.analytics.returns import monthly_returns

        render_metric_cards(result)

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
            [
                "Evolution",
                "Drawdown",
                "Weight Drift",
                "Monthly Returns",
                "Returns Heatmap",
                "Rolling Volatility",
            ]
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
            show_rebals = st.checkbox(
                "Overlay rebalance dates",
                value=True,
                key="bt_wd_show_rebals",
                help="Vertical dotted lines mark each rebalance — jumps in composition "
                     "right at a line are due to the rebalance, anything else is drift.",
            )
            st.plotly_chart(
                weight_drift_chart(result, show_rebalances=show_rebals),
                width="stretch",
            )
        with tab4:
            m_ret = monthly_returns(result.portfolio_value)
            st.plotly_chart(
                monthly_returns_histogram(m_ret),
                width="stretch",
            )
        with tab5:
            m_ret = monthly_returns(result.portfolio_value)
            st.plotly_chart(
                returns_heatmap(m_ret),
                width="stretch",
            )
        with tab6:
            st.plotly_chart(
                rolling_volatility_chart([result]),
                width="stretch",
            )

        # --- Raw Data Export ---
        _render_export_section(result, portfolio, data_service)


def _weights_with_rebal_flag(result) -> "pd.DataFrame":
    """Return the asset_weights_over_time DataFrame with a 'rebalance' boolean column."""
    import pandas as pd

    df = result.asset_weights_over_time.copy()
    rebal_set = {pd.Timestamp(d).normalize() for d in result.rebalance_dates}
    df["rebalance"] = pd.Index(df.index).normalize().isin(rebal_set)
    return df


def _render_export_section(result, portfolio, data_service) -> None:
    """Render a collapsible section to inspect and export raw backtest data."""
    import pandas as pd

    from portfolio_simulator.ui.components.data_export import download_excel_button

    st.divider()
    with st.expander("View & export raw data"):
        st.caption(
            "Inspect the underlying time series used in this backtest and download "
            "them as Excel files for further analysis."
        )

        show_full = st.checkbox(
            "Show full table in previews",
            value=False,
            key="bt_export_show_full",
            help="Off: previews show the last 250 rows. On: previews show every row "
                 "(can be slow for very long backtests).",
        )
        preview = (lambda df: df) if show_full else (lambda df: df.tail(250))

        data_tab1, data_tab2, data_tab3, data_tab4 = st.tabs(
            ["Portfolio Time Series", "Asset Weights", "Asset Prices", "Asset Returns"]
        )

        # Portfolio-level outputs — always available from the result object
        with data_tab1:
            portfolio_df = pd.DataFrame({
                "portfolio_value": result.portfolio_value,
                "daily_return": result.daily_returns,
            })
            st.dataframe(preview(portfolio_df), use_container_width=True)
            if not show_full:
                st.caption(f"Showing last 250 of {len(portfolio_df)} rows. Toggle above for full table.")
            else:
                st.caption(f"Showing all {len(portfolio_df)} rows.")
            download_excel_button(
                label="Download portfolio time series (.xlsx)",
                sheets={
                    "Portfolio Value": result.portfolio_value.to_frame("value"),
                    "Daily Returns": result.daily_returns.to_frame("return"),
                    "Asset Weights": _weights_with_rebal_flag(result),
                },
                filename=f"{result.portfolio_name}_portfolio.xlsx",
                key="bt_dl_portfolio",
                help="Multi-sheet workbook: portfolio value, daily returns, and asset weight trajectories.",
            )

        with data_tab2:
            weights_df = _weights_with_rebal_flag(result)
            st.dataframe(preview(weights_df), use_container_width=True)
            if not show_full:
                st.caption(
                    f"Showing last 250 of {len(weights_df)} rows. "
                    f"`rebalance = True` flags days where the portfolio was rebalanced "
                    f"to target weights ({len(result.rebalance_dates)} total)."
                )
            else:
                st.caption(
                    f"Showing all {len(weights_df)} rows. "
                    f"{len(result.rebalance_dates)} rebalance days flagged."
                )
            download_excel_button(
                label="Download asset weights (.xlsx)",
                sheets={"Asset Weights": weights_df},
                filename=f"{result.portfolio_name}_asset_weights.xlsx",
                key="bt_dl_weights",
                help="Daily actual weights per asset, with a boolean column flagging rebalance dates.",
            )

        # Asset-level data — fetched from the cache via data_service
        with data_tab3:
            try:
                prices = data_service.get_prices_bulk(
                    portfolio.tickers,
                    result.config.start_date,
                    result.config.end_date,
                )
                st.dataframe(preview(prices), use_container_width=True)
                if not show_full:
                    st.caption(f"Showing last 250 of {len(prices)} rows. Toggle above for full table.")
                else:
                    st.caption(f"Showing all {len(prices)} rows.")
                download_excel_button(
                    label="Download asset prices (.xlsx)",
                    sheets={"Asset Prices": prices},
                    filename=f"{result.portfolio_name}_asset_prices.xlsx",
                    key="bt_dl_prices",
                    help="Daily prices for every asset in the portfolio.",
                )
            except Exception as e:
                st.error(f"Could not load asset prices: {e}")

        with data_tab4:
            try:
                prices = data_service.get_prices_bulk(
                    portfolio.tickers,
                    result.config.start_date,
                    result.config.end_date,
                )
                returns = prices.pct_change().dropna(how="all")
                st.dataframe(preview(returns), use_container_width=True)
                if not show_full:
                    st.caption(f"Showing last 250 of {len(returns)} rows. Toggle above for full table.")
                else:
                    st.caption(f"Showing all {len(returns)} rows.")
                download_excel_button(
                    label="Download asset returns (.xlsx)",
                    sheets={"Asset Returns": returns},
                    filename=f"{result.portfolio_name}_asset_returns.xlsx",
                    key="bt_dl_returns",
                    help="Daily percentage returns for every asset in the portfolio.",
                )
            except Exception as e:
                st.error(f"Could not compute asset returns: {e}")
