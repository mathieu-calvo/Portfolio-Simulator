"""Authentication gate using streamlit-authenticator."""

from __future__ import annotations

import streamlit as st
import streamlit_authenticator as stauth


def _to_mutable(obj):
    """Recursively convert Streamlit Secrets / AttrDict objects into plain dicts.

    streamlit-authenticator mutates the credentials dict (to track failed login
    attempts, logged_in state, etc.), but st.secrets returns read-only objects.
    A shallow dict() copy isn't enough — nested values are still read-only.
    """
    if hasattr(obj, "to_dict"):
        obj = obj.to_dict()
    if isinstance(obj, dict):
        return {k: _to_mutable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_mutable(v) for v in obj]
    return obj


@st.cache_resource
def _get_authenticator() -> stauth.Authenticate:
    """Build the authenticator once per session and cache it.

    Caching is important because streamlit-authenticator stores mutable state
    (failed_login_attempts, logged_in, etc.) inside the credentials dict.
    Rebuilding it on every rerun would wipe that state.
    """
    credentials = _to_mutable(st.secrets["credentials"])
    return stauth.Authenticate(
        credentials,
        st.secrets["cookie"]["name"],
        st.secrets["cookie"]["key"],
        st.secrets["cookie"]["expiry_days"],
    )


def authenticate() -> str | None:
    """Run login flow. Returns username if authenticated, None otherwise."""
    authenticator = _get_authenticator()

    authenticator.login()

    if st.session_state.get("authentication_status"):
        authenticator.logout("Logout", "sidebar")
        return st.session_state["username"]
    elif st.session_state.get("authentication_status") is False:
        st.error("Username or password is incorrect.")
    else:
        st.info("Please log in to access the Portfolio Simulator.")

    return None
