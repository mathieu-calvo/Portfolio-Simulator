"""Portfolio Builder page -- search assets, set weights, save portfolios."""

from __future__ import annotations

import streamlit as st

from portfolio_simulator.domain.asset import Asset
from portfolio_simulator.domain.enums import AssetType, Currency
from portfolio_simulator.domain.portfolio import Portfolio, PortfolioAllocation
from portfolio_simulator.ui.components.asset_picker import asset_search
from portfolio_simulator.ui.components.weight_editor import weight_editor


def _get_provider():
    from portfolio_simulator.providers.yahoo import YahooFinanceProvider
    return YahooFinanceProvider()


def _get_store():
    from portfolio_simulator.services import get_portfolio_store
    return get_portfolio_store()


def render() -> None:
    st.header("Portfolio Builder")

    provider = _get_provider()
    store = _get_store()
    user_id = st.session_state.get("user_id", "local")

    # Initialize session state for portfolio building
    if "builder_assets" not in st.session_state:
        st.session_state.builder_assets = []

    # --- Asset Search ---
    st.subheader("Add Assets")
    selected = asset_search(provider, key="builder")

    if selected and st.button("Add to Portfolio"):
        # Avoid duplicates
        existing = {a["ticker"] for a in st.session_state.builder_assets}
        if selected.ticker not in existing:
            st.session_state.builder_assets.append({
                "ticker": selected.ticker,
                "name": selected.name,
                "asset_type": selected.asset_type.value,
                "currency": selected.currency,
                "ter": selected.ter or 0.0,
                "weight": 0.0,
            })
            st.rerun()
        else:
            st.warning(f"{selected.ticker} is already in the portfolio.")

    # --- Weight Editor ---
    if st.session_state.builder_assets:
        st.divider()
        updated = weight_editor(st.session_state.builder_assets, key="builder_weights")
        st.session_state.builder_assets = updated

        # Remove asset
        to_remove = st.selectbox(
            "Remove asset",
            ["-- None --"] + [a["ticker"] for a in updated],
            key="remove_asset",
        )
        if to_remove != "-- None --" and st.button("Remove"):
            st.session_state.builder_assets = [a for a in updated if a["ticker"] != to_remove]
            st.rerun()

    # --- Save ---
    st.divider()
    st.subheader("Save Portfolio")
    name = st.text_input("Portfolio name", key="portfolio_name")
    currency = st.selectbox("Base currency", [c.value for c in Currency], key="portfolio_currency")

    if st.button("Save Portfolio", type="primary"):
        assets_data = st.session_state.builder_assets
        if not name:
            st.error("Please enter a portfolio name.")
        elif not assets_data:
            st.error("Please add at least one asset.")
        else:
            total_weight = sum(a["weight"] for a in assets_data)
            if abs(total_weight - 1.0) >= 0.01:
                st.error(f"Weights must sum to 100% (currently {total_weight:.1%})")
            else:
                try:
                    allocations = [
                        PortfolioAllocation(
                            asset=Asset(
                                ticker=a["ticker"],
                                name=a["name"],
                                asset_type=a["asset_type"],
                                currency=a.get("currency", "USD"),
                                ter=a.get("ter", 0.0),
                            ),
                            weight=a["weight"],
                        )
                        for a in assets_data
                    ]
                    portfolio = Portfolio(
                        name=name,
                        allocations=allocations,
                        base_currency=currency,
                    )
                    store.save(portfolio, user_id)
                    st.success(f"Portfolio '{name}' saved!")
                    st.session_state.builder_assets = []
                except Exception as e:
                    st.error(f"Error saving portfolio: {e}")

    # --- Existing Portfolios ---
    st.divider()
    st.subheader("Saved Portfolios")
    portfolios = store.list_all(user_id)
    if not portfolios:
        st.info("No portfolios saved yet.")
    else:
        for p in portfolios:
            with st.expander(f"{p.name} ({p.base_currency.value})"):
                for a in p.allocations:
                    st.text(f"  {a.asset.ticker} ({a.asset.name}): {a.weight:.1%}")
                if st.button(f"Delete {p.name}", key=f"del_{p.name}"):
                    store.delete(p.name, user_id)
                    st.rerun()
