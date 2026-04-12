"""Portfolio persistence via SQLite with JSON example seeding."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from portfolio_simulator.domain.portfolio import Portfolio

logger = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS portfolios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'local',
    name TEXT NOT NULL,
    data_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, name)
)
"""


class PortfolioStore:
    """Save and load portfolios from SQLite.

    On first initialization, seeds example portfolios from JSON fixtures
    if the database is empty.
    """

    def __init__(self, db_path: str | Path, fixtures_dir: str | Path | None = None) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False is required because this store is wrapped
        # in @st.cache_resource and therefore shared across Streamlit's
        # worker threads. All access is serialized through self._lock so
        # the single connection is used safely from multiple threads.
        self._conn = sqlite3.connect(
            str(self._db_path), check_same_thread=False
        )
        self._lock = threading.Lock()
        self._migrate()

        if fixtures_dir and self._is_empty():
            self._seed_from_fixtures(Path(fixtures_dir))

    def _migrate(self) -> None:
        """Create table or migrate from old schema."""
        # Check if old schema exists (name UNIQUE without user_id)
        cursor = self._conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='portfolios'")
        if cursor.fetchone():
            # Table exists — check if user_id column is present
            cols = [row[1] for row in self._conn.execute("PRAGMA table_info(portfolios)")]
            if "user_id" not in cols:
                logger.info("Migrating portfolios table: adding user_id column")
                self._conn.execute("ALTER TABLE portfolios ADD COLUMN user_id TEXT NOT NULL DEFAULT 'local'")
                # Recreate table with new unique constraint
                self._conn.execute("""
                    CREATE TABLE IF NOT EXISTS portfolios_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL DEFAULT 'local',
                        name TEXT NOT NULL,
                        data_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        UNIQUE(user_id, name)
                    )
                """)
                self._conn.execute("""
                    INSERT INTO portfolios_new (id, user_id, name, data_json, created_at, updated_at)
                    SELECT id, user_id, name, data_json, created_at, updated_at FROM portfolios
                """)
                self._conn.execute("DROP TABLE portfolios")
                self._conn.execute("ALTER TABLE portfolios_new RENAME TO portfolios")
                self._conn.commit()
        else:
            self._conn.execute(_CREATE_TABLE)
            self._conn.commit()

    def _is_empty(self) -> bool:
        row = self._conn.execute("SELECT COUNT(*) FROM portfolios").fetchone()
        return row[0] == 0

    def _seed_from_fixtures(self, fixtures_dir: Path) -> None:
        if not fixtures_dir.exists():
            return
        for path in sorted(fixtures_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                portfolio = Portfolio.from_dict(data)
                self.save(portfolio)
                logger.info(f"Seeded example portfolio: {portfolio.name}")
            except Exception:
                logger.warning(f"Failed to seed from {path}", exc_info=True)

    def save(self, portfolio: Portfolio, user_id: str = "local") -> None:
        """Save or update a portfolio."""
        now = datetime.now().isoformat()
        data_json = json.dumps(portfolio.to_dict())
        with self._lock:
            self._conn.execute(
                """INSERT INTO portfolios (user_id, name, data_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(user_id, name) DO UPDATE SET data_json = ?, updated_at = ?""",
                (user_id, portfolio.name, data_json, now, now, data_json, now),
            )
            self._conn.commit()

    def load(self, name: str, user_id: str = "local") -> Portfolio:
        """Load a portfolio by name."""
        with self._lock:
            row = self._conn.execute(
                "SELECT data_json FROM portfolios WHERE user_id = ? AND name = ?", (user_id, name)
            ).fetchone()
        if row is None:
            raise KeyError(f"Portfolio '{name}' not found")
        return Portfolio.from_dict(json.loads(row[0]))

    def list_all(self, user_id: str = "local") -> list[Portfolio]:
        """List all saved portfolios for a user."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT data_json FROM portfolios WHERE user_id = ? ORDER BY name", (user_id,)
            ).fetchall()
        return [Portfolio.from_dict(json.loads(row[0])) for row in rows]

    def delete(self, name: str, user_id: str = "local") -> None:
        """Delete a portfolio by name."""
        with self._lock:
            self._conn.execute(
                "DELETE FROM portfolios WHERE user_id = ? AND name = ?", (user_id, name)
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
