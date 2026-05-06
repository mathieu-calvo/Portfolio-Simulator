"""Portfolio weight allocation editor."""

from __future__ import annotations

import streamlit as st


def _slider_key(key: str, ticker: str) -> str:
    return f"{key}_slider_{ticker}"


def _input_key(key: str, ticker: str) -> str:
    return f"{key}_input_{ticker}"


def clear_weight_state(ticker: str, key: str = "builder_weights") -> None:
    """Drop session state for a ticker's weight widgets.

    Call this when an asset is removed (or about to be re-added) so the next
    render seeds widget state from the asset's stored weight rather than reusing
    a stale value from a previous lifecycle.
    """
    st.session_state.pop(_slider_key(key, ticker), None)
    st.session_state.pop(_input_key(key, ticker), None)


def weight_editor(
    assets: list[dict],
    key: str = "weights",
) -> list[dict]:
    """Render weight editing controls for portfolio assets.

    Args:
        assets: List of dicts with 'ticker', 'name', 'weight' keys.
        key: Unique key prefix for Streamlit widgets.

    Returns:
        Updated list with adjusted weights.
    """
    if not assets:
        st.info("Add assets to your portfolio to set weights.")
        return assets

    st.subheader("Allocation Weights")
    total = 0.0
    updated = []

    for asset in assets:
        ticker = asset["ticker"]
        sk = _slider_key(key, ticker)
        ik = _input_key(key, ticker)

        # Seed widget state from the asset's stored weight on first appearance.
        # After that, the widgets own their state and stay in sync via callbacks.
        if sk not in st.session_state:
            w = float(asset.get("weight", 0.0))
            st.session_state[sk] = w
            st.session_state[ik] = round(w * 100, 1)

        def _sync_from_slider(s=sk, i=ik):
            st.session_state[i] = round(st.session_state[s] * 100, 1)

        def _sync_from_input(s=sk, i=ik):
            st.session_state[s] = st.session_state[i] / 100

        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            st.text(f"{asset['ticker']} - {asset['name']}")
        with col2:
            st.slider(
                "Weight",
                0.0,
                1.0,
                step=0.01,
                key=sk,
                on_change=_sync_from_slider,
                label_visibility="collapsed",
            )
        with col3:
            st.number_input(
                "Weight %",
                min_value=0.0,
                max_value=100.0,
                step=0.1,
                format="%.1f",
                key=ik,
                on_change=_sync_from_input,
                label_visibility="collapsed",
            )

        weight = float(st.session_state[sk])
        updated.append({**asset, "weight": weight})
        total += weight

    color = "green" if abs(total - 1.0) < 0.01 else "red"
    st.markdown(f"**Total: :{color}[{total:.1%}]**")
    if abs(total - 1.0) >= 0.01:
        st.warning("Weights must sum to 100%")

    return updated
