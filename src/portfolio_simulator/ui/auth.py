"""Authentication gate using streamlit-authenticator."""

from __future__ import annotations

import streamlit as st
import streamlit_authenticator as stauth


def _to_mutable(obj):
    """Recursively convert Streamlit Secrets / AttrDict objects into plain dicts.

    streamlit-authenticator mutates the credentials dict (to track failed login
    attempts, etc.), but st.secrets returns read-only objects. A shallow dict()
    copy isn't enough — nested values are still read-only.
    """
    if hasattr(obj, "to_dict"):
        obj = obj.to_dict()
    if isinstance(obj, dict):
        return {k: _to_mutable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_mutable(v) for v in obj]
    return obj


def authenticate() -> str | None:
    """Run login flow. Returns username if authenticated, None otherwise."""
    credentials = _to_mutable(st.secrets["credentials"])
    authenticator = stauth.Authenticate(
        credentials,
        st.secrets["cookie"]["name"],
        st.secrets["cookie"]["key"],
        st.secrets["cookie"]["expiry_days"],
    )

    authenticator.login()

    if st.session_state.get("authentication_status"):
        authenticator.logout("Logout", "sidebar")
        return st.session_state.get("username")
    elif st.session_state.get("authentication_status") is False:
        st.error("Username or password is incorrect.")
    else:
        st.info("Please log in to access the Portfolio Simulator.")

    return None
