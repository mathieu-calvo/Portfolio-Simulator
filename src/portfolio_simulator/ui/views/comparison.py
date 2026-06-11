"""Comparison page -- compare multiple portfolios side by side."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from portfolio_simulator.domain.enums import RebalanceFrequency, RebalanceStrategy
from portfolio_simulator.domain.simulation import SimulationConfig
from portfolio_simulator.utils.currency import currency_symbol


def _get_services():
    from portfolio_simulator.services import get_data_service, get_portfolio_store
    from portfolio_simulator.services.backtest_engine import BacktestEngine

    provider_name = st.session_state.get("provider_name", "yahoo")
    data_service = get_data_service(provider_name)
    engine = BacktestEngine(data_service)
    store = get_portfolio_store()
    return engine, store, data_service


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
              windows (YTD, 1Y, 3Y, 5Y, 10Y, full period), plus a calendar-year returns
              table. Useful for spotting whether a portfolio's edge is recent or durable.
            - **Drawdown:** Drawdown curves overlaid — the shallower the drawdowns, the
              better the downside protection.
            - **Weight Drift:** Stacked area per portfolio with rebalance dates marked,
              so you can see how each portfolio's composition evolved.

            **Align start dates:** When portfolios have different price-history depths,
            tick "Align start dates" to truncate everyone to the latest common start and
            rebase to the initial investment — better for fair visual comparison.
            """
        )

    engine, store, data_service = _get_services()
    user_id = st.session_state.get("user_id", "local")
    portfolios = store.list_all(user_id)

    if len(portfolios) < 2:
        st.info("Save at least 2 portfolios to compare. Go to Portfolio Builder.")
        return

    # --- Select Portfolios ---
    # Streamlit auto-purges keyed widget state when the widget unmounts (e.g.
    # navigating to a different page). Mirror the selection into a non-widget
    # key and only rehydrate when cmp_selected is missing — otherwise we'd
    # clobber the user's in-flight changes on every rerun.
    names = [p.name for p in portfolios]
    if "cmp_selected" not in st.session_state:
        st.session_state["cmp_selected"] = [
            n for n in st.session_state.get("cmp_selected_persistent", []) if n in names
        ]
    selected = st.multiselect(
        "Select portfolios to compare (2-5)",
        names,
        max_selections=5,
        key="cmp_selected",
    )
    st.session_state["cmp_selected_persistent"] = selected

    if len(selected) < 2:
        st.info("Select at least 2 portfolios.")
        return

    selected_portfolios = [p for p in portfolios if p.name in selected]
    currencies = {p.base_currency.value for p in selected_portfolios}
    shared_ccy = next(iter(currencies)) if len(currencies) == 1 else None
    sym = currency_symbol(shared_ccy)
    if shared_ccy is None and len(currencies) > 1:
        st.caption(
            "Selected portfolios use different base currencies — the initial "
            "investment below is interpreted in each portfolio's own currency."
        )

    # --- Shared Config ---
    st.subheader("Simulation Parameters")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start date",
            value=date(2015, 1, 1),
            min_value=date(1900, 1, 1),
            key="cmp_start",
        )
        end_date = st.date_input(
            "End date",
            value=date.today() - timedelta(days=1),
            min_value=date(1900, 1, 1),
            key="cmp_end",
        )
        initial = st.number_input(
            f"Initial investment ({sym.strip() or '$'})",
            value=10000, min_value=0, step=1000, key="cmp_init",
        )
    with col2:
        rebal = st.selectbox(
            "Rebalancing strategy",
            [s.value for s in RebalanceStrategy],
            format_func=lambda x: x.replace("_", " ").title(),
            key="cmp_rebal",
        )
        freq = st.selectbox(
            "Rebalancing frequency",
            [f.value for f in RebalanceFrequency],
            format_func=lambda x: x.replace("_", " ").title(),
            disabled=rebal != "calendar",
            key="cmp_freq",
        )
        tol = st.slider(
            "Rebalancing tolerance",
            0.01, 0.50, 0.05, 0.01,
            disabled=rebal != "tolerance",
            key="cmp_tol",
        )

    config = SimulationConfig(
        start_date=start_date,
        end_date=end_date,
        initial_investment=float(initial),
        rebalance_strategy=rebal,
        rebalance_frequency=freq,
        rebalance_tolerance=tol,
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

        from portfolio_simulator.analytics.comparison import align_results
        from portfolio_simulator.visualization.charts import (
            drawdown_chart,
            portfolio_evolution_chart,
            weight_drift_comparison_chart,
        )
        from portfolio_simulator.visualization.tables import (
            calendar_year_returns_table,
            multi_horizon_table,
            summary_stats_table,
        )

        # Detect mismatched start dates and offer alignment
        first_dates = [r.portfolio_value.index[0] for r in results]
        starts_differ = len(set(first_dates)) > 1
        if starts_differ:
            st.info(
                "Portfolios have different first available dates — toggle "
                "**Align start dates** below for a like-for-like visual comparison."
            )
        align = st.checkbox(
            "Align start dates (truncate to latest common start, rebase to initial investment)",
            value=False,
            key="cmp_align",
            disabled=not starts_differ,
        )
        display_results = align_results(results) if align else results

        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            ["Evolution", "Summary", "Multi-Horizon", "Drawdown", "Weight Drift"]
        )

        with tab1:
            st.plotly_chart(
                portfolio_evolution_chart(display_results),
                width="stretch",
            )
        with tab2:
            st.dataframe(summary_stats_table(display_results), width="stretch")
        with tab3:
            st.markdown("**Standard horizons**")
            st.caption(
                "Annualized and cumulative returns plus annualized volatility for each "
                "portfolio across the standard lookback windows."
            )
            st.dataframe(multi_horizon_table(display_results), width="stretch")
            st.markdown("**Calendar year returns**")
            st.caption(
                "Total return for each calendar year. Partial years (the first and "
                "last in the backtest window) reflect only the days actually covered."
            )
            st.dataframe(
                calendar_year_returns_table(display_results), width="stretch"
            )
        with tab4:
            st.plotly_chart(
                drawdown_chart(display_results),
                width="stretch",
            )
        with tab5:
            show_rebals = st.checkbox(
                "Overlay rebalance dates",
                value=True,
                key="cmp_wd_show_rebals",
                help="Vertical dotted lines mark each rebalance per portfolio. Same color "
                     "= same ticker across subplots.",
            )
            st.plotly_chart(
                weight_drift_comparison_chart(display_results, show_rebalances=show_rebals),
                width="stretch",
            )

        # --- Raw Data Export ---
        _render_export_section(display_results, selected_portfolios, data_service)


def _weights_with_rebal_flag(result) -> "pd.DataFrame":
    """Return a result's weights DataFrame with a 'rebalance' boolean column."""
    import pandas as pd

    df = result.asset_weights_over_time.copy()
    rebal_set = {pd.Timestamp(d).normalize() for d in result.rebalance_dates}
    df["rebalance"] = pd.Index(df.index).normalize().isin(rebal_set)
    return df


def _render_export_section(results, selected_portfolios, data_service) -> None:
    """Render a collapsible section to inspect and export comparison data."""
    import pandas as pd

    from portfolio_simulator.ui.components.data_export import download_excel_button

    st.divider()
    with st.expander("View & export raw data"):
        st.caption(
            "Inspect the underlying time series used in this comparison and download "
            "them as Excel files for further analysis."
        )

        show_full = st.checkbox(
            "Show full table in previews",
            value=False,
            key="cmp_export_show_full",
            help="Off: previews show the last 250 rows. On: previews show every row.",
        )
        preview = (lambda df: df) if show_full else (lambda df: df.tail(250))

        # Build combined value/return DataFrames
        values_df = pd.DataFrame({r.portfolio_name: r.portfolio_value for r in results})
        returns_df = pd.DataFrame({r.portfolio_name: r.daily_returns for r in results})

        data_tab1, data_tab2, data_tab3 = st.tabs(
            ["Portfolio Values & Returns", "Asset Weights", "Asset Prices"]
        )

        with data_tab1:
            st.markdown("**Portfolio Values**")
            st.dataframe(preview(values_df), use_container_width=True)
            if not show_full:
                st.caption(f"Showing last 250 of {len(values_df)} rows. Toggle above for full table.")
            else:
                st.caption(f"Showing all {len(values_df)} rows.")

            download_excel_button(
                label="Download comparison time series (.xlsx)",
                sheets={
                    "Portfolio Values": values_df,
                    "Daily Returns": returns_df,
                },
                filename="portfolio_comparison.xlsx",
                key="cmp_dl_values",
                help="Multi-sheet workbook with portfolio values and daily returns.",
            )

        with data_tab2:
            st.caption(
                "Daily actual weights for each portfolio, with a `rebalance` boolean "
                "column flagging the days a rebalance fired."
            )
            sheets: dict[str, pd.DataFrame] = {}
            for r in results:
                weights_df = _weights_with_rebal_flag(r)
                sheets[f"{r.portfolio_name} Weights"] = weights_df
                with st.expander(f"Preview: {r.portfolio_name} ({len(r.rebalance_dates)} rebalances)"):
                    st.dataframe(preview(weights_df), use_container_width=True)

            download_excel_button(
                label="Download all asset weights (.xlsx)",
                sheets=sheets,
                filename="comparison_asset_weights.xlsx",
                key="cmp_dl_weights",
                help="One sheet per portfolio with actual daily weights and a rebalance flag.",
            )

        with data_tab3:
            st.caption(
                "Asset-level prices for every portfolio in the comparison, fetched "
                "from the selected data source (cached)."
            )
            try:
                cfg = results[0].config
                sheets = {}
                for portfolio in selected_portfolios:
                    prices = data_service.get_prices_bulk(
                        portfolio.tickers, cfg.start_date, cfg.end_date
                    )
                    sheets[f"{portfolio.name} Prices"] = prices
                    with st.expander(f"Preview: {portfolio.name}"):
                        st.dataframe(preview(prices), use_container_width=True)

                download_excel_button(
                    label="Download all asset prices (.xlsx)",
                    sheets=sheets,
                    filename="comparison_asset_prices.xlsx",
                    key="cmp_dl_prices",
                    help="One sheet per portfolio, containing daily asset prices.",
                )
            except Exception as e:
                st.error(f"Could not load asset prices: {e}")
