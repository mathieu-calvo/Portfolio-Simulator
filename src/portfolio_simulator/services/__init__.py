"""Services package with store factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    from portfolio_simulator.services.pg_portfolio_store import PgPortfolioStore
    from portfolio_simulator.services.portfolio_store import PortfolioStore


@st.cache_resource
def get_portfolio_store():
    """Return the appropriate portfolio store based on configuration.

    Uses PostgreSQL if database_url is configured, otherwise SQLite.
    Cached via st.cache_resource so the DB connection is opened once per
    session, not once per rerun — avoids connection churn and latency.
    """
    from portfolio_simulator.config import settings

    if settings.database_url:
        from portfolio_simulator.services.pg_portfolio_store import PgPortfolioStore
        return PgPortfolioStore(settings.database_url)
    else:
        from portfolio_simulator.services.portfolio_store import PortfolioStore
        return PortfolioStore(settings.db_path)
