"""Services package with store factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from portfolio_simulator.services.pg_portfolio_store import PgPortfolioStore
    from portfolio_simulator.services.portfolio_store import PortfolioStore


def get_portfolio_store() -> PortfolioStore | PgPortfolioStore:
    """Return the appropriate portfolio store based on configuration.

    Uses PostgreSQL if database_url is configured, otherwise SQLite.
    """
    from portfolio_simulator.config import settings

    if settings.database_url:
        from portfolio_simulator.services.pg_portfolio_store import PgPortfolioStore
        return PgPortfolioStore(settings.database_url)
    else:
        from portfolio_simulator.services.portfolio_store import PortfolioStore
        return PortfolioStore(settings.db_path)
