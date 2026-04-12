"""Streamlit app entrypoint."""

import sys
from pathlib import Path

# Ensure `src/` is importable when running via `streamlit run` (e.g. on Streamlit Cloud)
_SRC_DIR = Path(__file__).resolve().parents[2]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

import streamlit as st

st.set_page_config(
    page_title="Portfolio Simulator",
    page_icon="\U0001f4c8",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    from portfolio_simulator.config import settings

    # --- Authentication gate ---
    if settings.require_auth:
        from portfolio_simulator.ui.auth import authenticate

        user_id = authenticate()
        if user_id is None:
            st.stop()
        st.session_state["user_id"] = user_id
    else:
        st.session_state.setdefault("user_id", "local")

    # --- Navigation ---
    st.sidebar.title("Portfolio Simulator")
    page = st.sidebar.radio(
        "Navigate",
        ["Portfolio Builder", "Backtest", "Comparison", "Optimizer"],
    )

    if page == "Portfolio Builder":
        from portfolio_simulator.ui.views.portfolio_builder import render
        render()
    elif page == "Backtest":
        from portfolio_simulator.ui.views.backtest import render
        render()
    elif page == "Comparison":
        from portfolio_simulator.ui.views.comparison import render
        render()
    elif page == "Optimizer":
        from portfolio_simulator.ui.views.optimizer import render
        render()


if __name__ == "__main__":
    main()
