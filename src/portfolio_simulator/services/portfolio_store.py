"""Portfolio persistence via SQLite with JSON example seeding."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from portfolio_simulator.domain.portfolio import Portfolio

logger = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS portfolios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    data_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
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
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute(_CREATE_TABLE)
        self._conn.commit()

        if fixtures_dir and self._is_empty():
            self._seed_from_fixtures(Path(fixtures_dir))

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

    def save(self, portfolio: Portfolio) -> None:
        """Save or update a portfolio."""
        now = datetime.now().isoformat()
        data_json = json.dumps(portfolio.to_dict())
        self._conn.execute(
            """INSERT INTO portfolios (name, data_json, created_at, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET data_json = ?, updated_at = ?""",
            (portfolio.name, data_json, now, now, data_json, now),
        )
        self._conn.commit()

    def load(self, name: str) -> Portfolio:
        """Load a portfolio by name."""
        row = self._conn.execute(
            "SELECT data_json FROM portfolios WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            raise KeyError(f"Portfolio '{name}' not found")
        return Portfolio.from_dict(json.loads(row[0]))

    def list_all(self) -> list[Portfolio]:
        """List all saved portfolios."""
        rows = self._conn.execute(
            "SELECT data_json FROM portfolios ORDER BY name"
        ).fetchall()
        return [Portfolio.from_dict(json.loads(row[0])) for row in rows]

    def delete(self, name: str) -> None:
        """Delete a portfolio by name."""
        self._conn.execute("DELETE FROM portfolios WHERE name = ?", (name,))
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
