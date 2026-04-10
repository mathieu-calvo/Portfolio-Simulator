"""Asset search and selection widget."""

from __future__ import annotations

import streamlit as st

from portfolio_simulator.providers.base import AssetInfo, DataProvider


def asset_search(
    provider: DataProvider,
    key: str = "asset_search",
) -> AssetInfo | None:
    """Render an asset search widget.

    Returns the selected AssetInfo or None if nothing selected.
    """
    query = st.text_input("Search assets (name or ticker)", key=f"{key}_query")
    if not query:
        return None

    results = provider.search_assets(query, limit=10)
    if not results:
        st.warning("No assets found.")
        return None

    options = {f"{a.ticker} - {a.name} ({a.asset_type.value})": a for a in results}
    selected = st.selectbox("Select asset", list(options.keys()), key=f"{key}_select")

    if selected:
        return options[selected]
    return None
