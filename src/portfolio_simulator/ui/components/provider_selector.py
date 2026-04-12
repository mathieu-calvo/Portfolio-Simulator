"""Data source (provider) selector sidebar component.

Displays the currently-active market data provider as a branded badge and —
when multiple providers are wired up — lets the user switch between them.
The selected provider name is persisted in ``st.session_state["provider_name"]``
and consumed by every view that needs market data.
"""

from __future__ import annotations

import streamlit as st

# Per-provider metadata used to render the sidebar badge and "coming soon" list.
# Add new entries here as providers are implemented. Set ``available=True`` once
# the provider class exists and can be instantiated.
PROVIDER_META: dict[str, dict] = {
    "yahoo": {
        "display_name": "Yahoo! Finance",
        "color": "#5F01D1",  # Yahoo brand purple
        "description": "Free public markets data via the yfinance library. "
                       "Supports stocks, ETFs, indices, crypto, and FX.",
        "website": "https://finance.yahoo.com",
        "available": True,
    },
    "reuters": {
        "display_name": "Reuters / Refinitiv",
        "color": "#FF8000",
        "description": "Professional-grade market data via Refinitiv Eikon. "
                       "Requires an API key — set PSIM_REUTERS_API_KEY.",
        "website": "https://www.refinitiv.com",
        "available": False,
    },
    "bloomberg": {
        "display_name": "Bloomberg",
        "color": "#000000",
        "description": "Bloomberg Terminal data via BLPAPI. Requires a "
                       "Bloomberg Terminal license.",
        "website": "https://www.bloomberg.com/professional",
        "available": False,
    },
}


def _available_providers() -> list[str]:
    return [name for name, meta in PROVIDER_META.items() if meta["available"]]


def _render_badge(meta: dict) -> None:
    """Render a branded text badge for the given provider.

    We deliberately don't fetch logo images from external URLs — hotlinked
    images (e.g. Wikipedia Commons) often fail to render on Streamlit Cloud
    and leave a broken-image icon in the sidebar. A styled text badge in
    the provider's brand color is reliable, clean, and offline-friendly.
    To add a real logo later, drop an SVG/PNG into src/portfolio_simulator/ui/assets/
    and extend this function to load it via importlib.resources.
    """
    st.markdown(
        f"""
        <div style='
            padding: 10px 12px;
            border-radius: 8px;
            background: {meta["color"]};
            color: white;
            text-align: center;
            font-weight: 600;
            font-size: 14px;
            margin: 6px 0 4px 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        '>
            {meta["display_name"]}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_provider_selector() -> str:
    """Render the sidebar data-source section and return the selected name.

    Behaviour:
    - If exactly one provider is available, show it as a badge (no selector).
    - If multiple are available, render a radio selector so the user can toggle.
    - Unavailable providers are listed in a "Coming soon" expander so users
      can see the roadmap.
    """
    available = _available_providers()
    if not available:
        raise RuntimeError("No data providers are marked available in PROVIDER_META")

    # Default on first render
    if "provider_name" not in st.session_state or st.session_state["provider_name"] not in available:
        st.session_state["provider_name"] = available[0]

    with st.sidebar:
        st.markdown("---")
        st.markdown("### Data Source")

        if len(available) == 1:
            current = available[0]
            st.session_state["provider_name"] = current
        else:
            current = st.radio(
                "Provider",
                available,
                format_func=lambda n: PROVIDER_META[n]["display_name"],
                key="provider_name",
                label_visibility="collapsed",
            )

        meta = PROVIDER_META[current]
        _render_badge(meta)
        st.caption(meta["description"])
        st.caption(f"[Website]({meta['website']})")

        # Surface the roadmap so users understand the selector will grow
        unavailable = [n for n, m in PROVIDER_META.items() if not m["available"]]
        if unavailable:
            with st.expander("Coming soon"):
                for name in unavailable:
                    m = PROVIDER_META[name]
                    st.markdown(f"**{m['display_name']}** — {m['description']}")

    return st.session_state["provider_name"]
