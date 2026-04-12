"""Services package with store and data-service factories."""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    from portfolio_simulator.providers.base import DataProvider
    from portfolio_simulator.services.data_service import DataService
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


def _build_provider(provider_name: str) -> "DataProvider":
    if provider_name == "yahoo":
        from portfolio_simulator.providers.yahoo import YahooFinanceProvider
        return YahooFinanceProvider()
    raise ValueError(
        f"Provider '{provider_name}' is not available. "
        f"Only 'yahoo' is currently implemented."
    )


@st.cache_resource
def get_data_service(provider_name: str) -> "DataService":
    """Return a cached DataService for the given provider.

    The cache key includes ``provider_name`` so switching providers in the UI
    returns a different (also cached) service instance. DataService opens
    SQLite cache connections in its constructor, so caching avoids re-opening
    them on every rerun.
    """
    from portfolio_simulator.services.data_service import DataService

    provider = _build_provider(provider_name)
    return DataService(provider)


def get_provider(provider_name: str) -> "DataProvider":
    """Return a fresh provider instance for the given name.

    Providers are cheap to build (no network/DB connections on construction),
    so this is not cached.
    """
    return _build_provider(provider_name)
