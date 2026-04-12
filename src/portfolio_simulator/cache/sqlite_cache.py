"""SQLite-based persistent cache for market data."""

from __future__ import annotations

import io
import logging
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS price_cache (
    cache_key TEXT PRIMARY KEY,
    data BLOB NOT NULL,
    fetched_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
)
"""


class SQLiteCache:
    """Persistent cache backed by a SQLite database.

    Price series are stored as Parquet blobs for compact, fast I/O.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False is required because this cache is held
        # inside DataService, which is wrapped in @st.cache_resource and
        # therefore shared across Streamlit's worker threads. We serialize
        # all access through self._lock so the single connection is used
        # safely from multiple threads.
        self._conn = sqlite3.connect(
            str(self._db_path), check_same_thread=False
        )
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute(_CREATE_TABLE)
            self._conn.commit()

    def get(self, key: str) -> pd.Series | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT data, expires_at FROM price_cache WHERE cache_key = ?", (key,)
            ).fetchone()
        if row is None:
            return None

        expires_at = datetime.fromisoformat(row[1])
        if datetime.now() > expires_at:
            self.invalidate(key)
            return None

        buf = io.BytesIO(row[0])
        df = pd.read_parquet(buf)
        series = df.iloc[:, 0]
        series.name = df.columns[0]
        return series

    def put(self, key: str, data: pd.Series, ttl_hours: int = 24) -> None:
        buf = io.BytesIO()
        data.to_frame().to_parquet(buf, engine="pyarrow")
        blob = buf.getvalue()

        now = datetime.now()
        expires = now + timedelta(hours=ttl_hours)

        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO price_cache (cache_key, data, fetched_at, expires_at) VALUES (?, ?, ?, ?)",
                (key, blob, now.isoformat(), expires.isoformat()),
            )
            self._conn.commit()

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM price_cache WHERE cache_key = ?", (key,))
            self._conn.commit()

    def clear(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM price_cache")
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
