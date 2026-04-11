"""Authentication gate using streamlit-authenticator."""

from __future__ import annotations

import streamlit as st
import streamlit_authenticator as stauth


def authenticate() -> str | None:
    """Run login flow. Returns username if authenticated, None otherwise."""
    credentials = dict(st.secrets["credentials"])
    authenticator = stauth.Authenticate(
        credentials,
        st.secrets["cookie"]["name"],
        st.secrets["cookie"]["key"],
        st.secrets["cookie"]["expiry_days"],
    )

    authenticator.login()

    if st.session_state.get("authentication_status"):
        authenticator.logout("Logout", "sidebar")
        return st.session_state["username"]
    elif st.session_state.get("authentication_status") is False:
        st.error("Username or password is incorrect.")
    else:
        st.info("Please log in to access the Portfolio Simulator.")

    return None
