"""Asset search and selection widget with autocomplete."""

from __future__ import annotations

import streamlit as st
from streamlit_searchbox import st_searchbox

from portfolio_simulator.providers.base import AssetInfo, DataProvider


def asset_search(
    provider: DataProvider,
    key: str = "asset_search",
) -> AssetInfo | None:
    """Render an asset search widget with autocomplete.

    Returns the selected AssetInfo or None if nothing selected.
    """

    def _search(query: str) -> list[tuple[str, AssetInfo]]:
        if not query or len(query) < 1:
            return []
        results = provider.search_assets(query, limit=10)
        return [
            (f"{a.ticker} - {a.name} ({a.asset_type.value})", a)
            for a in results
        ]

    selected: AssetInfo | None = st_searchbox(
        _search,
        placeholder="Search assets (name or ticker)...",
        key=f"{key}_searchbox",
        clear_on_submit=True,
    )

    return selected
