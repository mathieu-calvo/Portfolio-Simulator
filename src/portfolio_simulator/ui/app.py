"""Streamlit app entrypoint."""

import streamlit as st

st.set_page_config(
    page_title="Portfolio Simulator",
    page_icon="\U0001f4c8",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
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
