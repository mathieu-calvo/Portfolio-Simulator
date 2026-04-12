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


def _get_authenticator() -> stauth.Authenticate:
    """Return a cached Authenticate instance, building it once per session.

    We can't use @st.cache_resource because the Authenticate constructor
    instantiates a cookie manager (a streamlit custom component / widget),
    which isn't allowed inside cached functions. Instead we stash the instance
    in st.session_state so it's reused across reruns.
    """
    if "_authenticator" not in st.session_state:
        credentials = _to_mutable(st.secrets["credentials"])
        st.session_state["_authenticator"] = stauth.Authenticate(
            credentials,
            st.secrets["cookie"]["name"],
            st.secrets["cookie"]["key"],
            st.secrets["cookie"]["expiry_days"],
        )
    return st.session_state["_authenticator"]


def authenticate() -> str | None:
    """Run login flow. Returns username if authenticated, None otherwise."""
    authenticator = _get_authenticator()

    authenticator.login()

    if st.session_state.get("authentication_status"):
        authenticator.logout("Logout", "sidebar")
        return st.session_state.get("username")
    elif st.session_state.get("authentication_status") is False:
        st.error("Username or password is incorrect.")
    else:
        st.info("Please log in to access the Portfolio Simulator.")

    return None
