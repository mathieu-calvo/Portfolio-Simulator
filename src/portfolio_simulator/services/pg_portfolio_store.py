"""Portfolio persistence via PostgreSQL (Supabase)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

from portfolio_simulator.domain.portfolio import Portfolio

logger = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS portfolios (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    data_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, name)
)
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_portfolios_user ON portfolios(user_id)
"""


class PgPortfolioStore:
    """Save and load portfolios from PostgreSQL with per-user isolation."""

    def __init__(self, database_url: str) -> None:
        # Ensure SSL is required (Supabase enforces SSL)
        if "sslmode=" not in database_url:
            sep = "&" if "?" in database_url else "?"
            database_url = f"{database_url}{sep}sslmode=require"
        try:
            self._conn = psycopg2.connect(database_url, connect_timeout=10)
        except psycopg2.OperationalError as e:
            # Re-raise with a clearer message that Streamlit will show
            # (scrub the password from any URL that appears in the error)
            raise RuntimeError(
                f"Failed to connect to PostgreSQL: {e}. "
                f"Check that your database_url uses the Supabase Session pooler "
                f"(hostname should contain 'pooler.supabase.com') and that your "
                f"password is URL-encoded if it contains special characters."
            ) from e
        self._conn.autocommit = False
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        with self._conn.cursor() as cur:
            cur.execute(_CREATE_TABLE)
            cur.execute(_CREATE_INDEX)
        self._conn.commit()

    def save(self, portfolio: Portfolio, user_id: str = "local") -> None:
        """Save or update a portfolio for a specific user."""
        now = datetime.now(timezone.utc)
        data_json = json.dumps(portfolio.to_dict())
        with self._conn.cursor() as cur:
            cur.execute(
                """INSERT INTO portfolios (user_id, name, data_json, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (user_id, name)
                   DO UPDATE SET data_json = EXCLUDED.data_json, updated_at = EXCLUDED.updated_at""",
                (user_id, portfolio.name, data_json, now, now),
            )
        self._conn.commit()

    def load(self, name: str, user_id: str = "local") -> Portfolio:
        """Load a portfolio by name for a specific user."""
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT data_json FROM portfolios WHERE user_id = %s AND name = %s",
                (user_id, name),
            )
            row = cur.fetchone()
        if row is None:
            raise KeyError(f"Portfolio '{name}' not found")
        data = row[0] if isinstance(row[0], dict) else json.loads(row[0])
        return Portfolio.from_dict(data)

    def list_all(self, user_id: str = "local") -> list[Portfolio]:
        """List all saved portfolios for a specific user."""
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT data_json FROM portfolios WHERE user_id = %s ORDER BY name",
                (user_id,),
            )
            rows = cur.fetchall()
        results = []
        for row in rows:
            data = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            results.append(Portfolio.from_dict(data))
        return results

    def delete(self, name: str, user_id: str = "local") -> None:
        """Delete a portfolio by name for a specific user."""
        with self._conn.cursor() as cur:
            cur.execute(
                "DELETE FROM portfolios WHERE user_id = %s AND name = %s",
                (user_id, name),
            )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
