"""Portfolio Builder page -- search assets, set weights, save portfolios."""

from __future__ import annotations

import streamlit as st

from portfolio_simulator.domain.asset import Asset
from portfolio_simulator.domain.enums import AssetType, Currency
from portfolio_simulator.domain.portfolio import Portfolio, PortfolioAllocation
from portfolio_simulator.ui.components.asset_picker import asset_search
from portfolio_simulator.ui.components.weight_editor import clear_weight_state, weight_editor


def _get_provider():
    from portfolio_simulator.services import get_provider
    provider_name = st.session_state.get("provider_name", "yahoo")
    return get_provider(provider_name)


def _get_store():
    from portfolio_simulator.services import get_portfolio_store
    return get_portfolio_store()


def render() -> None:
    st.header("Portfolio Builder")

    st.caption(
        "Build a portfolio by searching for assets and setting their target weights. "
        "Saved portfolios can be used in the Backtest, Comparison, and Optimizer views."
    )
    with st.expander("How Portfolio Builder works"):
        st.markdown(
            """
            **What it does:** Lets you assemble a multi-asset portfolio by searching a
            universe of stocks, ETFs, and other instruments, then assigning each asset a
            target weight. The saved portfolio becomes the input to every other analysis
            in the app.

            **Workflow:**
            1. Search for an asset (name or ticker) — autocomplete suggests matches.
            2. Confirm the selection (you'll see a preview card) and click **Add to Portfolio**.
            3. Adjust weights in the weight editor — the sum must equal 100%.
            4. Give the portfolio a name, pick a base currency, and click **Save Portfolio**.

            **Weights:** Represent the target allocation at each rebalance. Actual weights
            drift between rebalance dates as asset prices change. Rebalancing frequency is
            set later, in the Backtest view.

            **Base currency:** All returns, values, and performance metrics are reported
            in this currency. FX conversions are applied automatically when an asset trades
            in a different currency.

            **TER (Total Expense Ratio):** An annual fee charged by fund managers
            (ETFs/mutual funds). When present and enabled in the backtest, it's deducted
            daily from the asset's return as `ter / 252`.
            """
        )

    provider = _get_provider()
    store = _get_store()
    user_id = st.session_state.get("user_id", "local")

    # Initialize session state for portfolio building
    if "builder_assets" not in st.session_state:
        st.session_state.builder_assets = []

    # --- Asset Search ---
    st.subheader("Add Assets")
    from portfolio_simulator.ui.components.provider_selector import PROVIDER_META
    _meta = PROVIDER_META.get(st.session_state.get("provider_name", "yahoo"), {})
    if _meta:
        st.caption(
            f"Assets are searched in **{_meta['display_name']}**. "
            f"Change the data source in the sidebar."
        )
    selected = asset_search(provider, key="builder")

    # Capture new selection into session state so it persists across reruns
    # until the user adds it or clears it. Fixes the UX issue where the
    # searchbox clears on submit, leaving no visible trace of the selection.
    if selected is not None:
        st.session_state["pending_asset"] = selected

    pending = st.session_state.get("pending_asset")
    if pending is not None:
        st.success(
            f"Selected: **{pending.ticker}** — {pending.name}  \n"
            f"Type: `{pending.asset_type.value}` · Currency: `{pending.currency}`"
            + (f" · TER: `{(pending.ter or 0) * 100:.2f}%`" if pending.ter else "")
        )
        col_add, col_clear = st.columns([1, 1])
        with col_add:
            if st.button("Add to Portfolio", type="primary", use_container_width=True):
                existing = {a["ticker"] for a in st.session_state.builder_assets}
                if pending.ticker not in existing:
                    existing_total = sum(a.get("weight", 0.0) for a in st.session_state.builder_assets)
                    default_weight = max(0.0, 1.0 - existing_total)
                    # Drop any stale widget state from a prior add/remove cycle
                    # so the editor seeds from default_weight, not the old value.
                    clear_weight_state(pending.ticker)
                    st.session_state.builder_assets.append({
                        "ticker": pending.ticker,
                        "name": pending.name,
                        "asset_type": pending.asset_type.value,
                        "currency": pending.currency,
                        "ter": pending.ter or 0.0,
                        "weight": default_weight,
                    })
                    del st.session_state["pending_asset"]
                    st.rerun()
                else:
                    st.warning(f"{pending.ticker} is already in the portfolio.")
        with col_clear:
            if st.button("Clear selection", use_container_width=True):
                del st.session_state["pending_asset"]
                st.rerun()

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
            clear_weight_state(to_remove)
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
