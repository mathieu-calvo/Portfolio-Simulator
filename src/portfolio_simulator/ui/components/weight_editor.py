"""Portfolio weight allocation editor."""

from __future__ import annotations

import streamlit as st


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

    for i, asset in enumerate(assets):
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            st.text(f"{asset['ticker']} - {asset['name']}")
        with col2:
            weight = st.slider(
                f"Weight",
                0.0,
                1.0,
                value=asset.get("weight", 1.0 / len(assets)),
                step=0.01,
                key=f"{key}_slider_{i}",
                label_visibility="collapsed",
            )
        with col3:
            weight = st.number_input(
                "Weight %",
                min_value=0.0,
                max_value=100.0,
                value=round(weight * 100, 1),
                step=0.1,
                format="%.1f",
                key=f"{key}_input_{i}",
                label_visibility="collapsed",
            ) / 100

        updated.append({**asset, "weight": weight})
        total += weight

    # Show total
    color = "green" if abs(total - 1.0) < 0.01 else "red"
    st.markdown(f"**Total: :{color}[{total:.1%}]**")
    if abs(total - 1.0) >= 0.01:
        st.warning("Weights must sum to 100%")

    return updated
